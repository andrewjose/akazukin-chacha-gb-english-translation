"""Akazukin Chacha (GB) English build: VWF engine + text insertion + layout.

python3 -I tools/build.py [--tr FILE_OR_DIR ...] [--out OUT.gb] [--placeholder] [--test TEST.json]

Input: merged translation JSON list(s) [{id, en, (short8)}] (the repo build.py writes $CHACHA_WORK/tl/merged.json).
Paths: see tools/common/paths.py (CHACHA_ROM, CHACHA_WORK, CHACHA_STRINGS, RGBDS_DIR).
  --test FILE : extra {id: en} or [{id,en}] overrides (applied last; used by the runtime tests).
  --placeholder : dialogue without a translation gets "[dlg_XXX]" + its control tokens (else: error).
Output: OUT.gb (512 KB), $CHACHA_WORK/engine/layout.json (every laid-out dialogue page, for typeset_check.py), build report on stdout.

Pipeline
 1. font assets (make_font.py) + VWF asm (src/vwf.asm, rgbds)
 2. dialogue (+ CALL-reachable orphans) -> tokens -> measured, balanced line breaking, page splitting
    -> bytes (ASCII = VWF codes, 80 heart, 81 note, 82 drop, EF-FE controls) -> banks 10h-16h,
    per-ID pointer table 10:$4000 + bank table 10:$4AB2.
 3. nick/item/name tables rebuilt in bank 17h (any length). (Hand slots: UI layer.)
 4. fixed UI fields (cmd, fixed, quest) in place with the fixed 8x8 encoding (font/fixed.tbl).
 5. font block LZ (bank 17h) + $9000 load repoint, mirror of 03:$5F23 for the $8800 load.
"""
import sys,os,json,re,glob,argparse,hashlib,subprocess
T=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,T)
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','common')); import paths
E=paths.ENGINE_WORK     # generated fonts (font/), layout, default output
from lz import compress,decompress
import asm

ORIG_MD5=paths.ORIG_MD5
STRINGS=paths.STRINGS
TL_OUT=os.path.join(paths.WORK,'tl')
MASTER_N=0x559
DLG_BANK0=0x10; DLG_BANK_LAST=0x16; VWF_BANK=0x17
PT=0x4000; BT=0x4000+MASTER_N*2
LINE_PX=120; ROWS=4; SPACE_W=None
CTRL={'END':0xEF,'SCROLL':0xF0,'SHAKE':0xF1,'CLR':0xF2,'WAIT':0xF3,'NICK':0xF4,'NICK2':0xF5,'ITEM':0xF6,'ITEM2':0xF7,
      'NAMEC8D3':0xF8,'FA':0xFA,'PAUSE':0xFC,'PASSWORD':0xFD,'NL':0xFE}
VARS={'NICK':'nick','NICK2':'nick','ITEM':'item','ITEM2':'item','NAMEC8D3':'name'}
SPECIAL={'<HEART>':0x80,'<NOTE>':0x81,'{drop}':0x82}
TOKRE=re.compile(r'<[^>]*>|\{[^}]*\}')

def off(b,a): return a if a<0x4000 else b*0x4000+a-0x4000

# ------------------------------------------------------------------ font metrics
WID=open(os.path.join(E,'font','vwf_widths.bin'),'rb').read() if os.path.exists(os.path.join(E,'font','vwf_widths.bin')) else None
def cw(code): return WID[code-0x20] if 0x20<=code<=0x82 else 0

# ------------------------------------------------------------------ tokenizer
class Enc:
    """VWF text -> list of elements"""
    def __init__(s,varw): s.varw=varw
    def parse(s,text,ctx):
        text=text.replace('\n','')
        el=[];i=0
        for m in list(TOKRE.finditer(text))+[None]:
            j=m.start() if m else len(text)
            for ch in text[i:j]:
                o=ord(ch)
                if ch==' ': el.append(('sp',))
                elif 0x21<=o<=0x7E: el.append(('ch',o))
                else: raise ValueError('%s: character %r not in the VWF font'%(ctx,ch))
            if not m: break
            t=m.group(0); i=m.end()
            if t in SPECIAL: el.append(('ch',SPECIAL[t])); continue
            name=t[1:-1]; arg=None
            if ':' in name: name,arg=name.split(':',1)
            if name=='FACE': el.append(('z',[0xF9,int(arg,16)]))
            elif name=='CALL': el.append(('call',arg))
            elif name=='HEX': el.append(('z',list(bytes.fromhex(arg))))
            elif name in ('NL',): el.append(('nl',))
            elif name=='SCROLL': el.append(('scroll',))
            elif name=='CLR': el.append(('clr',))
            elif name=='END': el.append(('end',))
            elif name in VARS: el.append(('var',CTRL[name],s.varw[VARS[name]]))
            elif name in CTRL: el.append(('z',[CTRL[name]]))
            else: raise ValueError('%s: unknown token %s'%(ctx,t))
        return el

# ------------------------------------------------------------------ words / runs
def words_of(els):
    """elements of one run (no structural) -> list of words; word = dict(items, w, text, kind)"""
    words=[];cur=[];lead=0;seen_word=False
    def flush():
        nonlocal cur
        if cur: words.append(cur); cur=[]
    for e in els:
        if e[0]=='sp': flush(); words.append(None)   # None = space marker
        else: cur.append(e)
    flush()
    # group: list of (leading_spaces_count, word elements)
    out=[];sp=0
    for w in words:
        if w is None: sp+=1; continue
        out.append([sp,w]); sp=0
    trailing=sp
    # zero-width-only words (e.g. " <PAUSE> ") glue to the next word (or the previous one at the end)
    res=[]
    k=0
    while k<len(out):
        sp,w=out[k]
        if all(e[0]=='z' for e in w):
            if k+1<len(out): out[k+1]=[sp,w+out[k+1][1]]; k+=1; continue
            if res: res[-1][1]=res[-1][1]+w; k+=1; continue
        res.append([sp,w]); k+=1
    W=[]
    for sp,w in res:
        width=0;items=[];txt=''
        for e in w:
            if e[0]=='ch': width+=cw(e[1]); items.append(e[1]); txt+=chr(e[1]) if e[1]<0x80 else {0x80:'♥',0x81:'♪',0x82:'💧'}[e[1]]
            elif e[0]=='var': width+=e[2]; items.append(e[1]); txt+='{%s}'%{0xF4:'NICK',0xF5:'NICK2',0xF6:'ITEM',0xF7:'ITEM2',0xF8:'NAME'}[e[1]]
            elif e[0]=='z': items+=e[1]
        W.append(dict(sp=sp,items=items,w=width,text=txt,els=w))
    return W,trailing

_pyphen=None
def hyph_pieces(word):
    """split a plain word at pyphen points (>=3 chars each side) -> list of (items,w,text) pieces or None"""
    global _pyphen
    t=word['text']
    if not re.fullmatch(r"[A-Za-z]{6,}[.,!?;:'\"]*",t): return None
    core=re.match(r'[A-Za-z]+',t).group(0)
    if _pyphen is None:
        import pyphen; _pyphen=pyphen.Pyphen(lang='en_US')
    pos=[p for p in _pyphen.positions(core) if p>=3 and len(core)-p>=3]
    if not pos: return None
    # map char positions to element indices (word may carry zero-width controls)
    els=word['els']; cuts=[];n=0
    for idx,e in enumerate(els):
        if e[0]=='ch':
            if n in pos: cuts.append(idx)
            n+=1
    return cut_word(els,cuts)

def cut_word(els,cuts):
    pieces=[];a=0
    for c in cuts+[len(els)]:
        seg=els[a:c]; a=c
        it=[]
        for e in seg:
            if e[0]=='ch': it.append(e[1])
            elif e[0]=='z': it+=e[1]
            elif e[0]=='var': it.append(e[1])
        pieces.append(dict(items=it,w=sum(cw(e[1]) if e[0]=='ch' else e[2] if e[0]=='var' else 0 for e in seg),
                           text=''.join(chr(e[1]) for e in seg if e[0]=='ch' and e[1]<0x80)))
    return pieces

def explicit_hyphen_pieces(word):
    els=word['els']; ch=[i for i,e in enumerate(els) if e[0]=='ch']
    cuts=[i+1 for k,i in enumerate(ch) if els[i]==('ch',0x2D) and 0<k<len(ch)-1]
    return cut_word(els,cuts) if cuts else None

def break_run(words,p0,hyph):
    """balanced breaking of one run (minimum lines, then minimum squared slack, no stranded last word).
    p0 = pen when the run continues an existing line (after a CALL). returns list of lines;
    line = list of (piece, glue_before, word_index); glue 'hy' = hyphenation point."""
    SW=cw(0x20); HW=cw(0x2D)
    pieces=[]
    for wi,w in enumerate(words):
        hp=hyph_pieces(w) if hyph else None
        xp=explicit_hyphen_pieces(w)
        if hp:
            for k,p in enumerate(hp): pieces.append((p,'sp' if k==0 else 'hy',wi))
        elif xp:
            for k,p in enumerate(xp): pieces.append((p,'sp' if k==0 else 'hx',wi))
        else: pieces.append((dict(items=w['items'],w=w['w'],text=w['text']),'sp',wi))
    n=len(pieces)
    if n==0: return [[]]
    def dp(cap_first):
        INF=float('inf'); best=[(INF,None)]*(n+1); best[0]=(0,None)
        for i in range(n):
            if best[i][0]==INF: continue
            cap=cap_first if i==0 else LINE_PX
            width=0
            for j in range(i,n):
                p,g,_=pieces[j]
                if j>i and g=='sp': width+=SW
                width+=p['w']
                endhy=(j+1<n and pieces[j+1][1]=='hy')
                tw=width+(HW if endhy else 0)
                last=(j==n-1)
                if tw>cap and j>i: break
                c=1_000_000+max(0,tw-cap)*10_000_000
                if not last: c+=(cap-tw)**2 if tw<=cap else 0
                if endhy: c+=6000
                if j+1<n and pieces[j+1][1]=='hx': c+=2500
                if last and i>0 and len({pieces[k][2] for k in range(i,j+1)})==1 and pieces[i][1]=='sp':
                    c+=40000 if tw<LINE_PX*0.4 else 15000
                tot=best[i][0]+c
                if tot<best[j+1][0]: best[j+1]=(tot,i)
        lines=[];j=n
        while j>0:
            i=best[j][1]; lines.append(pieces[i:j]); j=i
        return lines[::-1],best[n][0]
    if p0<=0: return dp(LINE_PX)[0]
    la,ca=dp(LINE_PX-p0-SW)
    lb,cb=dp(LINE_PX)
    if ca<=cb+1_000_000 and line_width(la[0])<=LINE_PX-p0-SW: return la
    return [[]]+lb

def break_run_ind(words,ind,hyph):
    global LINE_PX
    if not ind: return break_run(words,0,hyph)
    save=LINE_PX; LINE_PX=save-ind
    try: return break_run(words,0,hyph)
    finally: LINE_PX=save

def line_text(line):
    s=''
    for k,(p,g,_) in enumerate(line):
        if k and g=='sp': s+=' '
        s+=p['text']
        if k+1<len(line) and line[k+1][1]=='hy': pass
    return s

def line_width(line,next_is_hy=False):
    SW=cw(0x20); w=0
    for k,(p,g,_) in enumerate(line):
        if k and g=='sp': w+=SW
        w+=p['w']
    return w

class Layout:
    def __init__(s,enc,callee_info,ctx):
        s.enc=enc; s.ci=callee_info; s.ctx=ctx
    def layout_page(s,els,hyph,start_pen=0):
        """els: elements of one page (no clr). returns (rows: list of row dicts, out items, info)"""
        rows=[dict(text='',w=0,parts=[])]
        out=[]; info=dict(hyph=0,stranded=[],overflow=[],virtual=0,scroll_src=False)
        pen=start_pen; run=[]; endkind_prev=['start']
        SW=cw(0x20); HW=cw(0x2D)
        def newrow(kind):
            rows.append(dict(text='',w=0,parts=[],brk=kind))
        def emit_run(run,endkind):
            nonlocal pen
            words,trail=words_of(run)
            if not words:
                return
            p0=pen
            if endkind_prev[0]=='scroll': words[0]['sp']=0
            if p0==0 and words[0]['sp']:   # indentation after a hard break
                ind=words[0]['sp']*SW
            else: ind=0
            lines=break_run(words,p0,hyph) if p0>0 else break_run_ind(words,ind,hyph)
            if p0==0 and ind:
                out.extend([0x20]*words[0]['sp']); rows[-1]['w']+=ind; rows[-1]['text']+=' '*words[0]['sp']
            for li,line in enumerate(lines):
                if li>0:
                    out.append(('BRK','soft')); newrow('soft'); pen=0
                if li==0 and p0>0 and line:
                    out.append(0x20); pen+=SW; rows[-1]['w']+=SW; rows[-1]['text']+=' '
                for k,(p,g,_) in enumerate(line):
                    if k and g=='sp': out.append(0x20); pen+=SW; rows[-1]['text']+=' '
                    out.extend(p['items']); pen+=p['w']; rows[-1]['text']+=p['text']
                    if k+1<len(line) and line[k+1][1]=='hy': pass
                if li+1<len(lines) and lines[li+1] and lines[li+1][0][1]=='hy':
                    out.append(0x2D); pen+=HW; rows[-1]['text']+='-'; info['hyph']+=1
                rows[-1]['w']=pen
                if pen>LINE_PX: info['overflow'].append(rows[-1]['text'])
            if len(lines)>1 and lines[-1] and len({x[2] for x in lines[-1]})==1 and lines[-1][0][1]=='sp':
                info['stranded'].append(line_text(lines[-1]))
        for e in els+[('eop',)]:
            if e[0] in ('nl','scroll','call','eop','end'):
                emit_run(run,e[0]); run=[]; endkind_prev[0]=e[0]
                if e[0] in ('nl','scroll'):
                    if e[0]=='scroll': info['scroll_src']=True
                    out.append(('BRK','hard')); newrow('hard'); pen=0
                elif e[0]=='call':
                    ci=s.ci(e[1])
                    if ci is None:
                        out.append(('CALL',e[1])); continue
                    first_w=ci['first_w']
                    if ci['clr']:
                        out.append(('CALL',e[1])); out.append(('VROWS',len(ci['rows_text'])-1))
                        rows=[dict(text=t,w=0,parts=[],brk='virtual') for t in ci['rows_text']] or [dict(text='',w=0,parts=[])]
                        pen=0 if ci['ends_nl'] else ci['end_pen']; rows[-1]['w']=pen; continue
                    start=pen
                    if pen>0:
                        # callee starts mid-line (caller text before the CALL): keep it on this line with a word gap
                        # if its first row fits, else break the line before the CALL
                        if pen+SW+first_w<=LINE_PX:
                            out.append(0x20); pen+=SW; rows[-1]['text']+=' '; start=pen
                        else:
                            out.append(('BRK','soft')); newrow('soft'); pen=0; start=0
                            info.setdefault('warn',[]).append('CALL mid-line: line broken before the call')
                    out.append(('CALL',e[1])); out.append(('VROWS',len(ci['rows_text'])-1))
                    rows[-1]['text']+=ci['rows_text'][0] if ci['rows_text'] else ''
                    rows[-1]['w']=start+first_w
                    if rows[-1]['w']>LINE_PX: info['overflow'].append(rows[-1]['text'])
                    for t in ci['rows_text'][1:]:
                        rows.append(dict(text=t,w=0,parts=[],brk='virtual'))
                    if len(ci['rows_text'])==1: pen=start+ci['end_pen']
                    else: pen=ci['end_pen']
                    rows[-1]['w']=pen
                    if ci['ends_nl']: pen=0
                elif e[0]=='end': out.append(0xEF)
            else: run.append(e)
        return rows,out,info

def assign_breaks(rows,out,allow_scroll):
    """turn ('BRK',kind) markers into NL/SCROLL bytes. returns (bytes list, max_row_overflow)"""
    r=0;res=[];over=0;ri=0
    for x in out:
        if isinstance(x,tuple) and x[0]=='VROWS':
            r=min(r+x[1],ROWS-1) if allow_scroll else r+x[1]; continue
        if isinstance(x,tuple) and x[0]=='BRK':
            if r+1<ROWS: r+=1; res.append(0xFE)
            elif allow_scroll: res.append(0xF0)
            else: r+=1; over=max(over,r+1-ROWS); res.append(0xFE)
        else: res.append(x)
    return res,over

def count_rows(rows):
    # rows that hold visible text (trailing empty rows from a final hard NL don't count)
    n=len(rows)
    while n>1 and rows[n-1]['text'].strip()=='' : n-=1
    return n

def split_points(els):
    """indices of 'sp' elements usable as page splits: (idx, priority)  0 = sentence end, 1 = clause, 2 = any"""
    pts=[]
    for i,e in enumerate(els):
        if e[0]!='sp': continue
        # previous visible char
        j=i-1
        while j>=0 and els[j][0]=='z': j-=1
        if j<0 or els[j][0]=='sp': continue
        prev=els[j]
        ch=chr(prev[1]) if prev[0]=='ch' and prev[1]<0x80 else ''
        k=j
        if ch in '"\')' and k>0 and els[k-1][0]=='ch': ch=chr(els[k-1][1]) if els[k-1][1]<0x80 else ''
        waited=any(els[x][0]=='z' and 0xF3 in els[x][1] for x in range(j+1,i))
        pri=0 if (ch in '.!?' or waited or prev==('ch',0x80) or prev==('ch',0x81)) else 1 if ch in ',;:' else 2
        if ch=='.' and j>=2 and els[j-1]==('ch',ord('r')) and els[j-2]==('ch',ord('M')): pri=2   # "Mr." is not a sentence end
        pts.append((i,pri))
    return pts

# boxes that are not the standard 15x4 dialogue box (report card, $00:1990: message C915*2 at (1,14), +1 at (6,9);
# dlg_00C = partner name at (13,3)). width in px, rows.
BOXSPEC={}
for _i in range(0,12,2): BOXSPEC['dlg_%03X'%_i]=(120,3); BOXSPEC['dlg_%03X'%(_i+1)]=(104,1)
BOXSPEC['dlg_00C']=(48,1)

def layout_string(sid,text,L,report):
    global LINE_PX,ROWS
    save=(LINE_PX,ROWS); LINE_PX,ROWS=BOXSPEC.get(sid,(120,4))
    try: return _layout_string(sid,text,L,report)
    finally: LINE_PX,ROWS=save

def _layout_string(sid,text,L,report):
    """full layout of one dialogue string -> list of byte items (ints / ('CALL',x))"""
    els=L.enc.parse(text,sid)
    pages=[[]]
    for e in els:
        if e[0]=='clr': pages.append([])
        else: pages[-1].append(e)
    out=[];rep=dict(id=sid,pages=[],splits=[],hyph=0,stranded=[],overflow=[],warn=[])
    first=True
    queue=list(pages)
    pi=0
    while queue:
        pg=queue.pop(0)
        if not first: out.append(0xF2)
        first=False
        scroll_src=any(e[0]=='scroll' for e in pg)
        rows,o,info=L.layout_page(pg,False)
        nrows=count_rows(rows)
        if nrows>ROWS and not scroll_src:
            rows2,o2,info2=L.layout_page(pg,True)
            if count_rows(rows2)<=ROWS:
                rows,o,info=rows2,o2,info2; nrows=count_rows(rows)
            elif sid in BOXSPEC:
                pass   # fixed screen layout (no WAIT possible): reported as overflow, translator must shorten
            else:
                # split at the latest point that makes page 1 fit; prefer sentence ends
                pts=split_points(pg); done=False
                for pri in (0,1,2):
                    cand=[i for i,p in pts if p<=pri]
                    for i in reversed(cand):
                        r1,_,_=L.layout_page(pg[:i],False)
                        if count_rows(r1)<=ROWS:
                            head=pg[:i]
                            if not any(x[0]=='z' and 0xF3 in x[1] for x in head[-3:]): head=head+[('z',[0xF3])]
                            queue.insert(0,pg[i+1:]); rows,o,info=L.layout_page(head,False); nrows=count_rows(rows)
                            rep['splits'].append(dict(kind=['sentence','clause','word'][pri],at=''.join(' ' if x[0]=='sp' else chr(x[1]) for x in pg[max(0,i-40):i] if x[0]=='sp' or x[0]=='ch' and x[1]<0x80)))
                            done=True; break
                    if done: break
        b,over=assign_breaks(rows,o,scroll_src)
        out.extend(b)
        rep['pages'].append([dict(text=r['text'],w=r['w'],brk=r.get('brk','start')) for r in rows])
        rep['box']=[LINE_PX,ROWS]
        rep['hyph']+=info['hyph']; rep['stranded']+=info['stranded']; rep['overflow']+=info['overflow']; rep['warn']+=info.get('warn',[])
        if count_rows(rows)>ROWS and not scroll_src: rep['overflow'].append('page has %d rows'%count_rows(rows))
        rep.setdefault('scroll',False); rep['scroll']|=scroll_src
    report.append(rep)
    return out,rep

# ------------------------------------------------------------------ fixed encoding
def load_fixed():
    m={}
    for ln in open(os.path.join(E,'font','fixed.tbl')):
        ln=ln.rstrip('\n')
        if not ln or ln[0]=='#': continue
        k,_,v=ln.partition('='); m[v]=int(k,16)
    return m
def enc_fixed(text,fx,ctx,errs,roww=18):
    if '<NL>' in text:   # multi-row tilemap field (pw_error): each row padded to roww cells, trailing <HEX> kept raw
        out=[]
        for part in text.split('<NL>'):
            m=re.search(r'(<HEX:[0-9a-fA-F]+>)+$',part); tail=m.group(0) if m else ''
            body=part[:len(part)-len(tail)]
            e=enc_fixed(body,fx,ctx,errs); out+=e+[0xFF]*max(0,roww-len(e))
            if tail: out+=enc_fixed(tail,fx,ctx,errs)
        return out
    out=[];i=0
    for m in list(TOKRE.finditer(text))+[None]:
        j=m.start() if m else len(text)
        for ch in text[i:j]:
            if ch in fx: out.append(fx[ch])
            elif ch.upper() in fx: out.append(fx[ch.upper()]); errs.append('%s: %r not in fixed font, used uppercase'%(ctx,ch))
            else: out.append(0xFF); errs.append('%s: %r not in fixed font -> blank'%(ctx,ch))
        if not m: break
        t=m.group(0); i=m.end()
        if t.startswith('<HEX:'): out+=list(bytes.fromhex(t[5:-1]))
        elif t=='<END>': out.append(0xEF)
        elif t in fx: out.append(fx[t])
        else: errs.append('%s: token %s not allowed in fixed text'%(ctx,t))
    return out

# ------------------------------------------------------------------ main
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--tr',nargs='*'); ap.add_argument('--out',default=os.path.join(E,'out','chacha_en.gb'))
    ap.add_argument('--placeholder',action='store_true'); ap.add_argument('--test')
    ap.add_argument('--layout',default=os.path.join(E,'layout.json'))
    a=ap.parse_args()
    global WID
    subprocess.run([sys.executable,'-I',os.path.join(T,'make_font.py')],check=True,stdout=subprocess.DEVNULL)
    ORIG=paths.rom_path()
    WID=open(os.path.join(E,'font','vwf_widths.bin'),'rb').read()
    orig=open(ORIG,'rb').read(); assert hashlib.md5(orig).hexdigest()==ORIG_MD5
    rom=bytearray(orig)+bytes([0xFF])*(0x80000-len(orig)); rom[0x148]=0x04
    S=json.load(open(STRINGS)); byid={x['id']:x for x in S}
    for x in S:
        for al in x['aliases']: byid[al]=x
    # translations
    files=[]
    for p in (a.tr or [TL_OUT]):
        files+=sorted(glob.glob(os.path.join(p,'*.json'))) if os.path.isdir(p) else [p]
    tr={};short={}
    for f in files:
        for x in json.load(open(f)):
            tr[x['id']]=x['en']
            if x.get('short8'): short[x['id']]=x['short8']
    if a.test:
        t=json.load(open(a.test))
        if isinstance(t,list): t={x['id']:x['en'] for x in t}
        tr.update(t)
    errs=[];warns=[]
    fx=load_fixed()
    # ---- name tables (VWF encoding) -> variable widths
    enc0=Enc({'nick':0,'item':0,'name':0})
    tables={}
    for blk in ('nick','item','name'):
        for x in S:
            if x['block']!=blk: continue
            t=tr.get(x['id'])
            if t is None: errs.append('%s: no translation'%x['id']); t='?<END>'
            els=enc0.parse(t,x['id'])
            items=[]
            for e in els:
                if e[0]=='ch': items.append(e[1])
                elif e[0]=='sp': items.append(0x20)
                elif e[0]=='end': pass
                else: errs.append('%s: control token in a name string'%x['id'])
            tables[x['id']]=items
    def wmax(blk): return max(sum(cw(c) for c in v) for k,v in tables.items() if byid[k]['block']==blk)
    varw={'nick':wmax('nick'),'item':wmax('item'),'name':wmax('name')}
    enc=Enc(varw)
    # ---- dialogue strings
    dlg=[x for x in S if x['block'] in ('dlg','orphan')]
    addr2rec={(x['bank'],int(x['addr'][1:],16)):x for x in S}
    def resolve(arg,caller):
        if arg.startswith('$'):
            t=addr2rec.get((caller['bank'],int(arg[1:],16)))
            if t is None: raise SystemExit('%s: CALL target %s unknown'%(caller['id'],arg))
            return t
        return byid[arg]
    def text_of(x):
        if x['id'] in tr: return tr[x['id']]
        if not a.placeholder: errs.append('%s: no translation'%x['id']);
        toks=re.findall(r'<(?:FACE|CALL)[^>]*>|<(?:WAIT|CLR|SCROLL|PAUSE|END|NICK2?|ITEM2?|NAMEC8D3|PASSWORD)>',x['jp'])
        # keep structure; one placeholder phrase per box
        s='';said=False
        for t in toks:
            if t in ('<WAIT>','<END>') and not said: s+='[%s]'%x['id']; said=True
            if t=='<CLR>': said=False
            s+=t
        return s
    report=[];info_cache={}
    def callee_info(arg,caller=None):
        return None
    items={}
    order=[]
    # layout callees first (records that are CALL targets)
    def layout_rec(x,stack=()):
        if x['id'] in items: return
        text=text_of(x)
        L=Layout(enc,lambda arg: cinfo(arg,x,stack+(x['id'],)),x['id'])
        try:
            it,rep=layout_string(x['id'],text,L,report)
        except ValueError as ex:
            errs.append(str(ex)); it,rep=[0xEF],dict(pages=[[]])
        items[x['id']]=[('CALL',resolve(v[1],x)['id']) if isinstance(v,tuple) else v for v in it]
        last=rep['pages'][-1] if rep['pages'] else []
        info_cache[x['id']]=dict(first_w=(last[0]['w'] if last else 0),rows=len(last),rows_text=[r['text'] for r in last],end_pen=last[-1]['w'] if last else 0,
                                 ends_nl=bool(last) and len(last)>1 and last[-1]['text']=='' ,clr=len(rep['pages'])>1)
    def cinfo(arg,caller,stack):
        t=resolve(arg,caller)
        if t['id'] in stack: return None
        layout_rec(t,stack)
        return info_cache[t['id']]
    for x in dlg:
        if x['block']=='orphan' and x['id'] not in tr: continue
        layout_rec(x)
    # ---- placement in banks 10h+
    def calls_of(i): return [v[1] for v in items[i] if isinstance(v,tuple)]
    callers={}
    for i in items:
        for c in calls_of(i): callers.setdefault(c,set()).add(i)
    groups=[];seen=set()
    for x in dlg:
        if x['id'] not in items or x['id'] in seen: continue
        g=[];st=[x['id']]
        while st:
            y=st.pop()
            if y in seen: continue
            seen.add(y); g.append(y); st+=calls_of(y); st+=sorted(callers.get(y,()))
        groups.append(g)
    size=lambda i: sum(3 if isinstance(v,tuple) else 1 for v in items[i])
    place={};cb=DLG_BANK0;cur=BT+MASTER_N
    for g in groups:
        need=sum(size(i) for i in g)
        if cur+need>0x8000: cb+=1; cur=0x4000
        if cb>DLG_BANK_LAST: raise SystemExit('dialogue does not fit in banks %02X-%02X'%(DLG_BANK0,DLG_BANK_LAST))
        for i in g: place[i]=(cb,cur); cur+=size(i)
    used_banks=(cb,cur)
    for x in dlg:   # wipe old spans
        for i in range(x['off'],x['off']+x['max_bytes']): rom[i]=0xEF
    for i,lst in items.items():
        b,ad=place[i]; buf=[]
        for v in lst:
            if isinstance(v,tuple):
                tb,ta=place[v[1]]
                if tb!=b: raise SystemExit('%s: CALL target %s in bank %02X, caller in %02X'%(i,v[1],tb,b))
                buf+=[0xFB,ta&0xFF,ta>>8]
            else: buf.append(v)
        o=off(b,ad); rom[o:o+len(buf)]=bytes(buf)
    for n in range(MASTER_N):
        x=byid['dlg_%03X'%n]; b,ad=place[x['id']]
        o=off(DLG_BANK0,PT+2*n); rom[o]=ad&0xFF; rom[o+1]=ad>>8; rom[off(DLG_BANK0,BT+n)]=b
    rom[0x3D6E]=DLG_BANK0       # B-replay: push the table bank before $3C4B
    # ---- VWF engine
    img,sym=asm.build()
    vb,vend=asm.patch(rom,img,sym,None); assert vb==VWF_BANK
    # ---- name tables in bank 17h
    cur=(vend+0xF)&~0xF
    tbl_spec=[('nick',0x4AB2,72,[0x3DD2,0x3DE8]),('item',0x4BD1,64,[0x3DF4,0x3DFC]),('name',0x4C51,54,[0x3E04])]
    # map original table slots -> string ids
    slot={}
    for x in S:
        for pl in x['ptr_locs']: slot[pl]=x['id']
    newaddr={}
    def put(data):
        nonlocal cur
        o=off(VWF_BANK,cur); rom[o:o+len(data)]=bytes(data); ad=cur; cur+=len(data)
        assert cur<0x5F23
        return ad
    tbl_addr={}
    for blk,base,n,refs in tbl_spec:
        tbl_addr[blk]=put([0]*(2*n))
    for sid,it in tables.items():
        newaddr[sid]=put(it+[0xEF])
    for blk,base,n,refs in tbl_spec:
        ta=tbl_addr[blk]
        for k in range(n):
            sid=slot.get(off(0x0E,base+2*k))
            if sid is None: raise SystemExit('table %s slot %d has no string'%(blk,k))
            ad=newaddr[sid]; o=off(VWF_BANK,ta+2*k); rom[o]=ad&0xFF; rom[o+1]=ad>>8
        for r in refs: rom[r]=ta&0xFF; rom[r+1]=ta>>8
    rom[0x3E0A]=VWF_BANK
    # battle hand slots ($00:1434-$14E6, incl. the $1496/$14A1 item-name reader) belong to the UI layer
    # (ui/tools/build_ui.py renders them from bank 19h tiles): no short-name table here.
    # ---- fixed UI / cmd / quest in place
    for x in S:
        if x['block'] not in ('fixed','cmd','quest'): continue
        if x['id'] not in tr: errs.append('%s: no translation'%x['id']); continue
        e=enc_fixed(tr[x['id']],fx,x['id'],warns)
        if len(e)>x['max_bytes']: errs.append('%s: %d bytes > %d'%(x['id'],len(e),x['max_bytes'])); e=e[:x['max_bytes']]
        if x['block']!='quest': e+= [0xFF]*(x['max_bytes']-len(e))
        rom[x['off']:x['off']+len(e)]=bytes(e)
    # ---- font block
    font=open(os.path.join(E,'font','font9000.bin'),'rb').read()
    lzd=compress(font); assert decompress(lzd,0,0x800)[0]==font
    FA=0x6000; o=off(VWF_BANK,FA); rom[o:o+len(lzd)]=lzd
    rom[0x2D6E]=VWF_BANK; rom[0x2D7A]=FA&0xFF; rom[0x2D7B]=FA>>8
    m0=off(3,0x5F23); m1=off(VWF_BANK,0x5F23); rom[m1:m1+0xC4]=orig[m0:m0+0xC4]
    # ---- checksums
    c=0
    for i in range(0x134,0x14D): c=(c-rom[i]-1)&0xFF
    rom[0x14D]=c; g=(sum(rom)-rom[0x14E]-rom[0x14F])&0xFFFF; rom[0x14E]=g>>8; rom[0x14F]=g&0xFF
    os.makedirs(os.path.dirname(os.path.abspath(a.out)),exist_ok=True); os.makedirs(os.path.dirname(os.path.abspath(a.layout)),exist_ok=True)
    open(a.out,'wb').write(rom)
    json.dump(dict(varw=varw,report=report),open(a.layout,'w'),indent=0)
    # ---- summary
    nsplit=sum(len(r['splits']) for r in report); nh=sum(r['hyph'] for r in report)
    # two-box ending scenes (dual mode): each box owns 44 canvas cells, so every page (and every 4 visible rows of a
    # scrolling page) of an ending message must fit in 44 cells (ceil(width/8) per row)
    import math
    for lo,hi in ((0x198,0x1CA),(0x1E2,0x1EB)):
        for i in range(lo,hi+1):
            r=next((q for q in report if q['id']==byid['dlg_%03X'%i]['id']),None)
            if r is None: continue
            for pi,pg in enumerate(r['pages']):
                c=[math.ceil(l['w']/8) for l in pg]
                worst=max((sum(c[k:k+4]) for k in range(max(1,len(c)-3))),default=0)
                if worst>44 and i==0x1E2:
                    warns.append('%s p%d: %d cells (> 44, ok: printed before the first window box)'%(r['id'],pi+1,worst))
                elif worst>44: errs.append('%s p%d: %d canvas cells > 44 (two-box ending box)'%(r['id'],pi+1,worst))
    nover=[r['id'] for r in report if r['overflow']]
    for r in report:
        for o in r['overflow']: errs.append('%s: overflow: %s'%(r['id'],o))
    print('wrote %s md5 %s'%(a.out,hashlib.md5(rom).hexdigest()))
    print('dialogue: %d strings, banks %02X-%02X (last bank used to $%04X), name tables 17:$%04X-$%04X'%(len(items),DLG_BANK0,used_banks[0],used_banks[1],vend,cur))
    print('name slot widths (px):',varw)
    print('auto splits: %d, hyphens: %d, overflow strings: %d %s'%(nsplit,nh,len(nover),nover[:10]))
    for r in report:
        for s in r['splits']: print('  split %s (%s): ...%s'%(r['id'],s['kind'],s['at']))
    for w in warns[:40]: print('warn:',w)
    if len(warns)>40: print('warn: ... %d more'%(len(warns)-40))
    for e in errs[:60]: print('ERROR:',e)
    if len(errs)>60: print('ERROR: ... %d more'%(len(errs)-60))
    sys.exit(1 if errs else 0)
main()
