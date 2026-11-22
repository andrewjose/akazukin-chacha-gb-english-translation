"""Akazukin Chacha (GB) English UI layer.  Runs AFTER the engine build:

    python3 -I tools/ui/build_ui.py IN.gb OUT.gb [--tr $CHACHA_WORK/tl/merged.json]

Paths: tools/common/paths.py (CHACHA_ROM, CHACHA_WORK, CHACHA_STRINGS, RGBDS_DIR, CHACHA_TTF).

IN.gb = engine/tools/build.py output.  Every byte this script changes outside banks 18h-1Fh is asserted first
(original value or the engine's value).  See ../NOTES.md for the screen-by-screen design.

What it does
 * Labels are precomposed at build time (tools/ptext.py, engine VWF font, emboldened 1 px like the menu font)
   into 8x8 tiles; at runtime a blitter in bank 18h copies them to VRAM (STAT-safe) and optionally writes the tilemap.
 * Bank 0 $1434-$14E6 (HUD init + cmd records + hand-slot printer, HUD-only) is replaced by the HUD entry,
   a far-call dispatcher and stubs; $1A06 (rank kanji) and the FD printer ($3F30) are redirected.
 * Static screen layouts (HUD 02:7812, report card 02:520B, results 02:7902, password 03:6961) are re-lettered
   in place: label tile ids written into the tilemaps, the rest of each label area blanked.
 * Password: codes stay the game's (00-36, 70-77, 7B); on the password screen tiles 00-36/77/7B get Latin glyphs,
   and the FD printer translates the same codes to the same characters for the VWF.
 * Title menu sprites: OBJ font copy ($2D91) repointed to a block with "New Game"/"Continue" word tiles.
 * Results stamps (02:7A6A pass / 02:7B6A fail, 256 bytes raw each) redrawn in English.
"""
import sys,os,json,re,subprocess,hashlib,argparse
T=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,T); sys.path.insert(0,os.path.join(T,'..','engine'))
sys.path.insert(0,os.path.join(T,'..','common')); import paths
UI=paths.UI_WORK     # generated asm/tiles (tmp/gen), objects, symbols
import ptext
from lz import compress,decompress
STRINGS=paths.STRINGS
MERGED=os.path.join(paths.WORK,'tl','merged.json')
UI_BANK=0x18
GEN=os.path.join(UI,'tmp','gen')

def off(b,a): return a if a<0x4000 else b*0x4000+a-0x4000
def vram_tile(t,obj=False):
    if obj: return 0x8000+t*16
    return 0x9000+t*16 if t<0x80 else 0x8800+(t-0x80)*16
def maddr(row,col,base=0x9800): return base+row*32+col

# ------------------------------------------------------------------ texts (UI wording; see NOTES.md)
UIT={
 'run':'Run', 'left':'Left', 'right':'Right',
 'rep_title':'Report Card', 'name':'Name', 'rank':'Rank', 'exp':'EXP', 'skill':'Skill',
 'days_left':'Days left', 'to_parents':'To Parents',
 'res_title':'Exam Results', 'task':'Task', 'score':'Your score:', 'points':'pts.', 'urara':'Urara',
 'gameover':'GAME OVER',
 'pw_title':None, 'pw_end':'End', 'pw_err1':None, 'pw_err2':None,
 'new':'New Game', 'cont':'Continue',
}
RANKS=['Novice','Grade 5','Grade 4','Grade 3','Grade 2','Grade 1','Special']   # shokyuu go kyuu..ikkyuu tokkyuu
QUEST_ALT={}   # filled from tl/out alt_long (results screen has 16 cells)

# ------------------------------------------------------------------ helpers
class Out:
    def __init__(s): s.lines=[]; s.blobs=[]; s.n=0; s.blobbytes=0
    def blob(s,data,name=None):
        name=name or 'blob%d'%s.n; s.n+=1
        s.blobs.append((name,bytes(data))); s.blobbytes+=len(data); return name
OUT=Out()
REC=[]    # (label, [records]) record = dict(blob, vram, n, t0, map, cols)

def rec(blob,vram,n,t0,mp,cols):
    return dict(blob=blob,vram=vram,n=n,t0=t0,map=mp,cols=cols)

class Pool:
    def __init__(s,name,ranges): s.name=name; s.free=[t for a,b in ranges for t in range(a,b+1)]; s.i=0
    def take(s,n):
        # n consecutive tile ids
        for i in range(s.i,len(s.free)-n+1):
            run=s.free[i:i+n]
            if run[-1]-run[0]==n-1:
                del s.free[i:i+n]; return run[0]
        raise SystemExit('pool %s: no %d consecutive tiles left'%(s.name,n))

def static_label(rom,tmap_off,text,row,col,ncells,pool,align='l',bold=True,w=20,obj=False,blank=True,xoff=0):
    """re-letter a ROM tilemap area (row,col..col+ncells-1): only occupied cells get tiles. -> record (no map write)"""
    W=ptext.width(text,bold)
    if W>ncells*8: raise SystemExit('static label %r (%d px) > %d cells'%(text,W,ncells))
    if align=='c': x0=(ncells*8-W)//2
    elif align=='r': x0=ncells*8-W
    else: x0=0
    x0+=xoff
    c0=x0//8; c1=(x0+W-1)//8; n=c1-c0+1
    cv,_=ptext.canvas(text,n,align='l',bold=bold,xoff=x0-c0*8)
    data=ptext.to_tiles(cv)
    t0=pool.take(n)
    if blank:
        for c in range(ncells): rom[tmap_off+row*w+col+c]=0xFF
    for k in range(n): rom[tmap_off+row*w+col+c0+k]=t0+k
    return rec(OUT.blob(data),vram_tile(t0,obj),n,t0,0,n)

def dyn_label(text,ncells,t0,mp,align='l',bold=True,rows=1,tall=False,xoff=0,yoff=0,obj=False):
    data=ptext.tiles(text,ncells,align=align,bold=bold,rows=rows,tall=tall,xoff=xoff,yoff=yoff)
    return rec(OUT.blob(data),vram_tile(t0,obj),ncells*rows,t0,mp,ncells)

def exit_sign(orig):
    """dungeon exit sign 32x16 (4x2 tiles): keep the frame, letter EXIT"""
    px=[[0]*32 for _ in range(16)]
    for t in range(8):
        tx,ty=t%4,t//4
        for y in range(8):
            lo,hi=orig[t*16+2*y],orig[t*16+2*y+1]
            for x in range(8): px[ty*8+y][tx*8+x]=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
    for y in range(4,12):
        for x in range(5,27): px[y][x]=0
    g,W=ptext.render('EXIT',bold=True); x0=4+(24-W)//2
    for y in range(6):
        for x in range(W):
            if g[y][x]: px[5+y][x0+x]=3
    out=bytearray()
    for t in range(8):
        tx,ty=t%4,t//4
        for y in range(8):
            lo=hi=0
            for x in range(8):
                c=px[ty*8+y][tx*8+x]; lo|=(c&1)<<(7-x); hi|=((c>>1)&1)<<(7-x)
            out+=bytes([lo,hi])
    return bytes(out)

def put(rom,o,data,expect=None,what=''):
    if expect is not None:
        cur=bytes(rom[o:o+len(expect)])
        if cur!=bytes(expect):
            raise SystemExit('assert failed at %06X (%s): %s != %s'%(o,what,cur.hex(),bytes(expect).hex()))
    rom[o:o+len(data)]=bytes(data)

def expect_any(rom,o,options,what):
    cur=bytes(rom[o:o+len(options[0])])
    if cur not in [bytes(x) for x in options]:
        raise SystemExit('assert failed at %06X (%s): %s not in %s'%(o,what,cur.hex(),[bytes(x).hex() for x in options]))

# ------------------------------------------------------------------ main
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--tr',default=MERGED)
    a=ap.parse_args()
    os.makedirs(GEN,exist_ok=True)
    rom=bytearray(open(a.inp,'rb').read()); orig=open(paths.rom_path(),'rb').read()
    assert hashlib.md5(orig).hexdigest()==paths.ORIG_MD5, 'original ROM MD5 mismatch'
    assert len(rom)==0x80000 and rom[0x148]==4, 'input must be the engine build (512 KB)'
    for b in range(UI_BANK,0x20):
        seg=rom[b*0x4000:(b+1)*0x4000]
        assert seg.count(0xFF)==0x4000, 'bank %02X not empty in the engine build'%b
    tr={x['id']:x for x in json.load(open(a.tr))}
    S=json.load(open(STRINGS)); byid={x['id']:x for x in S}
    alt={i:x['alt_long'] for i,x in tr.items() if x.get('alt_long')}   # longer variants (results screen quest line)
    def en(i): return tr[i]['en'].replace('<END>','')
    pwt=en('pw_title').strip('- ').strip()                       # "Diary Spell"
    m=en('pw_error').split('<NL>'); err1=m[0].strip(); err2=re.sub(r'<HEX:[0-9a-fA-F]+>','',m[1]).replace('<HEART>','♡').strip()

    ofont=decompress(orig,off(3,0x5976),0x800)[0]
    lists={}   # name -> list of records
    tables={}  # name -> list of records (pointer table)
    consts={}

    # ============ HUD (window $9C00, LCDC $8800 mode). tiles 3C-53.
    hud_off=off(2,0x7812)
    for c in list(range(1,10))+list(range(11,19)):          # rows 3/4 label cells -> blank
        for r in (3,4): rom[hud_off+r*20+c]=0xFF
    hp=Pool('hud',[(0x41,0x43)])
    lists['HudStatic']=[static_label(rom,hud_off,UIT['run'],3,11,4,hp)]
    cmds=[en('cmd_%d'%i).strip() for i in range(6)]
    tables['CmdRecs']=[dyn_label(t,5,0x3C,maddr(3,2,0x9C00)) for t in cmds]
    consts['NUM_CMD']=6
    slot={}
    for x in S:
        for pl in x['ptr_locs']: slot[pl]=x['id']
    items=[]
    for k in range(64):
        sid=slot[off(0x0E,0x4BD1+2*k)]; full=en(sid)
        s8=tr[sid].get('short8') or full
        t=full if ptext.width(full)<=64 else s8
        if ptext.width(t)>64: t=s8[:8]
        items.append(t)
    item_blobs=[OUT.blob(ptext.tiles(t,8,align='l'),'item%02X'%k) for k,t in enumerate(items)]
    lb=OUT.blob(ptext.tiles(UIT['left'],8,align='l')); rb=OUT.blob(ptext.tiles(UIT['right'],8,align='l'))
    tables['LeftRecs']=[rec(b,vram_tile(0x44),8,0x44,maddr(4,2,0x9C00),8) for b in item_blobs+[lb]]
    tables['RightRecs']=[rec(b,vram_tile(0x4C),8,0x4C,maddr(4,11,0x9C00),8) for b in item_blobs+[rb]]

    # ============ report card (02:520B tilemap 20x18 at $9800). pool 3C-71
    ro=off(2,0x520B); rp=Pool('report',[(0x3C,0x71)])
    L=[]
    for c in range(1,19): rom[ro+1*20+c]=0xFF
    rom[ro+20+2:ro+20+5]=bytes([0x72,0x7B,0x72]); rom[ro+20+15:ro+20+18]=bytes([0x72,0x7B,0x72])
    L.append(static_label(rom,ro,UIT['rep_title'],1,5,10,rp,align='c'))
    L.append(rec(OUT.blob(ofont[0x73*16:0x74*16]),vram_tile(0x73),1,0x73,0,1))   # gauge dot: original .
    L.append(static_label(rom,ro,UIT['name'],3,7,5,rp))
    L.append(static_label(rom,ro,UIT['rank'],5,7,4,rp))
    for r in (4,5):
        for c in range(13,19): rom[ro+r*20+c]=0xFF
    L.append(static_label(rom,ro,UIT['exp'],7,7,5,rp))
    for c in range(13,19): rom[ro+7*20+c]=0xFF
    L.append(static_label(rom,ro,UIT['skill'],9,1,4,rp))
    for c in range(1,19): rom[ro+11*20+c]=0xFF
    L.append(static_label(rom,ro,UIT['days_left'],11,8,8,rp,align='r',blank=False,xoff=-3))
    for c in range(1,19): rom[ro+13*20+c]=0xFF
    rom[ro+13*20+1]=0x7D
    r_tp=static_label(rom,ro,UIT['to_parents'],13,3,10,rp,blank=False); L.append(r_tp)
    endc=3+r_tp['n']
    for c in range(endc+1,19): rom[ro+13*20+c]=0x7D
    lists['ReportLabels']=L
    t_rw=rp.take(6)
    rw=[x.strip() for x in re.sub(r'<HEX:[0-9a-fA-F]+>','',en('rank_words')).replace('So-so','So-so ').split()]
    rw=['Poor','So-so','Almost','Close'] if len(rw)!=4 else rw
    tables['RankWordRecs']=[dyn_label(t,6,t_rw,maddr(7,13)) for t in rw]
    consts['REPORT_POOL_LEFT']=len(rp.free)
    # rank (both screens): tall text, 6x2 cells, tiles B2-BD ($8B20), map $988D
    tables['RankRecs']=[rec(OUT.blob(ptext.big_tiles(t)),vram_tile(0xB2),14,0xB2,maddr(4,12),7) for t in RANKS]   # tiles B2-BF
    consts['NUM_RANK']=len(RANKS)

    # ============ results (02:7902 tilemap). pool 3C-71
    so=off(2,0x7902); sp=Pool('results',[(0x3C,0x53),(0x80,0x93)])   # 54-6F = engine dual-mode canvas
    L=[]
    for c in range(1,19): rom[so+1*20+c]=0xFF
    rom[so+20+2]=0x7B; rom[so+20+17]=0x7B
    L.append(static_label(rom,so,UIT['res_title'],1,3,14,sp,align='c'))
    L.append(static_label(rom,so,UIT['name'],3,7,5,sp))
    L.append(static_label(rom,so,UIT['rank'],5,7,4,sp))
    for r in (4,5):
        for c in range(13,19): rom[so+r*20+c]=0xFF
    for c in range(1,19): rom[so+7*20+c]=0xFF
    for c in range(1,19): rom[so+8*20+c]=0xFF
    L.append(static_label(rom,so,UIT['days_left'],8,6,8,sp,align='r',blank=False,xoff=-3))
    L.append(static_label(rom,so,UIT['task']+':',9,1,6,sp))
    for c in range(1,12): rom[so+11*20+c]=0xFF
    L.append(static_label(rom,so,UIT['score'],11,1,10,sp,blank=False))
    L.append(static_label(rom,so,UIT['points'],13,8,4,sp,blank=False,xoff=4))
    for c in range(1,16): rom[so+15*20+c]=0xFF
    L.append(static_label(rom,so,UIT['urara'],15,11,5,sp,align='r',blank=False))
    lists['ResultLabels']=L
    t_q=0xC0                     # rank-kanji tiles C0-CF (unused: rank drawn into B2-BF; digits D2-DB kept)
    quests=[]
    for i in range(6):
        q=alt.get('quest_%d'%i) or en('quest_%d'%i)
        if ptext.width(q)>16*8: q=en('quest_%d'%i)
        quests.append(q)
    tables['QuestRecs']=[dyn_label(q,16,t_q,maddr(10,2)) for q in quests]
    consts['NUM_QUEST']=6

    # ============ game over (03:4F16: "geemu oobaa" 10 cells at $9905)
    lists['GameOverLabels']=[dyn_label(UIT['gameover'],10,0x3C,maddr(8,5),align='c')]

    # ============ password screen (03:6961 tilemap; LCDC $8800; portraits use tiles 40-4E, 50-5E, E0-EE)
    po=off(3,0x6961)
    # glyph alphabet in grid reading order over the original code positions
    grid=[]
    for r in (8,10,12,14):
        for c in range(1,19):
            v=orig[po+r*20+c]
            if v<=0x36: grid.append(v)
    assert sorted(grid)==list(range(0x37)), 'password grid codes'
    ALPHA=list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')+list('34679')+list('abdefghijkmnqrty')+list('#%&+=$</')
    assert len(ALPHA)==55 and len(set(ALPHA))==55
    code2ch={code:ALPHA[i] for i,code in enumerate(grid)}
    code2ch.update({0x70:'?',0x71:'!',0x72:'-',0x73:'.',0x74:'♡',0x75:'♪',0x76:'💧',0x77:'>',0x7B:'*'})
    def gtile(ch):
        px,w,adv=ptext.glyph(ch,True)
        x0=(8-w)//2
        cv=[[0]*8 for _ in range(8)]
        for y in range(8):
            for x in range(w):
                if px[y][x]: cv[y][x0+x]=1
        return ptext.to_tiles(cv)
    gl=b''.join(gtile(code2ch[c]) for c in range(0x37))
    PL=[rec(OUT.blob(gl,'pwglyphs'),vram_tile(0),0x37,0,0,0x37),
        rec(OUT.blob(gtile('>')),vram_tile(0x77),1,0x77,0,1),
        rec(OUT.blob(gtile('*')),vram_tile(0x7B),1,0x7B,0,1)]
    # decoration ◯ (original 7B art from the font) -> tile 5F
    PL.append(rec(OUT.blob(ofont[0x7B*16:0x7C*16]),vram_tile(0x5F),1,0x5F,0,1))
    for c in (2,17):
        assert orig[po+4*20+c]==0x7B; rom[po+4*20+c]=0x5F
    pp=Pool('pw_title',[(0x37,0x3F)])
    r_title=static_label(rom,po,pwt,4,4,12,pp,align='c')
    pe=Pool('pw_end',[(0x60,0x62)])
    r_end=static_label(rom,po,UIT['pw_end'],16,13,3,pe,align='l')
    PL+= [r_title,r_end]
    lists['PwLabels']=PL
    lists['PwRedraw']=[r_title]
    # error rows (window $9D01 / $9D41, 18 cells): regular weight to fit the tile budget
    def err_rec(text,t0,mp,pool_n):
        W=ptext.width(text,False); n=(W+7)//8
        assert n<=pool_n,(text,n,pool_n)
        x0=(18*8-W)//2; c0=x0//8; n=((x0-c0*8)+W+7)//8
        cv,_=ptext.canvas(text,n,align='l',bold=False,xoff=x0-c0*8)
        return rec(OUT.blob(ptext.to_tiles(cv)),vram_tile(t0),n,t0,mp+c0,n)
    lists['PwErrLabels']=[err_rec(err1,0x37,0x9D01,9),err_rec(err2,0x63,0x9D41,13)]
    xl=[0x20]*128
    for c,ch in code2ch.items():
        xl[c]={'♡':0x80,'♪':0x81,'💧':0x82}.get(ch,ord(ch))
    consts_pw=xl
    json.dump({'%02X'%c:ch for c,ch in sorted(code2ch.items())},open(os.path.join(GEN,'pw_alphabet.json'),'w'),ensure_ascii=False,indent=0)

    # ============ title menu (sprites from the OBJ font copy at $8000; 6 sprites per item at 04:4B33/4B39)
    obj=bytearray(ofont)
    nt=ptext.tiles(UIT['new'],6,align='l',xoff=2); ct=ptext.tiles(UIT['cont'],6,align='l',xoff=2)
    obj[0:6*16]=nt; obj[6*16:12*16]=ct
    import logo
    logo_t=logo.to_tiles(logo.render2(gap=0.6,tw=122,th=19))
    COPY=bytes.fromhex('7e3cc342bd99a5a5a1a1bd99c3427e3c')       # original (c) tile 80 (title VRAM)
    ctext='Min Ayahana/Shueisha/TV Tokyo/NAS'
    px,W=ptext.render(ctext,bold=False,space=2)
    assert W<=19*8,W
    cv=[[0]*(19*8) for _ in range(8)]
    for y in range(8):
        for x in range(W):
            if px[y][x]: cv[y][x]=1
    copy_t=COPY+ptext.to_tiles(cv)
    lists['TitleLabels']=[rec(OUT.blob(logo_t,'logo'),0x9500,48,0x50,0,16),
                          rec(OUT.blob(copy_t,'copyright'),vram_tile(0),20,0,maddr(14,0),20)]

    # ------------------------------------------------------------ generate asm data
    os.makedirs(GEN,exist_ok=True)
    A=[]
    def recline(r):
        return '    db BANK(%s)\n    dw %s, $%04X\n    db %d, $%02X\n    dw $%04X\n    db %d'%(r['blob'],r['blob'],r['vram'],r['n'],r['t0'],r['map'],r['cols'])
    A.append('SECTION "ui_data", ROMX, BANK[UI_BANK]')
    for k,v in consts.items(): A.insert(0,'DEF %s EQU %d'%(k,v))
    for name,L in lists.items():
        A.append('%s::'%name)
        for r in L: A.append(recline(r))
        A.append('    db $FF')
    for name,L in tables.items():
        A.append('%s::'%name)
        A.append('    dw '+', '.join('.r%d'%i for i in range(len(L))))
        for i,r in enumerate(L): A.append('.r%d'%i); A.append(recline(r))
    A.append('PwXlat::'); A.append('    db '+', '.join('$%02X'%v for v in consts_pw))
    objlz=compress(bytes(obj)); assert decompress(objlz,0,0x800)[0]==bytes(obj)
    open(os.path.join(GEN,'objfont.lz'),'wb').write(objlz)
    A.append('ObjFontLZ::'); A.append('    INCBIN "tmp/gen/objfont.lz"')
    # tile blobs: banks 19h.. (8 KB+ of item names)
    bank=0x19; used=0
    for name,data in OUT.blobs:
        p=os.path.join(GEN,name+'.bin'); open(p,'wb').write(data)
        if used+len(data)>0x3F00 or used==0:
            if used: bank+=1
            used=0; A.append('SECTION "ui_tiles_%02X_%s", ROMX, BANK[$%02X]'%(bank,name,bank))
        A.append('%s:: INCBIN "tmp/gen/%s.bin"'%(name,name)); used+=len(data)
    assert bank<=0x1F
    open(os.path.join(GEN,'data.asm'),'w').write('\n'.join(A)+'\n')

    # ------------------------------------------------------------ assemble
    t=os.path.join(UI,'tmp')
    subprocess.run([paths.tool('rgbasm'),'-I',T+os.sep,'-o',t+'/ui.o',os.path.join(T,'src','ui.asm')],cwd=UI,check=True)
    subprocess.run([paths.tool('rgblink'),'-o',t+'/ui.gb','-n',t+'/ui.sym','-m',t+'/ui.map',t+'/ui.o'],cwd=UI,check=True)
    img=open(t+'/ui.gb','rb').read(); sym={}
    for ln in open(t+'/ui.sym'):
        mm=re.match(r'([0-9A-Fa-f]+):([0-9A-Fa-f]+) (\S+)',ln)
        if mm: sym[mm.group(3)]=(int(mm.group(1),16),int(mm.group(2),16))
    def S_(n): return sym[n][1]
    # bank 0 sections (assert originals)
    b0=[(0x1434,0x14E7,None),(0x1A06,0x1A3C,None),(0x3F30,0x3F33,bytes.fromhex('060e21')),(0x1A00,0x1A03,bytes.fromhex('3e04ea')),(0x2D86,0x2D89,bytes.fromhex('010001'))]
    assert orig[0x1434:0x1437]==bytes.fromhex('21e714')
    # engine wrote $1496 (bank) / $14A1-2 (short table) inside this range: accepted
    for a0,a1,exp in b0:
        if exp is not None: put(rom,a0,b'',exp,'b0 %04X'%a0)
        rom[a0:a1]=img[a0:a1]          # assembled code + 00 padding (unreachable)
    # keep the HUD list at $14E7 untouched (asserted)
    assert rom[0x14E7:0x14F0]==orig[0x14E7:0x14F0]
    for b in range(UI_BANK,0x20):
        o=b*0x4000
        if o+0x4000<=len(img): rom[o:o+0x4000]=img[o:o+0x4000]
    # call-site patches
    def callpatch(b,a,orig_target,stub):
        o=off(b,a); put(rom,o,[0xCD,S_(stub)&0xFF,S_(stub)>>8],[0xCD,orig_target&0xFF,orig_target>>8],'%02X:%04X'%(b,a))
    put(rom,0x1913,[0xCD,S_('Stub_Report')&0xFF,S_('Stub_Report')>>8,0,0,0],bytes.fromhex('21831acda204'),'report list')
    callpatch(0,0x196E,0x32BC,'Stub_RankWord')
    callpatch(3,0x4E24,0x2DA5,'Stub_Result')
    callpatch(3,0x4E61,0x32BC,'Stub_Quest')
    callpatch(3,0x4F25,0x32BC,'Stub_GameOver')
    callpatch(4,0x4439,0x0316,'Stub_PwInit')
    callpatch(4,0x451D,0x32BC,'Stub_PwErr')
    put(rom,off(4,0x4526),[0,0,0],bytes.fromhex('cdbc32'),'pw err row2')
    callpatch(4,0x453C,0x0354,'Stub_PwErrDone')
    callpatch(4,0x423A,0x2D91,'Stub_Title')
    # title: OBJ font copy -> UI bank block; menu sprite codes
    put(rom,0x2D92,[UI_BANK],[0x03],'obj font bank'); lz=S_('ObjFontLZ')
    put(rom,0x2D9E,[lz&0xFF,lz>>8],[0x76,0x59],'obj font addr')
    put(rom,off(4,0x4B33),list(range(12)))
    # stamps (results): 02:7A6A pass, 02:7B6A fail (16 tiles each, 4x4)
    import stamps
    for a_,kind in ((0x7A6A,'pass'),(0x7B6A,'fail')):
        o=off(2,a_); data=stamps.make(kind,orig[o:o+256]); put(rom,o,data,orig[o:o+256],'stamp '+kind)
    # results: 2-tile word after the key press (03:4EF8 -> $9909 from table 03:4F42, 6 quests): blank
    put(rom,off(3,0x4F42),[0xFF]*12,orig[off(3,0x4F42):off(3,0x4F42)+12],'results 2-tile words')
    # dungeon exit sign deiriguchi (raw 4x2 tiles 02:7EE1) -> EXIT
    import sfx_art
    from lz2 import decompress as dec2
    o=off(2,0x7EE1); put(rom,o,exit_sign(orig[o:o+128]),orig[o:o+128],'exit sign')
    # battle defeat burst (OBJ stream 0B:7AF0, 0x140 bytes, 328 compressed) -> BOOM!, in place
    o=off(0xB,0x7AF0); z,c=dec2(orig,o,0x140); assert c==328
    lz=compress(sfx_art.burst_data(sfx_art.edit_burst(sfx_art.burst_img(z)))); assert len(lz)<=c,len(lz)
    put(rom,o,lz,orig[o:o+len(lz)],'burst')
    # Holy Falls sign (OBJ stream 0B:6D3D, 0x40 bytes, 57 compressed): taki -> water-drop mark, in place
    o=off(0xB,0x6D3D); z,c=dec2(orig,o,0x40); assert c==57
    lz=compress(sfx_art.sign_data(sfx_art.edit_sign(sfx_art.sign_img(z)))); assert len(lz)<=c,len(lz)
    put(rom,o,lz,orig[o:o+len(lz)],'falls sign')
    # ending illustrations: SFX re-lettered, recompressed IN PLACE (the picture record's bank is also used for the
    # tilemap commands that follow, so the stream must stay in its bank; the new streams are smaller)
    # picture tiles and their tilemap are decompressed from the original ROM here (record: bank, len, src, then
    # tilemap commands; the decoder runs with a 0x900-byte zero prefix like the game's $8000-based window)
    for nm,ro in sfx_art.PICS.items():
        tm=sfx_art.record_tilemaps(orig,ro)[0][1]
        b0,ln,src=orig[ro],orig[ro+1]|orig[ro+2]<<8,orig[ro+3]|orig[ro+4]<<8
        assert '%02X_%04X'%(b0,src)==nm[-7:],nm
        oo=off(b0,src); data,used=dec2(orig,oo,ln,bytes(0x900))
        assert len(data)==ln,nm
        new=sfx_art.decompose(data,tm,sfx_art.edit_picture(nm,sfx_art.compose(data,tm)))
        lz=compress(new); assert dec2(lz,0,len(new))[0]==new and len(lz)<=used,(nm,len(lz),used)
        put(rom,oo,lz,orig[oo:oo+len(lz)],'picture '+nm)
    # SGB border (bank 0D) - assert untouched by the engine, then English edits
    o=0xD*0x4000-0x4000
    assert rom[o+0x4000:o+0x6800]==orig[o+0x4000:o+0x6800], 'SGB border changed before the UI build'
    import sgb_en
    sgb_en.apply(rom)
    # checksums
    c=0
    for i in range(0x134,0x14D): c=(c-rom[i]-1)&0xFF
    rom[0x14D]=c; g=(sum(rom)-rom[0x14E]-rom[0x14F])&0xFFFF; rom[0x14E]=g>>8; rom[0x14F]=g&0xFF
    open(a.out,'wb').write(rom)
    print('wrote %s md5 %s'%(a.out,hashlib.md5(rom).hexdigest()))
    print('blobs %d bytes; report pool left %d; results pool left %d'%(OUT.blobbytes,len(rp.free),len(sp.free)))
    print('items:',items)
    print('quests:',quests,' pw:',pwt,'|',err1,'|',err2)
main()
