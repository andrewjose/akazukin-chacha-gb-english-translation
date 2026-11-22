"""English results stamps (32x32, 4x4 tiles raw 2bpp at 02:7A6A pass / 02:7B6A fail): keep the original ring,
clear the inside, draw two lines of text (engine VWF font, regular weight)."""
import ptext
TEXT={'pass':('Well','done!'),'fail':('Try','again')}
R_CLEAR=12.6
def decode(data):
    px=[[0]*32 for _ in range(32)]
    for t in range(16):
        tx,ty=t%4,t//4
        for y in range(8):
            lo,hi=data[t*16+2*y],data[t*16+2*y+1]
            for x in range(8):
                px[ty*8+y][tx*8+x]=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
    return px
def encode(px):
    out=bytearray()
    for t in range(16):
        tx,ty=t%4,t//4
        for y in range(8):
            lo=hi=0
            for x in range(8):
                c=px[ty*8+y][tx*8+x]; lo|=(c&1)<<(7-x); hi|=((c>>1)&1)<<(7-x)
            out+=bytes([lo,hi])
    return bytes(out)
def make(kind,orig):
    px=decode(orig)
    for y in range(32):
        for x in range(32):
            if (x-15.5)**2+(y-15.5)**2<R_CLEAR**2: px[y][x]=0
    l1,l2=TEXT[kind]
    for line,y0 in ((l1,7),(l2,15)):
        g,W=ptext.render(line,bold=False)
        x0=(32-W)//2
        for y in range(8):
            for x in range(W):
                if g[y][x]: px[y0+y][x0+x]=3
    return encode(px)
if __name__=='__main__':
    import sys
    r=open(sys.argv[1],'rb').read(); o=2*0x4000-0x4000
    for a,k in ((0x7A6A,'pass'),(0x7B6A,'fail')):
        ptext.preview(make(k,r[o+a:o+a+256]),4,4,sys.argv[2]+'_%s.png'%k,8)
