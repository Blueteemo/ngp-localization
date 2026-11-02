"""One controlled FE story relocation, not a full-story translator.

Uses the frozen P06 font bank and preserves FE entry semantics. The original
record is redirected to a new FE record, which returns to the next original
record. Saves made inside this experiment are not compatible with stock P06.
"""
import hashlib
import json
import os
from pathlib import Path
from environment import ROM, OUTPUT
from ngp_localization.paths import ensure_distinct_paths

P06_SHA = '12ac7406dbb255e20c682fa11c001ffa37cc626830f3b0310e2bb02554995fa7'
START, END, TARGET = 0x93377, 0x93390, 0xD2700


def encode_sample(slots, text):
    out = bytearray([0xFE])
    page = None
    if not isinstance(text, str) or not 1 <= len(text.split('\n')) <= 4:
        raise ValueError('Sample requires one to four text lines')
    for line in text.split('\n'):
        if len(line) > 12:
            raise ValueError('Sample exceeds dialogue line width')
    for char in text:
        if char == '\n':
            out.append(0x81); page = None
            continue
        slot = slots[char]
        glyph_page = 48 + slot // 128
        if glyph_page != page:
            out.append(0xC0 | glyph_page); page = glyph_page
        out.append(slot % 128)
    out += bytes([0x82, 0x83, 0x80, 0x02]) + (0x200000 + END).to_bytes(3, 'little')
    return bytes(out)


def main():
    original = ROM.read_bytes()
    if hashlib.sha256(original).hexdigest() != P06_SHA:
        raise ValueError('Requires the frozen P06 source-build output')
    manifest = json.loads((ROM.parent / 'P06_patch.json').read_text())
    if manifest['output_sha256'] != P06_SHA:
        raise ValueError('P06 allocation manifest does not match')
    if manifest['relocated_text_end'] > TARGET:
        raise ValueError('Sample region overlaps P06 assets')
    slots = {g['label']: g['slot'] for g in manifest['glyphs']}
    text_file = os.environ.get('PURE_SAMPLE_TEXT_FILE')
    if not text_file:
        raise ValueError('Supply PURE_SAMPLE_TEXT_FILE; no game dialogue is embedded')
    text_path = Path(text_file)
    text = text_path.read_text(encoding='utf-8')
    payload = encode_sample(slots, text)
    if TARGET + len(payload) >= 0xD3000 or any(original[TARGET:TARGET+len(payload)]):
        raise ValueError('Sample region is not the verified unused P06 gap')
    if original[START] != 0xFE or original[END-3:END] != bytes([0x82, 0x83, 0x80]):
        raise ValueError('Unexpected original FE record boundary')
    data = bytearray(original)
    data[TARGET:TARGET+len(payload)] = payload
    data[START:START+4] = bytes([0x02]) + (0x200000+TARGET).to_bytes(3, 'little')
    digest = hashlib.sha256(data).hexdigest()
    expected = os.environ.get('PURE_EXPECTED_SAMPLE_SHA')
    if expected and digest != expected:
        raise ValueError('Sample differs from the caller-supplied expected hash')
    out = OUTPUT / 'Pure_story_sample.ngc'
    ensure_distinct_paths([ROM, ROM.parent / 'P06_patch.json', text_path], [out, OUTPUT / 'story_sample.json'])
    summary_path = OUTPUT / 'story_sample.json'
    if out.exists() or summary_path.exists():
        raise ValueError('Use a new output location; do not replace an experiment or its saves')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with out.open('xb') as stream:
        stream.write(data)
    summary = {'base_sha256': P06_SHA, 'output_sha256': digest, 'translated_records': 1,
               'original_offset': START, 'original_end': END, 'relocated_offset': TARGET,
               'text': text, 'save_compatibility': 'experimental output only; do not use P06 player saves'}
    with summary_path.open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
