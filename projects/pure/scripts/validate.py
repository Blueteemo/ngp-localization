from pathlib import Path
import sys,json,hashlib,tempfile
from environment import PROJECT as R, OUTPUT, EVIDENCE, ROM, BEETLE_CORE, BASELINE
from libretro_frontend import Core
from native_session import machine,run,write_png
kind=sys.argv[1];assert kind in ['med','native']
rom=ROM
initial_sha=hashlib.sha256(rom.read_bytes()).hexdigest()
m=json.loads((OUTPUT/'P05_patch.json').read_text());mp={x['new_offset']+0x200000:x['original_offset']+0x200000 for x in m['fields']};demo={x['original_offset']+0x200000 for x in m['fields']if x['original_offset']>=0xca000}
P=EVIDENCE/'validation'/kind;P.mkdir(parents=True,exist_ok=True)
if kind=='med':
 fresh_save=tempfile.TemporaryDirectory(prefix='fresh_boot_',dir=P)
 c=Core(BEETLE_CORE,rom,Path(fresh_save.name));step=lambda:c.run(1);pointer=lambda:int.from_bytes(c.memory()[0x256:0x25a],'little');shot=lambda p:c.screenshot(p)
else:
 c=machine(rom);step=lambda:run(c,1);pointer=lambda:int.from_bytes(c.read(0x4256,4),'little');shot=lambda p:write_png(c,p)
events=[];last=None;seen=set();pending=[]
for f in range(1,17501):
 step();ptr=pointer()
 if ptr!=last:
  original=mp.get(ptr,ptr);events.append({'frame':f,'pointer':original});last=ptr
  if ptr in mp and original in demo and original not in seen:seen.add(original);pending.append((f+150,original))
 for due,addr in list(pending):
  if f==due:shot(P/f'{addr:06x}.png');pending.remove((due,addr))
 if f==4800:shot(P/'title_prompt.png')
hw=None
if kind=='native':hw={'violations':c.hw_violations()}
c.close()
if kind=='med':fresh_save.cleanup()
baseline=R/'reference'/('med_original_events.json'if kind=='med'else'native_original_events.json')
a=[x for x in json.loads(baseline.read_text())if x['ptr']in demo];b=[x for x in events if x['pointer']in demo and x['frame']>1]
assert len(a)>=24 and len(b)>=24
rows=[{'pointer':hex(x['ptr']),'original_frame':x['frame'],'translated_frame':y['frame'],'difference':y['frame']-x['frame']}for x,y in zip(a[:24],b[:24])]
(P/'timing_comparison.json').write_text(json.dumps({'expected':a[:24],'actual':b[:24],'rows':rows},indent=2))
assert all(x['ptr']==y['pointer']and x['frame']==y['frame']for x,y in zip(a[:24],b[:24]))
assert seen==demo,(seen,demo)
assert hashlib.sha256(rom.read_bytes()).hexdigest()==initial_sha,'ROM changed during validation'
result={'rom_sha256':initial_sha,'core':kind,'frames':17500,'opening_fields_reached':len(seen),'matched_opening_landmarks':24,'all_landmarks_same_frame':True,'hardware_diagnostics':hw,'landmarks':rows}
(P/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='landmarks'}))
from PIL import Image
narration_visible=Image.open(P/'2ca682.png').convert('L').getextrema()[1]>100
result['opening_black_background_narration_visible']=narration_visible
result['visual_status']='narration visible; inspect other captures' if narration_visible else 'known blank narration; trace success is not visual success'
(P/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'opening_narration_visible':narration_visible,'visual_status':result['visual_status']}))
