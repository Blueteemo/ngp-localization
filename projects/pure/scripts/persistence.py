from pathlib import Path
import sys,json,hashlib,shutil
from PIL import Image,ImageChops
from environment import PROJECT as R, OUTPUT, EVIDENCE, ROM, BEETLE_CORE, BASELINE
from libretro_frontend import Core
ROM=ROM;LIB=BEETLE_CORE
P=EVIDENCE/'persistence';P.mkdir(parents=True,exist_ok=True);source=EVIDENCE/'menus/persistent'
log=json.loads((source.parent/'log.json').read_text());expected=next(x['script']for x in log if x['name']=='story_next')
c=Core(LIB,ROM,source);c.run(1200);c.press(0,3,150);c.press(0,3,300);c.press(5);c.press(0,3,600);c.screenshot(P/'slot_information.png');c.press(0,3,500);c.screenshot(P/'load_prompt.png');c.press(0,3,900);c.screenshot(P/'loaded.png')
before=hex(int.from_bytes(c.memory()[0x256:0x25a],'little'));assert before==expected,(before,expected)
c.press(0,3,300);c.screenshot(P/'next_page.png');after=hex(int.from_bytes(c.memory()[0x256:0x25a],'little'));assert after!=before;c.close()
# The write happened in test_p02_menus.py's terminated process. This process
# loaded it without using a state or modifying the ROM/RAM script position.
I=P/'initialize';I.mkdir(exist_ok=True);shutil.copytree(source,I/'save',dirs_exist_ok=True);old={x.name:hashlib.sha256(x.read_bytes()).hexdigest()for x in(I/'save').iterdir()}
c=Core(LIB,ROM,I/'save');c.run(1200);c.press(0,3,150);c.press(0,3,300);c.press(5);c.press(5);c.press(0,3,720);c.press(5);c.press(0,3,300);c.press(5);c.press(0,3,600);c.screenshot(I/'initialized.png');c.press(0,3,300);c.close();new={x.name:hashlib.sha256(x.read_bytes()).hexdigest()for x in(I/'save').iterdir()};assert old!=new
c=Core(LIB,ROM,I/'save');c.run(1200);c.press(0,3,150);c.press(0,3,300);c.press(5);c.press(0,3,600);c.screenshot(I/'empty_slots_after_reboot.png');c.press(0,3,300);c.screenshot(I/'empty_slot_prompt.png');c.close()
result={'rom_sha256':hashlib.sha256(ROM.read_bytes()).hexdigest(),'separate_process_save_load':True,'saved_script':expected,'loaded_script':before,'next_script':after,'loaded_position_exact':True,'progressed':True,'initialize_performed_only_on_copied_disposable_save':True,'initialized_flash_changed':old!=new}
(P/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
