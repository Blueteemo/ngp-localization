from pathlib import Path
import json,hashlib
from PIL import Image
from native_session import machine,run,press,write_png
from environment import PROJECT as R, OUTPUT, EVIDENCE, ROM, BEETLE_CORE, BASELINE
rom=ROM
p=EVIDENCE/'signature';p.mkdir(parents=True,exist_ok=True)
m=machine(rom);counts={}
def shot(name,present):
 write_png(m,p/(name+'.png'));im=Image.open(p/(name+'.png')).convert('RGB')
 count=sum(im.getpixel((x,y))==(85,85,85)for y in range(75,84)for x in range(40,120))
 assert(count>100)if present else(count==0),(name,count)
 counts[name]=count
run(m,1200);press(m,16,3,150);shot('before_menu',False)
press(m,16,3,300);shot('menu',True)
press(m,2);press(m,2);press(m,16,3,720);shot('options',False)
# Original settings exit returns to the title prompt, not straight to the menu.
press(m,32,3,600);shot('returned_title',False)
press(m,16,3,300);shot('returned_menu',True)
result={'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'native_menu_hw_violations':m.hw_violations(),'signature_gray_pixel_counts':counts,'title_to_menu_options_title_menu_verified':True}
assert result['native_menu_hw_violations']==0
m.close();(p/'result.json').write_text(json.dumps(result,indent=2));print(result)
