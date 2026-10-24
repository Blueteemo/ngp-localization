"""Replace only Japanese status lettering in original three bitmap cards.
Palette, border, music-note pattern and character art stay in their original form.
The format was verified against the game's live 202640/2026A7 asset loader.
"""
from pathlib import Path
from PIL import Image,ImageFont,ImageDraw
from environment import PROJECT as R, OUTPUT, FONT_ROOT
def build_assets(original,put,cursor):
 font=ImageFont.truetype(str(FONT_ROOT/'fusion10/fusion-pixel-10px-monospaced-zh_hans.otf'),10)
 results=[]
 for idx,lines,ys in [(101,['正在','保存','存档'],[27,45,65]),(102,['正在','初始化','存档'],[27,45,65]),(103,['开始','菜单'],[37,57])]:
  table=0x3576+idx*4;start=int.from_bytes(original[table:table+4],'little')-0x200000;p=start+2;pals=[]
  for _ in range(48):
   v=int.from_bytes(original[p:p+2],'little')
   if v==0x8000:p+=2;pals.append([None]*4)
   else:pals.append([None]+[int.from_bytes(original[p+k:p+k+2],'little')for k in [0,2,4]]);p+=6
  w,h=original[p:p+2];p+=2;maps=p;p+=w*h*4;ns=int.from_bytes(original[p:p+2],'little');p+=2+ns*4;countoff=p;nt=int.from_bytes(original[p:p+2],'little');p+=2;raw=p;end=p+nt*16
  assert w==20 and h==11 and ns==0
  assert end==int.from_bytes(original[table+4:table+8],'little')-0x200000
  asset=bytearray(original[start:end]);mask=Image.new('L',(w*8,h*8));draw=ImageDraw.Draw(mask)
  for line,y in zip(lines,ys):draw.text(((72-len(line)*10)//2,y),line,font=font,anchor='ls',fill=255)
  bg=pals[8][2];ink=pals[8][3];extra=[]
  for cy in range(2,9):
   for cx in range(1,8):
    ma=maps+(cy*w+cx)*4;entry=int.from_bytes(original[ma:ma+2],'little');assert entry!=65535 and entry&0xc000==0
    tile=entry&511;pal=(entry>>9)&15;rawtile=original[raw+tile*16:raw+(tile+1)*16];assert bg in pals[pal]
    bgi=pals[pal].index(bg);words=[int.from_bytes(rawtile[y*2:y*2+2],'little')for y in range(8)];changed=False
    for y in range(8):
     for x in range(8):
      sx=cx*8+x;sy=cy*8+y
      if 12<=sx<60 and 16<=sy<72:
       value=bgi
       if mask.getpixel((sx,sy))>=128:
        assert ink in pals[pal],(idx,cx,cy);value=pals[pal].index(ink)
       before=(words[y]>>(14-2*x))&3
       if value!=before:words[y]=(words[y]&~(3<<(14-2*x)))|(value<<(14-2*x));changed=True
    if changed:
     newindex=nt+len(extra);assert newindex+20<404
     extra.append(b''.join(v.to_bytes(2,'little')for v in words))
     a=ma-start;asset[a:a+2]=((entry&~511)|newindex).to_bytes(2,'little')
  a=countoff-start;asset[a:a+2]=(nt+len(extra)).to_bytes(2,'little');asset+=b''.join(extra)
  assert original[cursor:cursor+len(asset)]==bytes(len(asset))
  at=cursor;cursor+=len(asset);assert cursor<0xdf000
  put(at,bytes(asset),'Chinese status bitmap card '+str(idx))
  put(table,(0x200000+at).to_bytes(4,'little'),'status bitmap resource pointer '+str(idx))
  results.append({'resource':idx,'original':start,'relocated':at,'old_tiles':nt,'new_tiles':nt+len(extra),'text':lines,'caption_roi':[12,16,60,72]})
 return cursor,results
