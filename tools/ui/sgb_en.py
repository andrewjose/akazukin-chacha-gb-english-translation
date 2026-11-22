"""English SGB border (bank 0D). apply(rom) edits CHR tiles in place (only tiles used once) and 3+7 map entries.
Edits (see NOTES.md):
  logo aka zukin chacha (cols 11-25, rows 1-3, palette 1)      -> "Akazukin ChaCha" (red / green, black outline)
  ribon masukottokomikkusu (row 1 cols 0-6)                  -> removed (sky); its 7 tiles feed the 3 shared sky cells of the logo
  hatsubaichuu (RMC box, palette 0)                                -> "On sale!"
  vertical aka zukin chacha (cols 3-4 rows 6-14, palette 1)     -> rotated "Akazukin ChaCha"
  ayahana min (cols 1-2 rows 10-14, palette 1)                    -> rotated "Min" / "Ayahana"
  nedan (price box row 25, palette 0)                       -> "Price"
  hoora♪ (row 20 cols 27-31, palette 0)                     -> "Look!♪"
  bau bau (dog's bark)                                    -> 'Arf' 'arf' """
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from sgb import Border
import ptext
from PIL import Image,ImageDraw,ImageFont
E=14   # background (light blue) in palettes 0/1

def text_px(s,bold=False):
    px,W=ptext.render(s,bold=bold); return px,W

def rot_cw(px):
    """rotate a pixel matrix 90 degrees clockwise"""
    H=len(px); W=len(px[0])
    return [[px[H-1-x][y] for x in range(H)] for y in range(W)]

def blit(img,px,x0,y0,col):
    for y,r in enumerate(px):
        for x,v in enumerate(r):
            if v and 0<=y0+y<len(img) and 0<=x0+x<len(img[0]): img[y0+y][x0+x]=col

def outline(img,mask,col):
    H=len(img); W=len(img[0])
    for y in range(H):
        for x in range(W):
            if mask[y][x]: continue
            if any(0<=y+dy<H and 0<=x+dx<W and mask[y+dy][x+dx] for dy in (-1,0,1) for dx in (-1,0,1)):
                img[y][x]=col

def logo_img(W=120,H=24):
    """returns index image (palette 1): red 'Akazukin' (6 upper / 3 lower), green 'ChaCha' (c upper / a lower), outline b"""
    F=ImageFont.truetype(ptext.BIGFONT,22*8)
    words=['Akazukin','ChaCha']
    gap=F.getlength(' ')*0.7
    total=F.getlength(words[0])+gap+F.getlength(words[1])
    bb=F.getbbox('AkazukinChaCha')
    big=Image.new('L',(int(total)+40,bb[3]+40),0); d=ImageDraw.Draw(big)
    d.text((10,10),words[0],font=F,fill=255); x1=10+F.getlength(words[0])+gap
    d.text((x1,10),words[1],font=F,fill=128)
    box=big.getbbox(); big=big.crop(box)
    tw,th=W-4,H-4
    sm=big.resize((tw,th),Image.NEAREST if False else Image.BOX)
    split=(x1-box[0])*tw/big.width
    img=[[E]*W for _ in range(H)]; mask=[[0]*W for _ in range(H)]
    ox,oy=2,3
    for y in range(th):
        for x in range(tw):
            v=sm.getpixel((x,y))
            if v>60:
                mask[oy+y][ox+x]=1
                red=x<split-1
                upper=y<th*0.55
                img[oy+y][ox+x]=(6 if upper else 3) if red else (0xC if upper else 0xA)
    outline(img,mask,0xB)
    return img

def apply(rom):
    b=Border(rom)
    # ---- free the tiny ad line (row 1 cols 0-6) -> sky tile 4B
    freed=[]
    for x in range(0,7):
        t=b.entry(x,1)[0]; assert b.cnt[t]==1; freed.append(t); b.set_entry(x,1,0x4B,p=0)
    for x in range(0,7): b.cnt[freed[x]]=0
    # ---- logo: give the 3 shared sky cells inside the logo their own tiles
    for (x,y),t in zip(((18,1),(21,1),(25,1)),freed):
        b.set_entry(x,y,t,p=1); b.cnt[t]=1; b.cnt[0x4B]-=1
    for x in range(11,26):
        for y in range(1,4): assert b.entry(x,y)[1]==1 and b.cnt[b.entry(x,y)[0]]==1,(x,y)
    lg=logo_img(W=128)
    # cloud cell (26,1) (shared tile EE, palette 2): own copy + the logo's outline pixels (index B = black in palette 2 too)
    cl=b.cell(26,1); t=freed[3]; b.set_entry(26,1,t,p=2); b.cnt[t]=1; b.cnt[0xEE]-=1
    for y in range(8):
        for x in range(8):
            v=lg[y][120+x]
            if v!=E: assert v==0xB,(x,y,v); cl[y][x]=0xB
    b.set_cell(26,1,cl)
    for y in range(8):
        for x in range(120,128): lg[y][x]=E
    b.set_region(11,1,lg,skip_shared=True)
    # ---- hatsubaichuu -> On sale!  (region cols 0-5 rows 1-4; interior x 5..42, y 21..31)
    r=b.region(0,1,6,5)
    for y in range(21,32):
        for x in range(5,43):
            if r[y][x] in (0x9,0xA,0xB,0xD): r[y][x]=E
    px,W=text_px('On sale!'); blit(r,px,5+(38-W)//2,24,0xB)
    b.set_region(0,1,r)
    # ---- vertical title (cols 3-4 rows 6-14) -> rotated text
    r=b.region(3,6,5,15)
    for y in range(len(r)):
        for x in range(len(r[0])): r[y][x]=E
    px,W=text_px('Akazukin ChaCha')
    split=ptext.width('Akazukin',False)+2
    m=rot_cw(px)                       # W rows x 8 cols
    H=len(r); y0=(H-W)//2; x0=4
    mask=[[0]*16 for _ in range(H)]
    for y,row in enumerate(m):
        for x,v in enumerate(row):
            if v:
                r[y0+y][x0+x]=6 if y<split else 0xC; mask[y0+y][x0+x]=1
    outline(r,mask,0xB)
    b.set_region(3,6,r)
    # ---- author (cols 1-2 rows 10-14) -> rotated "Min" / "Ayahana"
    r=b.region(1,10,3,15)
    for y in range(len(r)):
        for x in range(len(r[0])): r[y][x]=E
    H=len(r)
    for line,xc in (('Min',8),('Ayahana',0)):
        px,W=text_px(line); m=rot_cw(px)
        y0=(H-W)//2 if line=='Ayahana' else 3
        blit(r,m,xc,y0,0x5)
    b.set_region(1,10,r)
    # ---- price: nedan -> Price (row 25 cells cols 0-5; text area x 5..31, y 9..15 of the region rows 25-26)
    r=b.region(0,25,6,27)
    for y in range(1,8):
        for x in range(5,32):
            if r[y][x]!=0xC: r[y][x]=0xC
    px,W=text_px('Price',bold=True); blit(r,px,6,1,0xF)
    b.set_region(0,25,r)
    # ---- hoora♪ -> Look!♪ (row 20 cells cols 27-31, y 0..5 of that row band; head starts at y 6)
    r=b.region(27,20,32,21)
    for y in range(0,6):
        for x in range(0,40):
            if r[y][x] in (0xB,0xC,0xD,0x9,0xA): r[y][x]=E
    for x in range(0,8):
        if r[6][x] in (0xB,0xC,0xD,0x9,0xA): r[6][x]=E
    px,W=text_px('Look! ♪'); blit(r,px,1,0,0xB)
    b.set_region(27,20,r)
    # ---- bau bau (bark) -> "Arf" "arf" (cols 12-18 rows 23-24; region origin x=96,y=184)
    r=b.region(12,23,19,25)
    for y in range(2,15):
        for x in range(8,20): r[y][x]=E if r[y][x] in (0xB,0xD,0x9) else r[y][x]
    for y in range(2,10):
        for x in range(38,48): r[y][x]=E if r[y][x] in (0xB,0xD,0x9) else r[y][x]
    for y in range(2,7):
        for x in range(36,38): r[y][x]=E if r[y][x] in (0xB,0xD,0x9) else r[y][x]
    px,W=text_px('Arf'); blit(r,px,8,4,0xB)
    px,W=text_px('arf'); assert 35+W<=48; blit(r,px,35,1,0xB)
    b.set_region(12,23,r)
    b.write(rom)
    return b

if __name__=='__main__':
    rom=bytearray(open(sys.argv[1],'rb').read()); b=apply(rom); b.render(sys.argv[2])
