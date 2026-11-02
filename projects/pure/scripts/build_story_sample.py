"""One controlled FE story relocation, not a full-story translator.

Uses the frozen P06 font bank and preserves FE entry semantics. The original
record is redirected to a new FE record, which returns to the next original
record. Saves made inside this experiment are not compatible with stock P06.
"""
import hashlib
import io
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


def verified_slots(original, manifest, text, charbits):
    """Bind requested characters to actual frozen ROM bitmaps, not JSON labels."""
    from ngp_localization.glyph12 import pack
    glyphs = manifest.get('glyphs')
    if not isinstance(glyphs, list): raise ValueError('Missing allocation glyphs')
    slots = {}
    seen = set()
    for glyph in glyphs:
        slot = glyph['slot']
        if type(slot) is not int or not 0 <= slot < 1000 or slot in seen:
            raise ValueError('Invalid or duplicate glyph slot')
        seen.add(slot)
        offset = 0xD3000 + slot * 18
        actual = bytes(original[offset:offset+18])
        if len(actual) != 18 or bytes.fromhex(glyph['packed']) != actual:
            raise ValueError('Allocation bitmap differs from frozen ROM')
        slots.setdefault(actual, slot)
    result = {}
    for char in set(text) - {'\n'}:
        bitmap = pack(charbits(char))
        if bitmap not in slots:
            raise ValueError('Sample character has no verified glyph in frozen ROM')
        result[char] = slots[bitmap]
    return result


def public_summary(summary):
    return {key: value for key, value in summary.items() if key != 'text'}


def main():
    original = ROM.read_bytes()
    if hashlib.sha256(original).hexdigest() != P06_SHA:
        raise ValueError('Requires the frozen P06 source-build output')
    manifest = json.loads((ROM.parent / 'P06_patch.json').read_text(encoding='utf-8'))
    if manifest['output_sha256'] != P06_SHA:
        raise ValueError('P06 allocation manifest does not match')
    if manifest['relocated_text_end'] > TARGET:
        raise ValueError('Sample region overlaps P06 assets')
    text_file = os.environ.get('PURE_SAMPLE_TEXT_FILE')
    if not text_file:
        raise ValueError('Supply PURE_SAMPLE_TEXT_FILE; no game dialogue is embedded')
    text_path = Path(text_file)
    text = text_path.read_text(encoding='utf-8')
    from build_source import make_charbits
    from environment import PROJECT, FONT_ROOT
    from PIL import ImageFont
    lock = json.loads((PROJECT / 'assets/fonts.lock.json').read_text(encoding='utf-8'))['12']
    font_data = (FONT_ROOT / 'fusion12' / lock['filename']).read_bytes()
    if hashlib.sha256(font_data).hexdigest() != lock['sha256']:
        raise ValueError('Sample requires the pinned font')
    font = ImageFont.truetype(io.BytesIO(font_data), 12)
    donor_data = json.loads((PROJECT / 'assets/menu_glyphs.json').read_text(encoding='utf-8'))
    donors = {g['character']: int(g['bitmap'], 16) for g in donor_data['glyphs']}
    slots = verified_slots(original, manifest, text, make_charbits(original, font, donors))
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
    summary = {'base_sha256': P06_SHA, 'output_sha256': digest, 'translated_records': 1,
               'original_offset': START, 'original_end': END, 'relocated_offset': TARGET,
               'text': text, 'save_compatibility': 'experimental output only; do not use P06 player saves'}
    from ngp_localization.artifacts import publish_artifacts
    publish_artifacts(OUTPUT, {out.name: data, summary_path.name: json.dumps(summary, ensure_ascii=False, indent=2).encode('utf-8')})
    print(json.dumps(public_summary(summary), ensure_ascii=False))


if __name__ == '__main__':
    main()
