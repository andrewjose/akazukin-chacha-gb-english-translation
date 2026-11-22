"""English SFX in ending illustrations (BG pictures loaded by $1E30 to $8900, records in bank 0B) and the battle
defeat burst (OBJ stream 0B:7AF0). Pictures are edited in screen space (rows 6-11 tilemap captured at runtime,
regenerated from the ROM: record_tilemaps / pictures()), written back into their tiles and recompressed in place."""
import os,sys,json
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ptext
def tidx(t): return t-0x90           # picture tiles start at $8900 = tile 90
def compose(data,tmap):
    H=len(tmap)*8; W=len(tmap[0])*8; img=[[None]*W for _ in range(H)]
    for r,row in enumerate(tmap):
        for c,t in enumerate(row):
            k=tidx(t)
            if 0<=k<len(data)//16:
                for y in range(8):
                    lo,hi=data[k*16+2*y],data[k*16+2*y+1]
                    for x in range(8): img[r*8+y][c*8+x]=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
    return img
def decompose(data,tmap,img):
    data=bytearray(data); cnt={}
    for row in tmap:
        for t in row: cnt[t]=cnt.get(t,0)+1
    for r,row in enumerate(tmap):
        for c,t in enumerate(row):
            k=tidx(t)
            if not (0<=k<len(data)//16): continue
            new=bytearray(16)
            for y in range(8):
                lo=hi=0
                for x in range(8):
                    v=img[r*8+y][c*8+x]; lo|=(v&1)<<(7-x); hi|=((v>>1)&1)<<(7-x)
                new[2*y]=lo; new[2*y+1]=hi
            if bytes(new)!=bytes(data[k*16:k*16+16]):
                assert cnt[t]==1,'shared tile %02X edited'%t
                data[k*16:k*16+16]=new
    return bytes(data)
def show(img,path,scale=4,grid=True):
    from PIL import Image
    pal={None:(255,0,255),0:(255,255,255),1:(170,170,170),2:(85,85,85),3:(0,0,0)}
    H=len(img); W=len(img[0]); im=Image.new('RGB',(W,H))
    for y in range(H):
        for x in range(W): im.putpixel((x,y),pal[img[y][x]])
    im=im.resize((W*scale,H*scale),Image.NEAREST)
    if grid:
        from PIL import ImageDraw
        d=ImageDraw.Draw(im)
        for x in range(0,W,8): d.line([(x*scale,0),(x*scale,H*scale)],fill=(255,0,0))
        for y in range(0,H,8): d.line([(0,y*scale),(W*scale,y*scale)],fill=(255,0,0))
    im.save(path)
def draw_text(img,text,x0,y0,col=3,outline=None,bold=True):
    px,W=ptext.render(text,bold=bold)
    if outline is not None:
        for y in range(8):
            for x in range(W):
                if px[y][x]:
                    for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                            yy,xx=y0+y+dy,x0+x+dx
                            if 0<=yy<len(img) and 0<=xx<len(img[0]) and img[yy][xx] is not None: img[yy][xx]=outline
    for y in range(8):
        for x in range(W):
            if px[y][x] and img[y0+y][x0+x] is not None: img[y0+y][x0+x]=col
    return W
def clear(img,x0,y0,x1,y1,col=0,only=None):
    for y in range(y0,y1):
        for x in range(x0,x1):
            if img[y][x] is not None and (only is None or img[y][x] in only): img[y][x]=col

# ---------------------------------------------------------------- edits
def bg_restore(img,x0,y0,x1,y1,srcx):
    """replace pixels by the background at the same row from column srcx (+x%8 parity)"""
    for y in range(y0,y1):
        for x in range(x0,x1):
            if img[y][x] is not None: img[y][x]=img[y][srcx+(x%8)]
def stack(img,letters,xc,y0,col=3,gap=1):
    y=y0
    for ch in letters:
        px,W=ptext.render(ch,bold=True)
        x0=xc-W//2
        for yy in range(6):
            for xx in range(W):
                if px[yy][xx] and img[y+yy][x0+xx] is not None: img[y+yy][x0+xx]=col
        y+=6+gap
def edit_picture(nm,img):
    if nm=='orig_0D_7851':                       # puha ~ tsu! (drinking) -> "Pwah!"
        clear(img,30,6,78,17,0,only=(1,2,3))
        draw_text(img,'Pwah!',36,8)
    elif nm=='orig_0C_6D36':                     # ou! (Shiine) -> "Oh!"
        clear(img,72,0,88,38,0,only=(1,2,3))
        W=ptext.width('Oh!',True); assert W<=16
        draw_text(img,'Oh!',72+(16-W)//2,10)
    elif nm=='fail_06_7BF2':                     # hau x3 (crying) -> stacked "SOB"
        for (x0,y0,x1,y1) in ((32,0,48,22),(17,16,34,41),(114,4,128,28)):
            bg_restore(img,x0,y0,x1,min(y1,24),8)
            if y1>24: clear(img,x0,24,x1,y1,0)
        stack(img,'SOB',39,1); stack(img,'SOB',27,19); stack(img,'SOB',120,5)
    elif nm=='pic_0D_72E2':                      # Shiine: yokuyattazo! -> "Well done!", chikushoo (vertical) -> "Dang it!"
        clear(img,8,8,48,16,0,only=(1,2,3))
        px,W=ptext.render('Well done!',bold=False,space=2); assert W<=40
        for y in range(8):
            for x in range(W):
                if px[y][x]: img[8+y][8+(40-W)//2+x]=3
        clear(img,56,0,64,38,0,only=(1,2,3))
        px,W=ptext.render('Dang it!',bold=False); m=rot_cw(px); assert W<=36
        for y,row in enumerate(m):
            for x,v in enumerate(row):
                if v: img[1+(36-W)//2+y][56+x]=3
    elif nm=='pic_0C_6865':                      # ChaCha: shuumai -> "Pastries!" (heart kept), hautsu -> "Oof!" (small heart kept)
        clear(img,24,0,73,15,0,only=(1,2,3))
        big(img,'Pastries!',24,-1,11)
        clear(img,34,17,56,26,0,only=(3,))
        draw_text(img,'Oof!',34,18,bold=True)
    elif nm=='pic_06_775E':                      # Suzu: po -> blush hatching "///" (heart kept)
        clear(img,74,9,89,21,0,only=(1,2))
        for k in range(3):
            for i in range(6): img[18-i][76+k*4+i//2]=2
    elif nm=='pic_0C_76CC':                      # Marin: gyoe ~ -> "Gyaaah" (the ~ ~ ~! swoosh kept); todo ga (vertical) removed
        clear(img,16,16,54,32,0,only=(3,))
        big(img,'Gyaaah',16,14,12,outline=0)
        clear(img,128,20,138,41,0,only=(1,3))
    return img
def rot_cw(px):
    H=len(px); W=len(px[0])
    return [[px[H-1-x][y] for x in range(H)] for y in range(W)]
def big(img,text,x0,y0,size,col=3,outline=None):
    from PIL import Image,ImageDraw,ImageFont
    F=ImageFont.truetype(ptext.BIGFONT,size)
    W=F.getbbox(text)[2]; im=Image.new('1',(W+2,20),0); d=ImageDraw.Draw(im); d.fontmode='1'; d.text((1,0),text,font=F,fill=1)
    pts=[(x,y) for y in range(20) for x in range(W+2) if im.getpixel((x,y))]
    if outline is not None:
        for x,y in pts:
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                X,Y=x0+x+dx-1,y0+y+dy
                if 0<=Y<len(img) and 0<=X<len(img[0]) and img[Y][X] is not None: img[Y][X]=outline
    for x,y in pts:
        X,Y=x0+x-1,y0+y
        if 0<=Y<len(img) and 0<=X<len(img[0]) and img[Y][X] is not None: img[Y][X]=col
PICS={'orig_0D_7851':0x2FEA0,'orig_0C_6D36':0x2FF30,'fail_06_7BF2':0x2FFAE,
      'pic_0D_72E2':0x2FE73,'pic_0C_6865':0x2FF15,'pic_06_775E':0x2FF90,'pic_0C_76CC':0x2FF63}   # record offsets (bank 0B $7EA0/$7F30/$7FAE)

def burst_img(data):
    img=[[0]*40 for _ in range(32)]
    for k in range(20):
        i,h=k//2,k%2; sx=(i%5)*8; sy=(i//5)*16+h*8
        for y in range(8):
            lo,hi=data[k*16+2*y],data[k*16+2*y+1]
            for x in range(8): img[sy+y][sx+x]=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
    return img
def burst_data(img):
    out=bytearray()
    for k in range(20):
        i,h=k//2,k%2; sx=(i%5)*8; sy=(i//5)*16+h*8
        for y in range(8):
            lo=hi=0
            for x in range(8):
                v=img[sy+y][sx+x]; lo|=(v&1)<<(7-x); hi|=((v>>1)&1)<<(7-x)
            out+=bytes([lo,hi])
    return bytes(out)
def edit_burst(img):
    # chudoon above the cloud (rows 0-9) -> "KABOOM"; cloud colours 1/2 kept below
    for y in range(0,10):
        for x in range(40):
            if y<8 or img[y][x]==3: img[y][x]=0
    for y in range(10,15):                       # tails of chi / n beside the cloud
        for x in range(40):
            if (x<9 and img[y][x] in (1,3)) or (x>=29 and img[y][x]==3): img[y][x]=0
    W=ptext.width('BOOM!',True)
    draw_text(img,'BOOM!',(40-W)//2,1,col=3,outline=1)
    return img

def record_tilemaps(rom,rec_off):
    """picture record (bank 0B): bank,len(2),src(2), then commands: 00/01 msg(2) | FF end | xx ptr(2) -> tilemap
    (in the record's bank: rows, cols, data) blitted at $98C0 by $1F36. Returns list of (ptr, rows as lists)."""
    b=rom[rec_off]; o=rec_off+5; out=[]
    while True:
        a=rom[o]
        if a==0xFF: break
        if a in (0,1): o+=3; continue
        p=rom[o+1]|rom[o+2]<<8; o+=3
        q=b*0x4000+p-0x4000; nr,nc=rom[q],rom[q+1]
        out.append((p,[list(rom[q+2+r*nc:q+2+(r+1)*nc]) for r in range(nr)]))
    return out

# ---------------------------------------------------------------- Holy Falls sign (OBJ stream 0B:6D3D, 0x40 bytes)
def sign_img(data):
    img=[[0]*16 for _ in range(16)]
    for k in range(4):                   # 8x16 sprites: 48/49 left column, 4A/4B right column
        sx=(k//2)*8; sy=(k%2)*8
        for y in range(8):
            lo,hi=data[k*16+2*y],data[k*16+2*y+1]
            for x in range(8): img[sy+y][sx+x]=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
    return img
def sign_data(img):
    out=bytearray()
    for k in range(4):
        sx=(k//2)*8; sy=(k%2)*8
        for y in range(8):
            lo=hi=0
            for x in range(8):
                v=img[sy+y][sx+x]; lo|=(v&1)<<(7-x); hi|=((v>>1)&1)<<(7-x)
            out+=bytes([lo,hi])
    return bytes(out)
def edit_sign(img):
    # taki ("falls") is too long for a 12x14 board in English: a water-drop mark instead (engine VWF drop glyph)
    for y in range(3,13):
        for x in range(4,10): img[y][x]=1    # board face (x 4-9); right shading x 10-11 kept
    DROP=['..3..','..3..','.333.','.333.','33333','31333','33333','.333.']   # water drop, highlight colour 1
    x0=4+(6-5)//2; y0=3+1
    for y,row in enumerate(DROP):
        for x,ch in enumerate(row):
            if ch!='.': img[y0+y][x0+x]=int(ch)
    return img
