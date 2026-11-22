"""LZ decoder matching $00:2AD5 exactly (engine/tools/lz.py treats A0-BF as a zero fill; the game writes
n PAIRS of (00, literal byte) for A0-BF: $2B99-$2BDC). Compressor: engine lz.compress (never emits A0-BF)."""
import sys,os; sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','engine'))
from lz import compress
def decompress(r,o,n,prefix=b''):
    out=bytearray(prefix); s=o; n+=len(prefix); P=len(prefix)
    while len(out)<n:
        c=r[o]
        if c<0x80:
            if c==0x7F and r[o+1]==0xFF: break
            L=(c>>2)+2; d=(((c&3)-4)<<8)|r[o+1]; o+=2
            for _ in range(L):
                if len(out)>=n: break
                out.append(out[len(out)+d])
        elif c<0xA0:
            L=(c&0x1F)+1; o+=1
            for _ in range(L):
                if len(out)>=n: break
                out.append(r[o]); o+=1
        elif c<0xC0:
            L=(c&0x1F)+1; o+=1
            for _ in range(L):
                if len(out)>=n: break
                out.append(0)
                if len(out)>=n: break
                out.append(r[o]); o+=1
        elif c<0xE0:
            L=(c&0x1F)+2; out+=bytes([r[o+1]])*min(L,n-len(out)); o+=2
        else:
            L=c&0x1F
            if L==0x1F: L=(r[o+1]+0x1F)&0xFF; o+=1
            L=(L+1)&0xFF; o+=1; out+=bytes(min(L,n-len(out)))
    return bytes(out[P:]),o-s
