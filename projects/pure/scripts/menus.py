from pathlib import Path
import sys,json,hashlib,ctypes
from PIL import Image,ImageDraw
from environment import PROJECT as R, OUTPUT, EVIDENCE, ROM, BEETLE_CORE, BASELINE
from libretro_frontend import Core
ROM=ROM
initial_sha=hashlib.sha256(ROM.read_bytes()).hexdigest()
P=EVIDENCE/'menus';P.mkdir(parents=True,exist_ok=True)
LIB=BEETLE_CORE
c=Core(LIB,ROM,P/'persistent');log=[]
def shot(name):
 c.screenshot(P/(name+'.png'));log.append({'name':name,'frame':c.frames,'script':hex(int.from_bytes(c.memory()[0x256:0x25a],'little'))})
c.run(1200);c.press(0,3,150);c.press(0,3,300);shot('title_menu');c.save_state(P/'menu.state')
c.press(5);c.press(5);c.press(0,3,720);shot('options');c.save_state(P/'options.state');c.press(0,3,300);shot('buttons');c.press(5);c.press(8,3,360);shot('buttons_B_confirmed')
# Restore a disposable state to inspect initialization, without clearing the save.
c.load_state(P/'options.state');c.press(5);c.press(0,3,300);shot('initialize_prompt');c.press(8,3,300);shot('initialize_cancelled')
c.load_state(P/'menu.state');c.press(5);c.press(5);c.press(5);c.press(0,3,500);shot('extras');c.save_state(P/'extras.state');c.press(0,3,500);shot('CG_mode');c.press(5);c.press(7);shot('CG_switch');c.press(8,3,300)
c.load_state(P/'extras.state');c.press(5);c.press(0,3,500);shot('BGM_mode');c.press(0,3,300);shot('BGM_playing');c.press(5);shot('BGM_next')
c.load_state(P/'menu.state');c.press(0,3,1200);shot('story');c.press(0,3,600);shot('story_next');c.press(3,3,500);shot('in_game_menu');c.save_state(P/'ingame.state')
c.press(0,3,500);shot('save_slots');c.press(0,3,500);shot('save_confirmation');c.press(0,3,600);shot('save_finished');c.close()
(P/'log.json').write_text(json.dumps(log,indent=2))
files=[{'file':p.name,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in (P/'persistent').iterdir()]
(P/'persistent_files.json').write_text(json.dumps(files,indent=2))
fs=[P/(x['name']+'.png')for x in log]
for start in range(0,len(fs),12):
 s=Image.new('RGB',(640,3*180),'#ddd');d=ImageDraw.Draw(s)
 for i,f in enumerate(fs[start:start+12]):x=i%4*160;y=i//4*180;s.paste(Image.open(f),(x,y+20));d.text((x,y),f.stem,fill='black')
 s.save(P/f'sheet{start//12}.png')
assert hashlib.sha256(ROM.read_bytes()).hexdigest()==initial_sha,'ROM changed during validation'
(P/'result.json').write_text(json.dumps({'rom_sha256':initial_sha,'screens_captured':len(log),'scope':'menu capture only; see persistence result'},indent=2))
print('captured',len(log),'persistent',files)
