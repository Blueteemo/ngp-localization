"""Frame-by-frame check: credit must wait for the original menu-ready state."""
from pathlib import Path
import sys,json,hashlib,tempfile
from PIL import Image,ImageDraw
from libretro_frontend import Core
from native_session import machine,run,write_png
from environment import PROJECT as R, OUTPUT, EVIDENCE, ROM, BEETLE_CORE, BASELINE;kind=sys.argv[1];assert kind in ('med','native')
rom=ROM
p=EVIDENCE/'transition'/kind;p.mkdir(parents=True,exist_ok=True)
sha=hashlib.sha256(rom.read_bytes()).hexdigest()
if kind=='med':
 save=tempfile.TemporaryDirectory();c=Core(BEETLE_CORE,rom,Path(save.name))
 def step(n,key=False):c.run(n,[0]if key else[])
 def readptr():return int.from_bytes(c.memory()[0x148:0x14c],'little')
 def frame():return c.frame.convert('RGB').copy()
 grey=(82,85,82)
else:
 c=machine(rom)
 def step(n,key=False):run(c,n,16 if key else 0)
 def readptr():return int.from_bytes(c.read(0x4148,4),'little')
 def frame():
  write_png(c,p/'current.png');return Image.open(p/'current.png').convert('RGB').copy()
 grey=(85,85,85)
step(1200);step(3,True);step(150);rows=[];images=[]
for i in range(90):
 step(1,i<3);im=frame();images.append(im)
 count=sum(im.getpixel((x,y))==grey for y in range(75,84)for x in range(40,120))
 rows.append({'after_A':i+1,'signature_pixels':count,'menu_script':hex(readptr())})
(p/'trace.json').write_text(json.dumps(rows,indent=2))
# Native may complete the initial menu setup within the same sampled frame;
# 0x2912F6 is its next original input-loop wait, reached only after setup.
ready=next(x['after_A']for x in rows if x['menu_script']in('0x2912d8','0x2912f6'))
first=next(x['after_A']for x in rows if x['signature_pixels']>100)
assert ready==first,(ready,first)
assert all(x['signature_pixels']==0 for x in rows if x['after_A']<ready)
assert all(x['signature_pixels']>100 for x in rows if x['after_A']>=ready)
hw=c.hw_violations()if kind=='native'else None
assert hw in (None,0)
c.close()
if kind=='med':save.cleanup()
for name,i in [('before',2),('during',20),('ready',ready-1)]:images[i].save(p/(name+'.png'))
if kind=='med':
 frames=[]
 for im in images[::2]:frames.append(im.resize((480,456),Image.Resampling.NEAREST))
 frames[0].save(OUTPUT/'menu_transition.gif',save_all=True,append_images=frames[1:],duration=[30,30,40]*14+[30,30,1200],loop=0)
out=Image.new('RGB',(480,172),'#eee');d=ImageDraw.Draw(out)
for x,(label,i)in enumerate([('Before',2),('During',20),('Ready',ready-1)]):d.text((x*160+5,5),label,fill='black');out.paste(images[i],(x*160,20))
out.resize((960,344),Image.Resampling.NEAREST).save(p/'sequence.png')
assert hashlib.sha256(rom.read_bytes()).hexdigest()==sha
result={'rom_sha256':sha,'core':kind,'frames_captured':90,'menu_ready_after_A':ready,'signature_first_after_A':first,'signature_absent_through_transition':True,'signature_stays_visible_when_ready':True,'hardware_violations':hw,'trace':rows}
(p/'result.json').write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items()if k!='trace'})
