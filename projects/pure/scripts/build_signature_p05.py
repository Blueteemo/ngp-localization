"""Credit drawing routine called by the post-transition menu-ready wrapper.

The register-preserving routine writes unused title tiles and palette 3, then
maps rows 9/10. Initial title and animation do not invoke it.
"""
from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
from environment import PROJECT as R, OUTPUT, FONT_ROOT
def build_signature(original,put):
 f=ImageFont.truetype(str(FONT_ROOT/'fusion10/fusion-pixel-10px-monospaced-zh_hans.otf'),10)
 label='汉化：千岚之夏';m=Image.new('L',(70,10))
 ImageDraw.Draw(m).text((0,8),label,font=f,anchor='ls',fill=255);m=m.crop(m.getbbox())
 mask=Image.new('L',(160,152));mask.paste(m,((160-m.width)//2,75))
 writes=[]
 def byte(a,v):writes.append((a,v))
 def word(a,v):byte(a,v&255);byte(a+1,v>>8)
 # Scroll palette 3: transparent/grey/white/white.
 for a,v in [(0x829a,0x555),(0x829c,0xfff),(0x829e,0xfff)]:word(a,v)
 slot=352
 for cy in (9,10):
  for cx in range(5,15):
   for y in range(8):
    v=sum((1 if mask.getpixel((cx*8+x,cy*8+y))>=128 else 3)<<(14-2*x)for x in range(8))
    word(0xa000+slot*16+y*2,v)
   word(0x9000+(cy*32+cx)*2,slot|(3<<9))
   word(0x9800+(cy*32+cx)*2,0)
   slot+=1
 # F1 abs16 00 imm8: LD (absolute address), immediate byte. No register clobber.
 routine=b''.join(b'\xf1'+a.to_bytes(2,'little')+bytes([0,v])for a,v in writes)+b'\x0e'
 at=0xd8000;assert at+len(routine)<0xdf000
 assert original[at:at+len(routine)]==bytes(len(routine))
 put(at,routine,'title-menu-only dark grey localization credit')
 return {'text':label,'color_rgb':[85,85,85],'font_px':10,'y':75,'routine':at,'bytes':len(routine),'tile_range':[352,371],'scope':'original menu-ready script after slide, title text context only'}
