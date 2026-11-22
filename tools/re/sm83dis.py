"""Minimal SM83 (Game Boy CPU) disassembler.
python3 -I sm83dis.py ROM bank addr_hex count   (bank used for $4000-$7FFF)"""
import sys
R=['b','c','d','e','h','l','[hl]','a']
RP=['bc','de','hl','sp']; RP2=['bc','de','hl','af']
CC=['nz','z','nc','c']
ALU=['add a,','adc a,','sub ','sbc a,','and ','xor ','or ','cp ']
def dis1(mem,pc):
    """mem(addr)->byte. returns (text,length,target or None)"""
    op=mem(pc); b1=lambda: mem(pc+1); w=lambda: mem(pc+1)|mem(pc+2)<<8
    x,y,z=op>>6,(op>>3)&7,op&7; p,q=y>>1,y&1
    def rel(): d=b1(); d=d-256 if d>127 else d; return pc+2+d
    if op==0xCB:
        o=b1(); x2,y2,z2=o>>6,(o>>3)&7,o&7
        nm=['rlc','rrc','rl','rr','sla','sra','swap','srl'][y2] if x2==0 else ['bit','res','set'][x2-1]+' %d,'%y2
        return (nm+(' ' if x2==0 else '')+R[z2],2,None)
    if x==0:
        if z==0:
            if y==0: return('nop',1,None)
            if y==1: return('ld [$%04X],sp'%w(),3,None)
            if y==2: return('stop',2,None)
            if y==3: t=rel(); return('jr $%04X'%t,2,t)
            t=rel(); return('jr %s,$%04X'%(CC[y-4],t),2,t)
        if z==1:
            return(('ld %s,$%04X'%(RP[p],w()),3,None) if q==0 else ('add hl,%s'%RP[p],1,None))
        if z==2:
            m=['[bc]','[de]','[hl+]','[hl-]'][p]
            return(('ld %s,a'%m if q==0 else 'ld a,%s'%m),1,None)
        if z==3: return(('inc ' if q==0 else 'dec ')+RP[p],1,None)
        if z==4: return('inc '+R[y],1,None)
        if z==5: return('dec '+R[y],1,None)
        if z==6: return('ld %s,$%02X'%(R[y],b1()),2,None)
        return(['rlca','rrca','rla','rra','daa','cpl','scf','ccf'][y],1,None)
    if x==1:
        if op==0x76: return('halt',1,None)
        return('ld %s,%s'%(R[y],R[z]),1,None)
    if x==2: return(ALU[y]+R[z],1,None)
    if z==0:
        if y<4: return('ret '+CC[y],1,None)
        if y==4: return('ldh [$FF%02X],a'%b1(),2,None)
        if y==5: d=b1(); d=d-256 if d>127 else d; return('add sp,%d'%d,2,None)
        if y==6: return('ldh a,[$FF%02X]'%b1(),2,None)
        d=b1(); d=d-256 if d>127 else d; return('ld hl,sp%+d'%d,2,None)
    if z==1:
        if q==0: return('pop '+RP2[p],1,None)
        return(['ret','reti','jp hl','ld sp,hl'][p],1,None)
    if z==2:
        if y<4: t=w(); return('jp %s,$%04X'%(CC[y],t),3,t)
        return(['ld [$FF00+c],a','ld [$%04X],a'%w(),'ld a,[$FF00+c]','ld a,[$%04X]'%w()][y-4],1 if y in(4,6) else 3,None)
    if z==3:
        if y==0: t=w(); return('jp $%04X'%t,3,t)
        if y==6: return('di',1,None)
        if y==7: return('ei',1,None)
        return('db $%02X'%op,1,None)
    if z==4:
        if y<4: t=w(); return('call %s,$%04X'%(CC[y],t),3,t)
        return('db $%02X'%op,1,None)
    if z==5:
        if q==0: return('push '+RP2[p],1,None)
        if p==0: t=w(); return('call $%04X'%t,3,t)
        return('db $%02X'%op,1,None)
    if z==6: return(ALU[y]+'$%02X'%b1(),2,None)
    return('rst $%02X'%(y*8),1,y*8)
def make_mem(rom,bank):
    def m(a):
        if a<0x4000: return rom[a]
        if a<0x8000: return rom[bank*0x4000+a-0x4000]
        return 0
    return m
def dis(rom,bank,addr,count):
    m=make_mem(rom,bank); out=[]; pc=addr
    for _ in range(count):
        t,l,_=dis1(m,pc)
        raw=' '.join('%02X'%m(pc+i) for i in range(l))
        out.append('%02X:%04X  %-9s %s'%(bank if pc>=0x4000 else 0,pc,raw,t)); pc+=l
    return out
if __name__=='__main__':
    rom=open(sys.argv[1],'rb').read()
    print('\n'.join(dis(rom,int(sys.argv[2],16),int(sys.argv[3],16),int(sys.argv[4]))))
