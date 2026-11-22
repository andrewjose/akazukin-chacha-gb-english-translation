"""Proportional label renderer for the UI (build time).
Uses the engine's hand-drawn VWF font (engine/tools/fontdef.py). Labels are precomposed into 8x8 tiles here and
only copied to VRAM at runtime.

render(text, bold=True) -> (cols: list of 8-row column bitmaps as ints per row, width)
tiles(text, cells, align='c', bold=True, rows=1, tall=False, color=3, xoff=0) -> bytes (2bpp, cells*rows tiles, row-major)
"""
import sys,os
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','engine'))
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','common')); import paths
import fontdef
from PIL import Image
TOK={'♡':'<HEART>','♪':'<NOTE>','💧':'{drop}'}

def glyph(ch,bold):
    rows,adv=fontdef.G[TOK.get(ch,ch)]
    w=len(rows[0])
    px=[[1 if c=='#' else 0 for c in r] for r in rows]
    if bold and ch!=' ':
        px=[[1 if (r[x] or (x>0 and r[x-1])) else 0 for x in range(w)]+[r[w-1]] for r in px]
        w+=1; adv+=1
    return px,w,adv

def render(text,bold=True,spacing=0,space=None):
    """-> 8 rows of pixel lists, width (trailing bearing removed)"""
    out=[[] for _ in range(8)]; x=0
    chars=list(text)
    for i,ch in enumerate(chars):
        px,w,adv=glyph(ch,bold)
        if ch==' ' and space is not None: adv=space
        if i<len(chars)-1: adv+=spacing
        need=x+max(w,adv)
        for r in out: r.extend([0]*(need-len(r)))
        for y in range(8):
            for xx in range(w):
                if px[y][xx]: out[y][x+xx]=1
        x+=adv
    # trim trailing blank columns
    W=x
    while W>0 and all(out[y][W-1]==0 for y in range(8) if W-1<len(out[y])): W-=1
    return [r[:W]+[0]*max(0,W-len(r)) for r in out],W

def width(text,bold=True,spacing=0): return render(text,bold,spacing)[1]

def canvas(text,cells,align='c',bold=True,rows=1,tall=False,xoff=0,yoff=0,spacing=0):
    """pixel canvas (list of rows) cells*8 wide, rows*8 tall"""
    px,W=render(text,bold,spacing)
    CW=cells*8; H=rows*8
    if W>CW: raise ValueError('label %r: %d px > %d'%(text,W,CW))
    if align=='c': x0=(CW-W)//2
    elif align=='r': x0=CW-W
    else: x0=0
    x0+=xoff
    cv=[[0]*CW for _ in range(H)]
    src=px
    if tall: src=[r for r in px for _ in (0,1)]
    for y,r in enumerate(src):
        yy=y+yoff
        if 0<=yy<H:
            for x,v in enumerate(r):
                if v: cv[yy][x0+x]=1
    return cv,W

def to_tiles(cv,color=3,shade=None):
    """canvas (H x W, multiples of 8) -> 2bpp tiles row-major. shade: colour for a 1px drop shadow (None = none)"""
    H=len(cv); W=len(cv[0])
    col=[[color if cv[y][x] else 0 for x in range(W)] for y in range(H)]
    if shade is not None:
        for y in range(H):
            for x in range(W):
                if not cv[y][x] and ((x>0 and cv[y][x-1]) or (y>0 and cv[y-1][x])) : col[y][x]=shade
    out=bytearray()
    for ty in range(H//8):
        for tx in range(W//8):
            for y in range(8):
                lo=hi=0
                for x in range(8):
                    c=col[ty*8+y][tx*8+x]
                    lo|=(c&1)<<(7-x); hi|=((c>>1)&1)<<(7-x)
                out+=bytes([lo,hi])
    return bytes(out)

def tiles(text,cells,**kw):
    color=kw.pop('color',3); shade=kw.pop('shade',None)
    cv,W=canvas(text,cells,**kw)
    return to_tiles(cv,color,shade)

def cells_for(text,bold=True,spacing=0,pad=0):
    return (width(text,bold,spacing)+pad+7)//8

def preview(tiledata,cells,rows,path,scale=4):
    from gfx import tiles_img
    # tiles are row-major cells x rows
    n=len(tiledata)//16
    im=Image.new('L',(cells*8,rows*8),255)
    pal=(255,170,85,0)
    for t in range(n):
        tx=t%cells; ty=t//cells
        for y in range(8):
            lo,hi=tiledata[t*16+2*y],tiledata[t*16+2*y+1]
            for x in range(8):
                c=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
                im.putpixel((tx*8+x,ty*8+y),pal[c])
    im=im.resize((im.width*scale,im.height*scale),Image.NEAREST); im.save(path); return im

BIGFONT=paths.ttf()
def big_tiles(text,cells=7,rows=2,size=13,yoff=-1,align='l'):
    """16 px tall label (rank value): DejaVu Sans Condensed Bold rasterised 1-bit (no antialiasing)."""
    from PIL import ImageDraw,ImageFont
    F=ImageFont.truetype(BIGFONT,size)
    W=F.getbbox(text)[2]
    if W>cells*8: raise ValueError('big label %r %d px > %d'%(text,W,cells*8))
    x0={'l':0,'c':(cells*8-W)//2,'r':cells*8-W}[align]
    im=Image.new('1',(cells*8,rows*8),0); d=ImageDraw.Draw(im); d.fontmode='1'
    d.text((x0,yoff),text,font=F,fill=1)
    cv=[[1 if im.getpixel((x,y)) else 0 for x in range(cells*8)] for y in range(rows*8)]
    return to_tiles(cv)
