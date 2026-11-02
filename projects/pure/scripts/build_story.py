"""Build an explicit translated selection into an experimental 2 MiB Pure ROM.

No ROM is read at import time. This does not establish script reachability,
translate unselected records, or create a release. Output and saves are private.
"""
import argparse
import hashlib
import json
import io
from pathlib import Path
import re

from environment import FONT_ROOT, PROJECT
from ngp_localization.glyph12 import pack
from ngp_localization.paths import ensure_distinct_paths
from ngp_localization.artifacts import publish_artifacts
from ngp_localization.textmap import encode_record

BASE_SHA = '12ac7406dbb255e20c682fa11c001ffa37cc626830f3b0310e2bb02554995fa7'
SOURCE_SHA = '5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d'
BASE_SIZE, ROM_SIZE = 0x100000, 0x200000
TEXT_START, TEXT_LIMIT, FONT_START = 0x100000, 0x170000, 0x180000
HOOK_START, OLD_HOOK_SIZE = 0xD4800, 42
SAVE_START = 0x1F0000
MAX_GLYPHS = 61 * 128  # Pages 0..60; FD and FE are entry markers, not font pages.
ID_PATTERN = re.compile(r'0[xX][0-9a-fA-F]+\Z')
TAG_PATTERN = re.compile(r'\{\{([0-9a-fA-F]+)\}\}')


SAVE_ADDRESSES={
 0x2f8000:[0x124f,0x1366,0x1407,0x1483,0x16d3],
 0x2f9f00:[0x1281,0x1660],
 0x2fa000:[0x12b7,0x139f,0x13bd,0x16b0],
 0x0f8000:[0x12b1,0x1395,0x13c3,0x144d,0x16a4],
 0x0f9f00:[0x13dd,0x1690],
 0x0fa000:[0x13fb,0x1477,0x16c7],
}
SAVE_ERASE_BLOCKS={0x129d:16,0x167f:16,0x13ee:17,0x16ba:17}
def expand_save_layout(source):
 if len(source)!=0x200000:raise ValueError('requires exact 2-MiB input')
 data=bytearray(source);changes=[]
 for old,offsets in SAVE_ADDRESSES.items():
  for at in offsets:
   before=old.to_bytes(4,'little');after=(old+0x100000).to_bytes(4,'little')
   if data[at:at+4]!=before:raise ValueError(f'unexpected source immediate at {at:#x}')
   data[at:at+4]=after;changes.append({'offset':at,'before':before.hex(),'after':after.hex(),'reason':'save address/BIOS relative destination +1 MiB'})
 for at,block in SAVE_ERASE_BLOCKS.items():
  before=bytes([0xc7,0x35,0x03,block]);after=bytes([0xc7,0x35,0x03,block+16])
  if data[at:at+4]!=before:raise ValueError(f'unexpected erase instruction at {at:#x}')
  data[at:at+4]=after;changes.append({'offset':at,'before':before.hex(),'after':after.hex(),'reason':'16-Mbit erase block 32/33'})
 # The final 64 KiB are reserved for the 16-Mbit flash save geometry.
 if set(data[0x1f0000:]) not in ({0},{255},{0,255}):raise ValueError('reserved final64KiB contains non-padding bytes')
 data[0x1f0000:]=b'\xff'*0x10000
 return bytes(data),changes


def offset_value(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and ID_PATTERN.fullmatch(value):
        return int(value, 16)
    raise ValueError('Offsets must be nonnegative integers or 0x hexadecimal strings')


def layout_widths(events, all_controls=False):
    widths = [0]
    for kind, value in events:
        if kind == 'glyph':
            widths[-1] += 1
        elif all_controls or value[0] in (0x81, 0x83):
            widths.append(0)
    return widths


def parse_target(text, record):
    """Keep exact controls and validate normal, positioned or half-width layout."""
    if not isinstance(text, str):
        raise ValueError('Translation text must be a string')
    source_events = [('control', bytes.fromhex(t['raw_hex'])) if t['type'] == 'control'
                     else ('glyph', t['glyph_id']) for t in record['tokens']
                     if t['type'] in ('control', 'glyph')]
    expected = [value for kind, value in source_events if kind == 'control']
    events = []
    pos = 0
    while pos < len(text):
        char = text[pos]
        if char in '{}':
            match = TAG_PATTERN.match(text, pos)
            if not match or len(match.group(1)) % 2:
                raise ValueError('Malformed {{hex}} control tag')
            raw = bytes.fromhex(match.group(1))
            if raw == b'\x81':
                raise ValueError('Source 81 controls must be represented as newlines')
            events.append(('control', raw))
            pos = match.end()
        elif char == '\n':
            events.append(('control', b'\x81'))
            pos += 1
        else:
            if (char not in (' ', '\u3000') and not char.isprintable()) or 0xD800 <= ord(char) <= 0xDFFF:
                raise ValueError('Unsupported nonprinting translation character')
            events.append(('glyph', char))
            pos += 1
    if [value for kind, value in events if kind == 'control'] != expected:
        raise ValueError('Translation controls/newlines differ from source order/arguments')
    positioned = any(raw[0] == 0x87 for raw in expected)
    half_width = any(raw[0] == 0x8B for raw in expected)
    source_widths = layout_widths(source_events, all_controls=positioned)
    widths = layout_widths(events, all_controls=positioned)
    limits = source_widths if positioned else [max(12, n) if half_width else 12 for n in source_widths]
    if len(widths) != len(limits) or any(n > limit for n, limit in zip(widths, limits)):
        raise ValueError('Translation exceeds source-positioned or visible line width limits')
    if half_width:
        previous_glyph = None
        for kind, value in events:
            if kind == 'glyph':
                previous_glyph = value
            elif value[0] in (0x81, 0x83, 0x87):
                previous_glyph = None
            elif value == b'\x8b' and previous_glyph is not None:
                if not (0x20 <= ord(previous_glyph) <= 0x7e or previous_glyph in '「」'):
                    raise ValueError('8B cursor compression requires a narrow ASCII/bracket glyph')
    if half_width and not positioned:
        # 8B is a cursor adjustment, not permission to pack arbitrary CJK.
        # Only unchanged, mapped source ASCII/bracket lines may exceed 12 cells.
        source_lines = record.get('rendered_text', '').split('\n')
        target_lines = [[]]
        for kind, value in events:
            if kind == 'glyph':
                target_lines[-1].append(value)
            elif value[0] in (0x81, 0x83):
                target_lines.append([])
        for index, line in enumerate(target_lines):
            if len(line) <= 12:
                continue
            visible = ''.join(line)
            if (index >= len(source_lines) or visible != source_lines[index]
                    or any(not (0x20 <= ord(c) <= 0x7e or c in '「」') for c in visible)):
                raise ValueError('Long 8B lines require unchanged mapped source ASCII/brackets')
    mode = 'positioned_source_segments'  if positioned else 'source_half_width_lines' if half_width else '12_glyph_lines'
    return events, {'mode': mode, 'widths': widths, 'limits': limits,
                    'validation_scope': 'structural constraints only; raster overlap requires visual verification',
                    'source_widths': source_widths,
                    'ascii_sequence_validation': 'unchanged_long_ascii_lines' if half_width and not positioned else 'not_applicable'}


def prepare_plan(base, inventory, translations, selection):
    """Reject missing, extra, duplicate, overlapping or stale selected records."""
    if not isinstance(inventory, dict) or inventory.get('source_sha256') != SOURCE_SHA:
        raise ValueError('Inventory must identify the exact original Japanese source')
    records = inventory.get('records')
    if not isinstance(records, list) or not isinstance(translations, list) or not isinstance(selection, list):
        raise ValueError('Inventory records, translations and selection must be arrays')
    selected = [offset_value(value) for value in selection]
    if not selected or len(selected) != len(set(selected)):
        raise ValueError('Selection must be nonempty and contain no duplicate offsets')
    candidates = {}
    for record in records:
        if not isinstance(record, dict) or type(record.get('start_offset')) is not int:
            raise ValueError('Malformed inventory record')
        start = record['start_offset']
        if start in candidates:
            raise ValueError('Duplicate inventory offset')
        candidates[start] = record
    translated = {}
    for item in translations:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not ID_PATTERN.fullmatch(item['id']):
            raise ValueError('Translation ID must be a 0x hexadecimal string')
        start = offset_value(item['id'])
        if start in translated:
            raise ValueError('Duplicate translation ID')
        translated[start] = item.get('text')
    if set(translated) != set(selected):
        raise ValueError('Translation IDs must exactly equal selection; no missing/extra IDs')
    plans = []
    previous_end = -1
    for start in sorted(selected):
        if start not in candidates:
            raise ValueError(f'Selected offset {start:#x} is not an inventory candidate')
        record = candidates[start]
        raw = encode_record(record)
        end = record['end_offset']
        if len(raw) < 4 or start < 0 or end > len(base):
            raise ValueError('Selected record is too short or outside the source ROM')
        if start < previous_end:
            raise ValueError('Selected source records overlap')
        if base[start:end] != raw:
            raise ValueError(f'Source bytes no longer match P06 at {start:#x}')
        events, checks = parse_target(translated[start], record)
        plans.append({'start': start, 'end': end, 'raw': raw,
                      'entry': raw[0], 'events': events, 'line_widths': checks['widths'], 'layout_checks': checks})
        previous_end = end
    return plans


def collect_characters(plans):
    chars = sorted({value for plan in plans for kind, value in plan['events'] if kind == 'glyph'})
    if len(chars) > MAX_GLYPHS:
        raise ValueError('Too many glyphs: pages beyond 60 would collide with entry markers')
    return chars


def encode_target(plan, slots):
    output = bytearray([plan['entry']])
    page = None
    for kind, value in plan['events']:
        if kind == 'control':
            output.extend(value)
            page = None  # Controls may change interpreter state; always reselect.
        elif kind == 'glyph':
            slot = slots[value]
            if type(slot) is not int or not 0 <= slot < MAX_GLYPHS:
                raise ValueError('Glyph slot exceeds safe page range')
            wanted = slot // 128
            if wanted != page:
                output.append(0xC0 | wanted)
                page = wanted
            output.append(slot % 128)
        else:
            raise ValueError('Unknown target event')
    output.append(0x80)
    output.extend(b'\x02' + (0x200000 + plan['end']).to_bytes(3, 'little'))
    return bytes(output)


def expansion_hook(old):
    if len(old) != OLD_HOOK_SIZE or not old.startswith(b'\xa7\x24') or not old.endswith(bytes.fromhex('44000021001b0f1c20')):
        raise ValueError('Unexpected P06 font-selector hook')
    hook = bytearray.fromhex('a7 24 ec cf 00 00 30 00')
    low = len(hook); hook.extend(b'\x67\0')
    hook.extend(bytes.fromhex('ec cf 00 00 37 00'))
    high = len(hook); hook.extend(b'\x6f\0')
    hook.extend(bytes.fromhex('44 00 00 38 00 1b 0f 1c 20'))
    for jump in (low, high):
        hook[jump+1] = len(hook) - jump - 2
    hook.extend(old[2:])
    if len(hook) != 67:
        raise ValueError('Unexpected expanded hook size')
    return bytes(hook)


def render_glyphs(chars, font_data):
    # Pillow is intentionally absent from module imports and ROM-free tests.
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(io.BytesIO(font_data), 12)
    def bitmap(char):
        image = Image.new('L', (12, 12))
        ImageDraw.Draw(image).text((0, 10), char, font=font, anchor='ls', fill=255)
        return sum(1 << (143-y*12-x) for y in range(12) for x in range(12)
                   if image.getpixel((x, y)) >= 128)
    missing = bitmap('\U0010ffff')
    packed = []
    for char in chars:
        bits = 0 if char in (' ', '\u3000') else bitmap(char)
        if char not in (' ', '\u3000') and (not bits or bits == missing):
            raise ValueError(f'Missing or tofu glyph: U+{ord(char):04X}')
        packed.append(pack(bits))
    return b''.join(packed)


def changed_ranges(before, after):
    ranges = []
    start = None
    for pos, (a, b) in enumerate(zip(before, after)):
        if a != b and start is None:
            start = pos
        elif a == b and start is not None:
            ranges.append({'start': start, 'end': pos, 'kind': 'modified'})
            start = None
    if start is not None:
        ranges.append({'start': start, 'end': len(before), 'kind': 'modified'})
    if len(after) > len(before):
        ranges.append({'start': len(before), 'end': len(after), 'kind': 'added'})
    return ranges


def build_image(base, plans, chars, glyph_data):
    """Pure assembly helper; CLI authenticates P06 before invoking this function."""
    if len(base) != BASE_SIZE or len(glyph_data) != len(chars) * 18:
        raise ValueError('Incorrect ROM or glyph-bank length')
    if chars != collect_characters(plans):
        raise ValueError('Glyph order must be the sorted selected character set')
    if FONT_START + len(glyph_data) > SAVE_START:
        raise ValueError('Font bank overlaps reserved flash save blocks')
    slots = {char: slot for slot, char in enumerate(chars)}
    payloads, rows, cursor = [], [], TEXT_START
    for plan in plans:
        payload = encode_target(plan, slots)
        if cursor + len(payload) >= TEXT_LIMIT:
            raise ValueError('Translated text reaches the reserved text limit')
        payloads.append((plan, cursor, payload))
        rows.append({'original_offset': plan['start'], 'original_end': plan['end'],
                     'new_offset': cursor, 'new_end': cursor + len(payload),
                     'entry': plan['entry'], 'line_widths': plan['line_widths'], 'layout_checks': plan['layout_checks']})
        cursor += len(payload)
    old = base[HOOK_START:HOOK_START+OLD_HOOK_SIZE]
    hook = expansion_hook(old)
    if any(base[HOOK_START+OLD_HOOK_SIZE:HOOK_START+len(hook)]):
        raise ValueError('Expanded hook would overwrite existing P06 data')
    for plan in plans:
        if plan['start'] < HOOK_START+len(hook) and plan['end'] > HOOK_START:
            raise ValueError('Selected script overlaps the font selector hook')
    output = bytearray(base) + bytearray(ROM_SIZE - len(base))
    for plan, at, payload in payloads:
        output[at:at+len(payload)] = payload
        output[plan['start']:plan['start']+4] = b'\x02' + (0x200000+at).to_bytes(3, 'little')
    output[FONT_START:FONT_START+len(glyph_data)] = glyph_data
    output[HOOK_START:HOOK_START+len(hook)] = hook
    output, save_changes = expand_save_layout(bytes(output))
    return output, {'save_layout': {'capacity_bytes': ROM_SIZE, 'reserved_range': [SAVE_START, ROM_SIZE], 'erase_blocks': [32, 33], 'patches': save_changes}, 'record_count': len(rows), 'records': rows, 'glyph_count': len(chars),
                           'text_end': cursor, 'font_end': FONT_START+len(glyph_data),
                           'line_checks_passed': True, 'changed_ranges': changed_ranges(base, output)}


def parse_json_bytes(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique)


def read_json(path):
    return parse_json_bytes(path.read_bytes())


def read_input_set(path, paths):
    """A producer publishes this small hash manifest only after all inputs exist.

    Consumers pin its bytes once; mixed generations fail closed instead of
    attempting to infer consistency from independent mtime checks or file locks.
    """
    raw = path.read_bytes()
    expected = parse_json_bytes(raw)
    names = ('inventory', 'translations', 'selection')
    if not isinstance(expected, dict) or set(expected) != set(names):
        raise ValueError('Input set must contain exactly inventory/translations/selection SHA256')
    for value in expected.values():
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('Invalid input-set SHA256')
    snapshots = {name: paths[name].read_bytes() for name in names}
    if any(hashlib.sha256(snapshots[name]).hexdigest() != expected[name] for name in names):
        raise ValueError('Input generation differs from pinned input-set manifest')
    return snapshots, hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'inventory', 'translations', 'selection', 'input-set', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    try:
        lock_path = PROJECT / 'assets/fonts.lock.json'
        lock = read_json(lock_path)['12']
        font_path = FONT_ROOT / 'fusion12' / lock['filename']
        inputs = [args.rom, args.inventory, args.translations, args.selection, args.input_set, lock_path, font_path]
        outputs = [args.out / 'Pure_story.ngc', args.out / 'story_manifest.json']
        ensure_distinct_paths(inputs, [args.out, *outputs])
        if args.out.exists():
            raise ValueError('Output directory must be new; never reuse release or player-save directories')
        base = args.rom.read_bytes()
        if len(base) != BASE_SIZE or hashlib.sha256(base).hexdigest() != BASE_SHA:
            raise ValueError('Expected the exact frozen P06 ROM')
        font_data = font_path.read_bytes()
        font_hash = hashlib.sha256(font_data).hexdigest()
        if font_hash != lock['sha256']:
            raise ValueError('Pinned Fusion 12px font hash does not match')
        snapshots, input_set_hash = read_input_set(args.input_set, {name: getattr(args, name) for name in ('inventory', 'translations', 'selection')})
        plans = prepare_plan(base, *(parse_json_bytes(snapshots[name]) for name in ('inventory', 'translations', 'selection')))
        chars = collect_characters(plans)
        data, manifest = build_image(base, plans, chars, render_glyphs(chars, font_data))
        manifest.update({'kind': 'experimental explicit selection, not a release',
                         'scope': 'Selection only; no claim of full-script reachability or full translation',
                         'save_compatibility': 'Use new private saves for this output only',
                         'source_sha256': SOURCE_SHA, 'base_sha256': BASE_SHA,
                         'output_sha256': hashlib.sha256(data).hexdigest(), 'rom_size': len(data),
                         'font_sha256': font_hash,
                         'input_set_sha256': input_set_hash,
                         'inventory_sha256': hashlib.sha256(snapshots['inventory']).hexdigest(),
                         'translations_sha256': hashlib.sha256(snapshots['translations']).hexdigest(),
                         'selection_sha256': hashlib.sha256(snapshots['selection']).hexdigest(),
                         'glyph_characters': chars})
        publish_artifacts(args.out, {
            'Pure_story.ngc': bytes(data),
            'story_manifest.json': (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8'),
        })
        print(json.dumps({key:manifest[key] for key in ('kind','record_count','glyph_count','output_sha256')}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
