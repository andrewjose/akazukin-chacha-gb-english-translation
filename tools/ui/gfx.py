"""tile helpers: 2bpp <-> image"""
from PIL import Image
def tiles_img(data,cols=16,scale=2,pal=(255,170,85,0)):
    n=len(data)//16; rows=(n+cols-1)//cols
    img=Image.new('L',(cols*8,rows*8),128)
    for t in range(n):
        for y in range(8):
            lo,hi=data[t*16+y*2],data[t*16+y*2+1]
            for x in range(8):
                c=((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1)
                img.putpixel(((t%cols)*8+x,(t//cols)*8+y),pal[c])
    return img.resize((img.width*scale,img.height*scale),Image.NEAREST)
