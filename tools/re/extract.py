"""Extract all known text from Akazukin Chacha (J) GB.
python3 -I tools/re/extract.py ROM OUTDIR -> OUTDIR/strings.json, OUTDIR/all_strings.csv
(ROM defaults to $CHACHA_ROM, OUTDIR to $CHACHA_WORK/re). Both outputs contain game text: keep them out of git."""
import sys,json,csv,hashlib,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from chacha_common import *
rom=sys.argv[1] if len(sys.argv)>1 else ORIG
if not rom: sys.exit(__doc__)
OUT=sys.argv[2] if len(sys.argv)>2 else os.path.join(os.environ.get('CHACHA_WORK') or os.path.join(HERE,'..','..','build','work'),'re')
os.makedirs(OUT,exist_ok=True)
r=open(rom,'rb').read()

recs={}      # key: file offset of string start -> record
def add(block,bank,ptr_loc,addr,label,ctx='',fixed_len=None,encoding='ctrl'):
    o=off(bank,addr)
    if fixed_len is not None:
        raw=r[o:o+fixed_len]
        jp=''.join(T.get(b,GLYPH_EXTRA.get(b,'{%02X}'%b)) for b in raw); calls=[]
    elif encoding=='raw':   # name strings: printed raw until EF (no control processing)
        e=r.index(0xEF,o); raw=r[o:e+1]
        jp=''.join(T.get(b,GLYPH_EXTRA.get(b,'{%02X}'%b)) for b in raw[:-1])+'<END>'; calls=[]
    else:
        jp,raw,calls=decode(r,o,bank)
    if o in recs:
        rec=recs[o]
        if ptr_loc is not None and ptr_loc not in rec['ptr_locs']: rec['ptr_locs'].append(ptr_loc)
        rec['aliases'].append(label)
        return rec
    rec=dict(id=label,block=block,bank=bank,addr='$%04X'%addr,ptr_locs=[ptr_loc] if ptr_loc is not None else [],
             off=o,raw_hex=raw.hex(),jp=jp,max_bytes=len(raw),ctx=ctx,aliases=[],
             calls=['$%04X'%a for _,a in calls],fixed=fixed_len is not None,encoding=encoding if fixed_len is None else 'fixed')
    recs[o]=rec; return rec

# 1. master dialogue table: bank 0E $4000, 0x559 words; text bank chosen by ID (see id_bank)
for i in range(MASTER_N):
    pl=off(MASTER_BANK,MASTER_PTR+2*i); a=u16(r,pl); b=id_bank(i)
    add('dlg',b,pl,a,'dlg_%03X'%i,ctx='master id 0x%03X'%i)
# FB sub-strings that are not already table entries
for rec in list(recs.values()):
    for c in rec['calls']:
        a=int(c[1:],16); add('dlg',rec['bank'],None,a,'sub_%02X_%04X'%(rec['bank'],a),ctx='FB call target from '+rec['id'])
# 2. name tables in bank 0E, raw-printed until EF by $00:3E08 / $00:1495
for blk,base,n,ctx in [('nick',0x4AB2,72,'F4/F5: nickname table, idx = speaker(CE41)*6 + who(C8D2/C8D1)'),
                       ('item',0x4BD1,64,'F6/F7 + battle hand slots ($00:1495): item names'),
                       ('name',0x4C51,54,'F8: enemy / character names (idx C8D3)')]:
    for i in range(n):
        pl=off(0xE,base+2*i); a=u16(r,pl)
        add(blk,0xE,pl,a,'%s_%02X'%(blk,i),ctx=ctx,encoding='raw')
# 3. fixed-length records
for i in range(6):
    add('cmd',0,None,0x1476+5*i,'cmd_%d'%i,ctx='battle special command name, 5-byte record (bank0 $1476+5*i), copied to $9C62',fixed_len=5)
FIXED_EXTRA=[
 ('title_new',4,0x4B33,6,'title menu NEW GAME (inside title screen layout data at 04:$4B22, format not decoded)'),
 ('title_cont',4,0x4B39,6,'title menu CONTINUE'),
 ('bmenu_r1',2,0x784F,18,'battle command window row 1 (raw 20-wide tilemap at 02:$77xx; kana are tile ids)'),
 ('bmenu_r2',2,0x7863,18,'battle command window row 2'),
 ('pw_title',3,0x69B4,14,'password screen title (tilemap row)'),
 ('pw_error',4,0x460F,37,'password error message (tilemap rows, 18+ bytes)'),
 ('report_title',2,0x5224,10,'report card title (tilemap)'),
 ('report_parents',2,0x5311,12,'report card: to parents (tilemap)'),
 ('report_pts',2,0x7A2F,15,'report card: points / signature (tilemap)'),
 ('gameover',3,0x4F41,28,'game over / continue screen text (tilemap command data)'),
 ('rank_words',0,0x1A8B,25,'bank0 word list (amadamada/hodohodo/atochotto/mousukoshi), likely result rating'),
]
# quest-goal strings: 6 pointers at 03:$4F7B (EF-terminated, printed by unknown routine)
QUEST=(3,0x4F7B,6)
ORPHANS=[(6,0x7451),(0xE,0x57BE)]
for lbl,bank,addr,n,ctx in FIXED_EXTRA:
    add('fixed',bank,None,addr,lbl,ctx=ctx,fixed_len=n)

for i in range(QUEST[2]):
    pl=off(QUEST[0],QUEST[1]+2*i); add('quest',3,pl,u16(r,pl),'quest_%d'%i,ctx='quest goal list, ptr table 03:$4F7B',encoding='raw')
for b,a in ORPHANS:
    add('orphan',b,None,a,'orphan_%02X_%04X'%(b,a),ctx='EF-terminated dialogue with no known pointer (unused?)')
# overlap detection
L=sorted(recs.values(),key=lambda x:x['off'])
for a,b in zip(L,L[1:]):
    if b['off']<a['off']+a['max_bytes']:
        a.setdefault('contains',[]).append(b['id']); b['inside']=a['id']
out=L
json.dump(out,open(os.path.join(OUT,'strings.json'),'w'),ensure_ascii=False,indent=1)
with open(os.path.join(OUT,'all_strings.csv'),'w',newline='') as f:
    w=csv.writer(f); w.writerow(['id','block','bank','addr','file_off','ptr_locs','max_bytes','raw_hex','jp','ctx'])
    for x in out: w.writerow([x['id'],x['block'],'%02X'%x['bank'],x['addr'],'%05X'%x['off'],' '.join('%05X'%p for p in x['ptr_locs']),x['max_bytes'],x['raw_hex'],x['jp'],x['ctx']])
# summary
from collections import Counter
def jpchars(s):
    import re; s=re.sub(r'<[^>]*>|\{[^}]*\}','',s); return sum(1 for c in s if c not in ' \n\u309b\u309c')
cnt=Counter(); ch=Counter(); by=Counter()
for x in out: cnt[x['block']]+=1; ch[x['block']]+=jpchars(x['jp']); by[x['block']]+=x['max_bytes']
for k in cnt: print('%-6s strings %5d  jp_chars %6d  bytes %6d'%(k,cnt[k],ch[k],by[k]))
print('total',sum(cnt.values()),sum(ch.values()),sum(by.values()))
print('overlaps',sum(1 for x in out if 'inside' in x))
