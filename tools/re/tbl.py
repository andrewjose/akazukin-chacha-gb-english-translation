"""Table helpers. Encoding = BG tile index in the 0x8800-mode font block (font loaded to $9000).
The table itself lives in chacha.tbl (next to this file):
  T           codes 00-75: kana / punctuation of the game font (00-2D hiragana, 2E-36 small hiragana,
              37-64 katakana, 65-6D small katakana, 6E dakuten, 6F handakuten, 70-75 punctuation)
  GLYPH_EXTRA codes 76-7F, 8E, 8F, FF: frame pieces, scene-loaded kanji tiles, blank
enc(s) encodes kana text (voiced kana are written as base kana + separate dakuten/handakuten cell)."""
import os,re,unicodedata
TBL=os.path.join(os.path.dirname(os.path.abspath(__file__)),'chacha.tbl')
ALL={}
for ln in open(TBL,encoding='utf-8'):
    m=re.match(r'^([0-9A-F]{2})=(.*)$',ln.rstrip('\n'))
    if m: ALL[int(m.group(1),16)]=m.group(2)
T={k:v for k,v in ALL.items() if k<=0x75}
GLYPH_EXTRA={k:v for k,v in ALL.items() if k>0x75}
R={v:k for k,v in T.items()}
DAKU,HANDAKU=chr(0x3099),chr(0x309A)      # combining voiced / semi-voiced marks
def enc(s):
    out=[]
    for ch in s:
        d=unicodedata.normalize('NFD',ch)
        if len(d)==2 and d[1]==DAKU: out+=[R[d[0]],0x6E]
        elif len(d)==2 and d[1]==HANDAKU: out+=[R[d[0]],0x6F]
        elif ch==' ': out.append(0xFF)
        else: out.append(R[ch])
    return bytes(out)
