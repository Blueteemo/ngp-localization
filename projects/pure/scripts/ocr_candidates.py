"""Local-only Japanese glyph OCR candidates; never a confirmed Unicode map.

Requires a locally installed tesseract and user-provided jpn.traineddata.
Neither the input ROM nor rendered glyphs are transmitted anywhere.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw
from environment import PROJECT
from ngp_localization.glyph12 import unpack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--ids', type=Path, required=True, help='JSON array of explicit original glyph IDs')
    parser.add_argument('--tessdata', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='New private output directory')
    args = parser.parse_args()
    data = args.rom.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != '5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d':
        raise ValueError('Wrong original baseline')
    ids = json.loads(args.ids.read_text())
    if not isinstance(ids, list) or not ids or any(type(i) is not int or i < 0 or (i+1)*18 > 0x10000 for i in ids):
        raise ValueError('Expected a nonempty array of original font-bank glyph IDs')
    ids = sorted(set(ids))
    model_sha = hashlib.sha256((args.tessdata / 'jpn.traineddata').read_bytes()).hexdigest()
    version = subprocess.check_output(['tesseract', '--version'], text=True).splitlines()[0]
    args.out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy(); env['OMP_THREAD_LIMIT'] = '1'
    def recognize(gid):
        bits = unpack(data[0x10000+gid*18:0x10000+(gid+1)*18])
        image = Image.new('L', (96, 96), 255); draw = ImageDraw.Draw(image)
        for y in range(12):
            for x in range(12):
                if bits >> (143-y*12-x) & 1:
                    draw.rectangle((12+x*6,12+y*6,17+x*6,17+y*6), fill=0)
        path = args.out / f'{gid}.png'; image.save(path)
        result = {'glyph_id': gid, 'reviewed': False, 'candidate': '', 'confidence': None}
        try:
            proc = subprocess.run(['tesseract', str(path), 'stdout', '--tessdata-dir', str(args.tessdata),
                                   '-l', 'jpn', '--psm', '10', '-c', 'tessedit_create_tsv=1'], env=env, capture_output=True, text=True, check=True, timeout=20)
            if not proc.stdout.startswith('level\t'):
                raise ValueError('Tesseract did not return TSV')
            words = [r for r in csv.DictReader(io.StringIO(proc.stdout), delimiter='\t') if r.get('text', '').strip()]
            result['candidate'] = ''.join(r['text'].strip() for r in words)
            if words:
                result['confidence'] = min(float(r['conf']) for r in words)
        except (subprocess.SubprocessError, ValueError) as exc:
            result['error'] = type(exc).__name__
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(recognize, ids))
    result = {'kind': 'unreviewed OCR candidates only', 'source_sha256': digest, 'model_sha256': model_sha,
              'engine': version, 'glyph_count': len(ids), 'candidates': results}
    (args.out / 'candidates.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'glyph_count': len(ids), 'nonempty_candidates': sum(bool(x['candidate']) for x in results),
                      'single_character_candidates': sum(len(x['candidate']) == 1 for x in results),
                      'errors': sum('error' in x for x in results), 'reviewed': 0}))


if __name__ == '__main__':
    main()
