"""Balanced 12px prompt; retain original A pixels, move whole group to center."""
from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
from environment import PROJECT as R, OUTPUT, FONT_ROOT
def build_title(original,put):
 table=0x3576+100*4;start=int.from_bytes(original[table:table+4],'little')-0x200000
 end=int.from_bytes(original[table+4:table+8],'little')-0x200000;p=start+2
 for _ in range(48):p+=2 if original[p:p+2]==b'\x00\x80' else 6
 w,h=original[p:p+2];p+=2;maps=p;p+=w*h*4
 ns=int.from_bytes(original[p:p+2],'little');p+=2+ns*4
 countoff=p;nt=int.from_bytes(original[p:p+2],'little');raw=p+2
 assert(w,h)==(20,19)and raw+nt*16==end
 asset=bytearray(original[start:end]);extra=[];cache={}
 def mapcell(cx,cy,bg,fg=0xffff):
  a=maps-start+(cy*w+cx)*4;asset[a:a+4]=bg.to_bytes(2,'little')+fg.to_bytes(2,'little')
 red=Image.new('L',(160,152),1)
 for cy in (11,12):
  for cx in (8,9,10):
   a=maps+(cy*w+cx)*4;entry=int.from_bytes(original[a:a+2],'little');assert entry>>9==7
   tile=original[raw+(entry&511)*16:raw+((entry&511)+1)*16]
   for y in range(8):
    v=int.from_bytes(tile[y*2:y*2+2],'little')
    for x in range(8):red.putpixel((cx*8+x-2,cy*8+y),(v>>(14-2*x))&3)
 mask=Image.new('L',(160,152));d=ImageDraw.Draw(mask)
 f=ImageFont.truetype(str(FONT_ROOT/'fusion12/fusion-pixel-12px-monospaced-zh_hans.otf'),12)
 d.text((51,102),'按',font=f,anchor='ls',fill=255);d.text((86,102),'继续',font=f,anchor='ls',fill=255)
 for cy in (11,12):
  for cx in range(1,19):mapcell(cx,cy,0)
  for cx in range(6,14):
   pair=[]
   for layer in (0,1):
    words=[]
    for y in range(8):
     words.append(sum((red.getpixel((cx*8+x,cy*8+y))if layer==0 else(1 if mask.getpixel((cx*8+x,cy*8+y))>=128 else 0))<<(14-2*x)for x in range(8)))
    bitmap=b''.join(v.to_bytes(2,'little')for v in words)
    if bitmap not in cache:
     idx=249+len(extra);assert idx<269
     cache[bitmap]=idx;extra.append(bitmap)
     a=raw-start+idx*16;asset[a:a+16]=bitmap
    idx=cache[bitmap];pair.append(idx|((7 if layer==0 else 6)<<9))
   mapcell(cx,cy,*pair)
 assert len(asset)==end-start  # Reuse original prompt tile slots; preserve load duration.
 at=0xd5000;assert at+len(asset)<0xd8000 and original[at:at+len(asset)]==bytes(len(asset))
 put(at,bytes(asset),'title artwork with balanced 5px gaps around original A icon')
 put(table,(0x200000+at).to_bytes(4,'little'),'title resource pointer')
 return {'resource':100,'new_offset':at,'size':len(asset),'prompt_font_px':12,'circle_A_shape_unchanged':True,'circle_A_shift_px':-2,'prompt_ink_center':79.5,'gaps_px':[5,5]}
