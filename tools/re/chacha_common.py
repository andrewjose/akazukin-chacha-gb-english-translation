"""Shared definitions for Akazukin Chacha (GB) text tools."""
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
from tbl import T,GLYPH_EXTRA
ORIG=os.environ.get('CHACHA_ROM','')   # original ROM (set by build.py; or pass the path on the command line)
ORIG_MD5='9a5215658c60a1802b11f728c292b536'
MASTER_BANK=0x0E; MASTER_PTR=0x4000; MASTER_N=0x559
def id_bank(i):
    # mirrors $00:3C46 (static): IDs <0xDE stay in bank 0E; >=0x319 ->8; >=0x1ED ->7; else 6
    if i<0xDE: return 0x0E
    if i>=0x319: return 0x08
    if i>=0x1ED: return 0x07
    return 0x06
def off(bank,addr): return addr if addr<0x4000 else bank*0x4000+addr-0x4000
def u16(r,o): return r[o]|r[o+1]<<8
# control codes: code -> (tag, nargs)
CTRL={0xEF:('END',0),0xF0:('SCROLL',0),0xF1:('SHAKE',0),0xF2:('CLR',0),0xF3:('WAIT',0),
      0xF4:('NICK',0),0xF5:('NICK2',0),0xF6:('ITEM',0),0xF7:('ITEM2',0),0xF8:('NAMEC8D3',0),
      0xF9:('FACE',1),0xFA:('FA',0),0xFB:('CALL',2),0xFC:('PAUSE',0),0xFD:('PASSWORD',0),
      0xFE:('NL',0)}
TAG2CODE={v[0]:k for k,v in CTRL.items()}
def decode(r,o,bank,stop_at_end=True):
    """Decode from file offset o. Returns (text, raw_bytes, calls[list of (rel_pos, target_addr)])."""
    s=[];start=o;calls=[]
    while True:
        b=r[o]
        if b in CTRL:
            tag,n=CTRL[b]
            if b==0xFB:
                a=u16(r,o+1); calls.append((o-start,a)); s.append('<CALL:$%04X>'%a)
            elif b==0xF9: s.append('<FACE:%02X>'%r[o+1])
            elif b==0xFE: s.append('<NL>\n')
            elif b==0xEF: s.append('<END>')
            else: s.append('<%s>'%tag)
            o+=1+n
            if b==0xEF and stop_at_end: break
        elif b in T: s.append(T[b]); o+=1
        elif b in GLYPH_EXTRA: s.append(GLYPH_EXTRA[b]); o+=1
        else: s.append('{%02X}'%b); o+=1
        if o-start>2000: raise ValueError('runaway at %X'%start)
    return ''.join(s), r[start:o], calls
