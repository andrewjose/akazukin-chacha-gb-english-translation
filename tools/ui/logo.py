"""English title logo 'Akazukin ChaCha' (128x24 px = tiles 50-7F, rows of 16) drawn from a TTF:
1-bit text, fill colour 1, 1 px outline colour 3, 1 px drop shadow colour 3."""
from PIL import Image,ImageDraw,ImageFont
def render(text='Akazukin ChaCha',font=None,size=17,W=128,H=24,y=None,fill=1,spacing=0):
    import ptext; F=ImageFont.truetype(font or ptext.BIGFONT,size)
    # measure with optional letter spacing
    ws=[F.getbbox(ch)[2] if ch!=' ' else F.getlength(' ') for ch in text]
    total=sum(F.getlength(ch) for ch in text)+spacing*(len(text)-1)
    m=Image.new('1',(W,H),0); d=ImageDraw.Draw(m); d.fontmode='1'
    x=(W-total)/2
    bb=F.getbbox(text); th=bb[3]-bb[1]
    yy=(H-2-th)//2-bb[1] if y is None else y
    for ch in text:
        d.text((x,yy),ch,font=F,fill=1); x+=F.getlength(ch)+spacing
    px=[[m.getpixel((i,j)) for i in range(W)] for j in range(H)]
    out=[[0]*W for _ in range(H)]
    for j in range(H):
        for i in range(W):
            if px[j][i]: out[j][i]=fill
            else:
                nb=any(0<=j+dj<H and 0<=i+di<W and px[j+dj][i+di] for dj in (-1,0,1) for di in (-1,0,1))
                sh=(j>0 and i>0 and px[j-1][i-1]) or (j>1 and i>1 and px[j-2][i-1])
                if nb or sh: out[j][i]=3
    return out,total
def to_tiles(out):
    H=len(out); W=len(out[0]); b=bytearray()
    for ty in range(H//8):
        for tx in range(W//8):
            for y in range(8):
                lo=hi=0
                for x in range(8):
                    c=out[ty*8+y][tx*8+x]; lo|=(c&1)<<(7-x); hi|=((c>>1)&1)<<(7-x)
                b+=bytes([lo,hi])
    return bytes(b)
def preview(out,path,scale=4):
    pal=(255,170,85,0); H=len(out); W=len(out[0])
    im=Image.new('L',(W,H))
    for j in range(H):
        for i in range(W): im.putpixel((i,j),pal[out[j][i]])
    im.resize((W*scale,H*scale),Image.NEAREST).save(path)
if __name__=='__main__':
    import sys
    import ptext; fonts=[ptext.BIGFONT]
    ims=[]
    for f in fonts:
        for sz in (15,16,17):
            out,t=render(font=f,size=sz,spacing=-0.5)
            print(f.split('/')[-1],sz,t)
            preview(out,'/tmp/l.png'); ims.append(Image.open('/tmp/l.png').copy())
    o=Image.new('L',(ims[0].width,(ims[0].height+8)*len(ims)),128)
    for i,im in enumerate(ims): o.paste(im,(0,i*(im.height+8)))
    o.save(sys.argv[1])

def render2(words=(('Akazukin',2),('ChaCha',1)),font=None,
            W=128,H=24,tw=124,th=19,gap=0.35,thr=110):
    """render big, downsample to tw x th (non-uniform), threshold; per-word fill colours; outline + shadow."""
    import ptext; S=8; F=ImageFont.truetype(font or ptext.BIGFONT,22*S)
    full=' '.join(w for w,_ in words)
    bb=F.getbbox(full)
    big=Image.new('L',(bb[2]-bb[0]+4*S,bb[3]-bb[1]+4*S),0); d=ImageDraw.Draw(big)
    x=2*S-bb[0]; spans=[]
    for i,(w,c) in enumerate(words):
        x0=x; d.text((x,2*S-bb[1]),w,font=F,fill=255); x+=F.getlength(w)
        spans.append((x0,x,c))
        if i<len(words)-1: x+=F.getlength(' ')*gap*2
    # crop to ink
    box=big.getbbox(); big=big.crop(box); 
    sm=big.resize((tw,th),Image.LANCZOS)
    scale=tw/big.width
    px=[[1 if sm.getpixel((i,j))>thr else 0 for i in range(tw)] for j in range(th)]
    colour_at=lambda i: next((c for a,b,c in spans if (a-box[0])*scale-1<=i<=(b-box[0])*scale+1),1)
    out=[[0]*W for _ in range(H)]
    ox=(W-tw)//2; oy=(H-th)//2-1
    P=lambda j,i: 0<=j<th and 0<=i<tw and px[j][i]
    for j in range(H):
        for i in range(W):
            jj,ii=j-oy,i-ox
            if P(jj,ii): out[j][i]=colour_at(ii)
            else:
                nb=any(P(jj+dj,ii+di) for dj in (-1,0,1) for di in (-1,0,1))
                sh=P(jj-1,ii-1) or P(jj-2,ii-1) or P(jj-2,ii-2)
                if nb or sh: out[j][i]=3
    return out
