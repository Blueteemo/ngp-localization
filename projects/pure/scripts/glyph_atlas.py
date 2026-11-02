"""Render only explicitly selected original glyph IDs for local human mapping."""
import argparse
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw
from environment import PROJECT
from ngp_localization.glyph12 import unpack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--id', type=lambda s: int(s, 0), action='append', required=True, dest='ids')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data = args.rom.read_bytes()
    if hashlib.sha256(data).hexdigest() != '5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d':
        raise ValueError('Wrong original baseline')
    ids = sorted(set(args.ids))
    if any(i < 0 or (i + 1) * 18 > 0x10000 for i in ids):
        raise ValueError('Glyph ID falls outside the original font bank')
    if args.out.resolve() == args.rom.resolve() or args.out.exists():
        raise ValueError('Refusing to overwrite existing input/output')
    # Limit a sheet so thousands of IDs do not silently produce an unreadable image.
    if len(ids) > 96:
        raise ValueError('Select at most 96 glyphs per sheet')
    image = Image.new('RGB', (8 * 64, ((len(ids)+7)//8) * 72), 'white')
    draw = ImageDraw.Draw(image)
    for n, gid in enumerate(ids):
        bits = unpack(data[0x10000+gid*18:0x10000+(gid+1)*18])
        x, y = (n % 8) * 64, (n // 8) * 72
        draw.text((x+4,y+2), str(gid), fill='black')
        for gy in range(12):
            for gx in range(12):
                if bits >> (143-gy*12-gx) & 1:
                    draw.rectangle((x+gx*4,y+18+gy*4,x+gx*4+3,y+18+gy*4+3), fill='black')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f'Rendered {len(ids)} selected glyphs; no Unicode identities inferred')


if __name__ == '__main__':
    main()
