"""Check tracked publication files, not local ignored ROMs/font caches."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
blocked={'.ngc','.ngp','.rom','.bios','.flash','.sav','.state','.s0','.mem','.so','.dll','.dylib','.mp4','.wav','.ips','.otf'}
bad=[]
for name in filter(None,paths):
 p=root/name
 if p.suffix.lower()in blocked:bad.append(name)
 if p.is_file()and p.suffix in ('.md','.py','.json','.toml','.yml'):
  text=p.read_text(encoding='utf-8')
  # Keep this check self-contained without embedding the prohibited local strings.
  markers=['/workspace/'+'scratch/','libfile'+'_','https://drive.google.com/'+'file/d/']
  if any(x in text for x in markers):bad.append(name+': local/private reference')
if bad:
 print('\n'.join(bad));sys.exit(1)
print('Tracked public tree contains no blocked binaries or private workspace references')
