"""Free-space map: runs of 0xFF or 0x00 >= MIN bytes per 16 KB bank.
usage: python3 tools/re/freespace.py ROM"""
import sys
if len(sys.argv)<2: sys.exit(__doc__)
r=open(sys.argv[1],'rb').read()
MIN=64
for b in range(len(r)//0x4000):
    base=b*0x4000; runs=[]; o=0
    while o<0x4000:
        v=r[base+o]
        if v in (0,0xFF):
            e=o
            while e<0x4000 and r[base+e]==v: e+=1
            if e-o>=MIN: runs.append((o,e-o,v))
            o=e
        else: o+=1
    tot=sum(n for _,n,_ in runs)
    cpu=lambda o:(o if b==0 else 0x4000+o)
    print('bank %02X  free %5d  '%(b,tot)+', '.join('$%04X+%d(%02X)'%(cpu(o),n,v) for o,n,v in runs))
