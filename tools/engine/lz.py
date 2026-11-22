"""Decompressor for the game's VRAM LZ format ($00:2AD5). decompress(rom, file_off, out_len) -> (bytes, compressed_len)
Commands (byte c):
  00-7F : LZ back-ref. len=(c>>2)+2, disp = (((c&3)-4)<<8)|next  (negative, relative to dest). 2 bytes.  (7F FF = end marker)
  80-9F : literal run, n=(c&1F)+1 bytes follow.
  A0-BF : zero fill n=(c&1F)+1. 1 byte.
  C0-DF : RLE n=(c&1F)+2 copies of next byte. 2 bytes.
  E0-FF : zero fill n=(c&1F)+1; if (c&1F)==1F, n=(next+0x20)&0xFF (8-bit!). 1-2 bytes.
Stops when out_len bytes are written (caller passes bc) or at 7F FF."""
def decompress(r,o,n,prefix=b''):
    """prefix = VRAM bytes preceding dest (back-refs may reach before dest)."""
    out=bytearray(prefix); s=o; n+=len(prefix); P=len(prefix)
    while len(out)<n:
        c=r[o]
        if c<0x80:
            if c==0x7F and r[o+1]==0xFF: break
            L=(c>>2)+2; d=(((c&3)-4)<<8)|r[o+1]; o+=2
            for _ in range(L):
                if len(out)>=n: break
                j=len(out)+d
                if j<0: raise IndexError('back-reference before start of prefix (need more VRAM prefix)')
                out.append(out[j])   # d negative
        elif c<0xA0:
            L=(c&0x1F)+1; o+=1
            for _ in range(L):
                if len(out)>=n: break
                out.append(r[o]); o+=1
        elif c<0xC0:
            L=(c&0x1F)+1; o+=1; out+=bytes(min(L,n-len(out)))
        elif c<0xE0:
            L=(c&0x1F)+2; out+=bytes([r[o+1]])*min(L,n-len(out)); o+=2
        else:
            L=c&0x1F
            if L==0x1F: L=(r[o+1]+0x1F)&0xFF; o+=1   # 8-bit add in $00:2C11
            L=(L+1)&0xFF; o+=1; out+=bytes(min(L,n-len(out)))
    return bytes(out[P:]),o-s

def compress(data,prefix=b''):
    """Greedy compressor for the same format (back-refs up to 1024 back, len 2..33).
    Verified by round trip through decompress(). Produces no 7F FF end marker (the loader stops on bc)."""
    buf=bytes(prefix)+bytes(data); P=len(prefix); i=P; out=bytearray(); lit=bytearray()
    def flush():
        nonlocal lit
        while lit:
            ch=lit[:32]; out.append(0x80|(len(ch)-1)); out.extend(ch); lit=lit[32:]
    while i<len(buf):
        # zero run
        z=0
        while i+z<len(buf) and buf[i+z]==0 and z<0xFF: z+=1   # 8-bit count in the SM83 loader
        # rle
        rl=1
        while i+rl<len(buf) and buf[i+rl]==buf[i] and rl<33: rl+=1
        # lz
        best=(0,0)
        for d in range(1,min(1024,i)+1):
            L=0
            while L<33 and i+L<len(buf) and buf[i+L-d]==buf[i+L]: L+=1
            if L>best[0]: best=(L,d)
            if L==33: break
        if best[0]>=2 and best[0]==33 and (best[1]-1)//256*0+1: pass
        L,d=best
        # disallow c==0x7F with low byte FF (end marker): c=0x7F means len 33, disp hi 3 -> d<=256 with lo==FF -> d==1
        if L>=2 and ((L-2)<<2|(((-d)>>8)&3))==0x7F and ((-d)&0xFF)==0xFF: L=32
        cand=[]
        if z>=2: cand.append((z/(2 if z>32 else 1),'z'))
        if rl>=3: cand.append((rl/2,'r'))
        if L>=3: cand.append((L/2,'l'))
        if not cand: lit.append(buf[i]); i+=1; continue
        k=max(cand)[1]; flush()
        if k=='z':
            if z<=31: out.append(0xE0|(z-1))          # E0|1F means 'extended'
            else: out+=bytes([0xFF,z-0x20])            # n = (next+0x20)&0xFF -> 32..255
            i+=z
        elif k=='r': out+=bytes([0xC0|(rl-2),buf[i]]); i+=rl
        else:
            dd=(-d)&0x3FF; out+=bytes([((L-2)<<2)|(dd>>8),dd&0xFF]); i+=L
    flush(); return bytes(out)
