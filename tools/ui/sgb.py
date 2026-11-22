"""SGB border edit helpers (bank 0D: CHR $4000-$5FFF = 256 4bpp tiles, map $6000 32x28 words, palettes $6800 (3x16 BGR555))."""
from PIL import Image
from collections import Counter
O=0xD*0x4000-0x4000
class Border:
    def __init__(s,rom):
        s.rom=rom
        s.chr=bytearray(rom[O+0x4000:O+0x6000]); s.map=bytearray(rom[O+0x6000:O+0x6800])
        pl=rom[O+0x6800:O+0x6860]
        s.pal=[[((c&31)*8,((c>>5)&31)*8,((c>>10)&31)*8) for c in (pl[(p*16+i)*2]|pl[(p*16+i)*2+1]<<8 for i in range(16))] for p in range(3)]
        s.cnt=Counter(s.entry(x,y)[0] for y in range(28) for x in range(32))
    def entry(s,x,y):
        e=s.map[(y*32+x)*2]|s.map[(y*32+x)*2+1]<<8
        return e&0x3FF,((e>>10)&7)-4,bool(e&0x4000),bool(e&0x8000)
    def set_entry(s,x,y,t,p=None,hf=None,vf=None):
        t0,p0,h0,v0=s.entry(x,y)
        p=p0 if p is None else p; hf=h0 if hf is None else hf; vf=v0 if vf is None else vf
        e=(t&0x3FF)|((p+4)<<10)|(0x4000 if hf else 0)|(0x8000 if vf else 0)
        s.map[(y*32+x)*2]=e&0xFF; s.map[(y*32+x)*2+1]=e>>8
    def tile(s,t):
        d=s.chr[t*32:t*32+32]; px=[[0]*8 for _ in range(8)]
        for y in range(8):
            for x in range(8):
                b=7-x
                px[y][x]=((d[y*2]>>b)&1)|(((d[y*2+1]>>b)&1)<<1)|(((d[16+y*2]>>b)&1)<<2)|(((d[16+y*2+1]>>b)&1)<<3)
        return px
    def put_tile(s,t,px):
        d=bytearray(32)
        for y in range(8):
            for x in range(8):
                c=px[y][x]; b=7-x
                d[y*2]|=(c&1)<<b; d[y*2+1]|=((c>>1)&1)<<b; d[16+y*2]|=((c>>2)&1)<<b; d[16+y*2+1]|=((c>>3)&1)<<b
        s.chr[t*32:t*32+32]=d
    def cell(s,x,y):
        t,p,hf,vf=s.entry(x,y); px=s.tile(t)
        if hf: px=[r[::-1] for r in px]
        if vf: px=px[::-1]
        return px
    def set_cell(s,x,y,px,allow_shared=False):
        t,p,hf,vf=s.entry(x,y)
        if s.cnt[t]>1 and not allow_shared: raise ValueError('tile %02X at (%d,%d) is shared (%d uses)'%(t,x,y,s.cnt[t]))
        if vf: px=px[::-1]
        if hf: px=[r[::-1] for r in px]
        s.put_tile(t,px)
    def region(s,x0,y0,x1,y1):
        """index image (list of rows) of cells x0..x1-1, y0..y1-1"""
        H=(y1-y0)*8; W=(x1-x0)*8; out=[[0]*W for _ in range(H)]
        for cy in range(y0,y1):
            for cx in range(x0,x1):
                px=s.cell(cx,cy)
                for y in range(8):
                    for x in range(8): out[(cy-y0)*8+y][(cx-x0)*8+x]=px[y][x]
        return out
    def set_region(s,x0,y0,img,skip_shared=True):
        for cy in range(len(img)//8):
            for cx in range(len(img[0])//8):
                px=[r[cx*8:cx*8+8] for r in img[cy*8:cy*8+8]]
                t=s.entry(x0+cx,y0+cy)[0]
                if s.cnt[t]>1:
                    if px!=s.cell(x0+cx,y0+cy) and not skip_shared: raise ValueError('shared cell changed (%d,%d)'%(x0+cx,y0+cy))
                    continue
                s.set_cell(x0+cx,y0+cy,px)
    def write(s,rom):
        rom[O+0x4000:O+0x6000]=s.chr; rom[O+0x6000:O+0x6800]=s.map
    def render(s,path,scale=2):
        im=Image.new('RGB',(256,224))
        for ty in range(28):
            for tx in range(32):
                t,p,hf,vf=s.entry(tx,ty); px=s.cell(tx,ty); pp=s.pal[p] if 0<=p<3 else s.pal[0]
                for y in range(8):
                    for x in range(8):
                        c=px[y][x]; im.putpixel((tx*8+x,ty*8+y),pp[c] if c else pp[0])
        im.resize((256*scale,224*scale),Image.NEAREST).save(path)
