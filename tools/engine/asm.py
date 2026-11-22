"""Assemble src/vwf.asm -> $CHACHA_WORK/engine/tmp/vwf.gb + vwf.sym. patch(rom) copies the bank-0 sections and the VWF bank.
Assembled with the work dir as cwd (font/*.bin generated there) and this directory on the include path (src/defs.inc)."""
import os,sys,subprocess,re
SRC=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(SRC,'..','common')); import paths
E=paths.ENGINE_WORK
BANK0_PATCHES=[(0x1ED0,0x1ED3),(0x3C46,0x3C7E),(0x3C26,0x3C28),(0x3D99,0x3D9D),(0x3FD2,0x3FEB)]
def build():
    t=os.path.join(E,'tmp'); os.makedirs(t,exist_ok=True)
    subprocess.run([paths.tool('rgbasm'),'-I',SRC+os.sep,'-o',t+'/vwf.o',os.path.join(SRC,'src','vwf.asm')],cwd=E,check=True)
    subprocess.run([paths.tool('rgblink'),'-o',t+'/vwf.gb','-n',t+'/vwf.sym','-m',t+'/vwf.map',t+'/vwf.o'],cwd=E,check=True)
    img=open(t+'/vwf.gb','rb').read(); sym={}
    for ln in open(t+'/vwf.sym'):
        m=re.match(r'([0-9A-Fa-f]+):([0-9A-Fa-f]+) (\S+)',ln)
        if m: sym[m.group(3)]=(int(m.group(1),16),int(m.group(2),16))
    return img,sym
def patch(rom,img,sym,used):
    """used(start,end) marks bank-0 changes; returns end address of the VWF code in its bank."""
    for a,b in BANK0_PATCHES:
        rom[a:b]=img[a:b]
    vb,va=sym['VwfPutChar']; end=sym['VwfEnd'][1]
    o=vb*0x4000; rom[o:o+end-0x4000]=img[o:o+end-0x4000]
    return vb,end
if __name__=='__main__':
    img,sym=build(); print({k:'%02X:%04X'%v for k,v in sym.items() if not '.' in k})
