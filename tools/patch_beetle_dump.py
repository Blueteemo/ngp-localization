"""Optional read-only diagnostic export needed only by deeper memory inspection.

The shipped Pure menus/recording paths do not require this function.
"""
import argparse
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("checkout",type=Path)
a=p.parse_args()
file=a.checkout/'libretro.c'
text=file.read_text()
if 'retro_pure_dump' in text:
 print('Diagnostic export already present')
else:
 text+='''
/* ngp-localization: read-only bus inspection, no emulation behavior changes. */
extern uint8_t loadB(uint32_t address);
void retro_pure_dump(uint32_t address, uint8_t *out, uint32_t count)
{
   uint32_t i;
   for (i = 0; i < count; i++) out[i] = loadB(address + i);
}
'''
 file.write_text(text)
 print('Added optional read-only export; rebuild the core')
