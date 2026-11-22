"""Typesetting report + contact sheets for every laid-out dialogue page.
python3 -I tools/engine/typeset_check.py [$CHACHA_WORK/engine/layout.json] [--sheets DIR] [--per 160]
Reads the layout written by build.py. Checks: line overflow (> box width), page overflow (> box rows, non-scroll pages),
stranded single words on the last line of a paragraph, hyphenations, auto page splits, slack statistics.
Contact sheets: each page drawn with the real VWF glyphs/widths in its box (default 120x32 px);
name/item slots are drawn as a grey bar of the widest value; red = past the box edge. Exit 1 on overflow."""
import sys,os,json,re,math
T=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','common')); import paths
E=paths.ENGINE_WORK
from PIL import Image,ImageDraw
args=[a for a in sys.argv[1:] if not a.startswith('--')]
lay=args[0] if args else os.path.join(E,'layout.json')
def opt(k,d):
    return sys.argv[sys.argv.index(k)+1] if k in sys.argv else d
SD=opt('--sheets',os.path.join(E,'shots','typeset')); PER=int(opt('--per','160'))
D=json.load(open(lay)); varw=D['varw']; R=D['report']
G=open(os.path.join(E,'font','vwf_glyphs.bin'),'rb').read(); W=open(os.path.join(E,'font','vwf_widths.bin'),'rb').read()
SPEC={'♥':0x80,'♪':0x81,'💧':0x82}
VW={'NICK':varw['nick'],'NICK2':varw['nick'],'ITEM':varw['item'],'ITEM2':varw['item'],'NAME':varw['name']}
def tokens(t):
    i=0
    while i<len(t):
        m=re.match(r'\{(NICK2?|ITEM2?|NAME)\}',t[i:])
        if m: yield ('var',m.group(1)); i+=m.end(); continue
        yield ('ch',SPEC.get(t[i],ord(t[i]))); i+=1
def draw_line(px,x0,y0,t,bw):
    x=x0
    for k,v in tokens(t):
        if k=='var':
            for xx in range(VW[v]):
                for yy in range(1,6): px((x+xx,y0+yy),(190,190,190) if x+xx-x0<bw else (255,120,120))
            x+=VW[v]; continue
        c=v-0x20
        if not 0<=c<len(W): continue
        for yy in range(8):
            b=G[c*8+yy]
            for xx in range(8):
                if b>>(7-xx)&1: px((x+xx,y0+yy),(0,0,0) if x+xx-x0<bw else (220,0,0))
        x+=W[c]
    return x-x0
# ---- checks
issues=dict(line_over=[],page_over=[],stranded=[],hyph=[],split=[])
slacks=[];pages=[]
for r in R:
    bw,rows=r.get('box',[120,4])
    for pi,pg in enumerate(r['pages']):
        vis=[x for x in pg]
        while len(vis)>1 and not vis[-1]['text'].strip(): vis.pop()
        pages.append((r['id'],pi,pg,bw,rows,r.get('scroll',False)))
        for k,ln in enumerate(vis):
            if ln['w']>bw: issues['line_over'].append('%s p%d: %r (%d px)'%(r['id'],pi+1,ln['text'],ln['w']))
            if k+1<len(vis) and vis[k+1]['brk']=='soft': slacks.append(bw-ln['w'])
        if len(vis)>rows and not r.get('scroll'): issues['page_over'].append('%s p%d: %d rows (max %d)'%(r['id'],pi+1,len(vis),rows))
    for s in r['stranded']: issues['stranded'].append('%s: %r'%(r['id'],s))
    if r['hyph']: issues['hyph'].append('%s: %d'%(r['id'],r['hyph']))
    for s in r['splits']: issues['split'].append('%s (%s): ...%s'%(r['id'],s['kind'],s['at']))
for o in r.get('overflow',[]) if False else []: pass
print('strings %d, pages %d'%(len(R),len(pages)))
if slacks:
    s=sorted(slacks); print('slack on wrapped lines: mean %.1f px, median %d, max %d'%(sum(s)/len(s),s[len(s)//2],s[-1]))
for k,v in issues.items():
    print('%-10s %d'%(k,len(v)))
    for x in v[:40]: print('   ',x)
    if len(v)>40: print('    ... %d more'%(len(v)-40))
# ---- contact sheets
os.makedirs(SD,exist_ok=True)
for f in os.listdir(SD):
    if f.startswith('typeset_'): os.remove(os.path.join(SD,f))
BW,BH=160,48; COLS=8
for si in range(0,len(pages),PER):
    chunk=pages[si:si+PER]; nrow=math.ceil(len(chunk)/COLS)
    im=Image.new('RGB',(COLS*BW,nrow*BH),(255,255,255)); dr=ImageDraw.Draw(im); px=im.putpixel
    for i,(sid,pi,pg,bw,rows,scr) in enumerate(chunk):
        X=(i%COLS)*BW; Y=(i//COLS)*BH
        dr.rectangle([X+2,Y+9,X+5+bw,Y+10+8*rows],outline=(150,150,220))
        dr.text((X+3,Y-1),'%s p%d%s'%(sid,pi+1,' S' if scr else ''),fill=(0,0,160))
        vis=pg[-rows:] if scr else pg
        for k,ln in enumerate(vis[:rows+2]):
            def P(p,c,X=X,Y=Y):
                if 0<=p[0]-X<BW and 0<=p[1]-Y<BH: px(p,c)
            draw_line(P,X+4,Y+10+8*k,ln['text'],bw)
    im=im.resize((im.width*2,im.height*2),Image.NEAREST)
    im.save(os.path.join(SD,'typeset_%03d.png'%(si//PER)))
print('contact sheets ->',SD)
sys.exit(1 if issues['line_over'] or issues['page_over'] else 0)
