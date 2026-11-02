"""Bounded parser for selected FD/FE localization records (stdlib only).

Tokens cover every source byte exactly once. Rendering and unknown_glyph_ids are
derived fields: encode_record ignores them because they carry no source bytes.
"""

import json
import re

_CONTROLS = {
    0x81: 0, 0x82: 0, 0x83: 0, 0x84: 0, 0x85: 0,
    0x86: "expr2", 0x87: "expr2", 0x88: "expr1",
    0x89: 1, 0x8A: 0, 0x8B: 0, 0x8C: "expr1",
}
_ENTRY = (0xFD, 0xFE)
_HEX_KEY = re.compile(r"0[xX][0-9A-Fa-f]+")
_DEC_KEY = re.compile(r"[0-9]+")


def _int(value, name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    return value


def _page(value, name="initial_page"):
    value = _int(value, name)
    if not 0 <= value <= 63:
        raise ValueError(f"{name} must be in 0..63")
    return value


def _check_mapping(mapping):
    if not isinstance(mapping, dict):
        raise ValueError("mapping must be a dict")
    for key, value in mapping.items():
        if not isinstance(key, int) or isinstance(key, bool):
            raise ValueError("mapping keys must be integers")
        if not 0 <= key <= 8191:
            raise ValueError("mapping key out of range")
        if not isinstance(value, str) or not value:
            raise ValueError("mapping values must be nonempty strings")


def _hex(value):
    if not isinstance(value, str):
        raise ValueError("hex must be a string")
    if len(value) % 2:
        raise ValueError("hex must have even length")
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        raise ValueError("invalid hex") from None
    if raw.hex() != value.lower():
        raise ValueError("non-canonical hex")
    return raw


def _argument_end(data, offset):
    """Length of the game's operand at CPU 0x200B65; do not evaluate RAM."""
    if offset >= len(data):
        raise ValueError(f"missing operand at {offset:#x}")
    value = data[offset]
    if not value & 0x40:
        size = (2 if not value & 0x20 else 1 + bool(value & 0x10))
    elif not value & 0x20:
        size = 1 + bool(value & 0x10)
    elif not value & 0x80:
        size = 1
    else:
        size = 3 if value & 0x10 else 2
    end = offset + size
    if end > len(data):
        raise ValueError(f"truncated operand at {offset:#x}")
    return end


def decode_record(data: bytes, *, offset: int, mapping: dict[int, str],
                  initial_page: int = 0) -> dict:
    """Parse one record starting exactly at an FD/FE marker."""
    if not isinstance(data, bytes):
        raise ValueError("data must be bytes")
    offset = _int(offset, "offset")
    if not 0 <= offset < len(data):
        raise ValueError("offset outside data")
    page = _page(initial_page)
    _check_mapping(mapping)
    if data[offset] not in _ENTRY:
        raise ValueError("no FD/FE marker at offset")

    tokens = []
    rendered = []
    unknown = set()
    p = offset
    opcode = data[p]
    tokens.append({"type": "entry", "offset": p,
                   "raw_hex": data[p:p + 1].hex(), "opcode": opcode})
    p += 1

    while True:
        if p >= len(data):
            raise ValueError(f"missing terminator after record at {offset:#x}")
        value = data[p]
        if value == 0x80:
            tokens.append({"type": "end", "offset": p, "raw_hex": "80"})
            p += 1
            break
        if value < 0x80:
            glyph_id = page * 128 + value
            tokens.append({"type": "glyph", "offset": p,
                           "raw_hex": data[p:p + 1].hex(),
                           "glyph_id": glyph_id})
            if glyph_id in mapping:
                rendered.append(mapping[glyph_id])
            else:
                rendered.append(f"[glyph:{glyph_id}]")
                unknown.add(glyph_id)
            p += 1
        elif value >= 0xC0:
            if value in _ENTRY:
                raise ValueError(f"nested entry marker at {p:#x}")
            page = value & 63
            tokens.append({"type": "page", "offset": p,
                           "raw_hex": data[p:p + 1].hex(), "page": page})
            p += 1
        else:
            count = _CONTROLS.get(value)
            if count is None:
                raise ValueError(f"unknown control {value:#04x} at {p:#x}")
            end = p + 1
            if isinstance(count, str):
                for _ in range(int(count[-1])):
                    end = _argument_end(data, end)
            else:
                end += count
            if end > len(data):
                raise ValueError(f"truncated control arguments at {p:#x}")
            raw = data[p:end]
            args = list(raw[1:])
            tokens.append({"type": "control", "offset": p,
                           "raw_hex": raw.hex(), "opcode": value,
                           "args": args})
            if value == 0x81:
                rendered.append("\n")
            p = end

    return {
        "start_offset": offset,
        "end_offset": p,
        "initial_page": initial_page,
        "raw_hex": data[offset:p].hex(),
        "tokens": tokens,
        "rendered_text": "".join(rendered),
        "unknown_glyph_ids": sorted(unknown),
    }


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_mapping(path) -> dict[int, str]:
    """Load a JSON object with decimal or 0x-hex numeric keys."""
    try:
        with open(path, encoding="utf-8") as stream:
            obj = json.load(stream, object_pairs_hook=_no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON mapping") from exc
    if not isinstance(obj, dict):
        raise ValueError("mapping JSON must be an object")

    result = {}
    seen = set()
    for key, value in obj.items():
        if _HEX_KEY.fullmatch(key):
            number = int(key, 16)
        elif _DEC_KEY.fullmatch(key):
            number = int(key, 10)
        else:
            raise ValueError(f"bad mapping key {key!r}")
        if not 0 <= number <= 8191:
            raise ValueError("mapping key out of range")
        if number in seen:
            raise ValueError(f"duplicate numeric key {number}")
        seen.add(number)
        if not isinstance(value, str) or not value:
            raise ValueError("mapping values must be nonempty strings")
        result[number] = value
    return result


def encode_record(export: dict) -> bytes:
    """Rebuild raw bytes after re-parsing and comparing all byte-bearing fields."""
    if not isinstance(export, dict):
        raise ValueError("export must be a dict")
    start = _int(export.get("start_offset"), "start_offset")
    end = _int(export.get("end_offset"), "end_offset")
    if start < 0 or end < 0:
        raise ValueError("offsets must be nonnegative")
    page = _page(export.get("initial_page"))
    raw = _hex(export.get("raw_hex"))
    if end != start + len(raw):
        raise ValueError("end_offset does not match raw length")
    tokens = export.get("tokens")
    if not isinstance(tokens, list):
        raise ValueError("tokens must be a list")

    expected = decode_record(raw, offset=0, mapping={}, initial_page=page)
    if expected["end_offset"] != len(raw):
        raise ValueError("unparsed bytes after record terminator")
    if len(tokens) != len(expected["tokens"]):
        raise ValueError("wrong token count")

    for got, want in zip(tokens, expected["tokens"]):
        if not isinstance(got, dict):
            raise ValueError("token must be a dict")
        if got.get("type") != want["type"]:
            raise ValueError("wrong token type")
        if _int(got.get("offset"), "token offset") != start + want["offset"]:
            raise ValueError("token offset discontinuity")
        if _hex(got.get("raw_hex")) != bytes.fromhex(want["raw_hex"]):
            raise ValueError("token raw_hex mismatch")

        kind = want["type"]
        if kind == "entry":
            if _int(got.get("opcode"), "opcode") != want["opcode"]:
                raise ValueError("entry opcode mismatch")
        elif kind == "page":
            if _int(got.get("page"), "page") != want["page"]:
                raise ValueError("page mismatch")
        elif kind == "glyph":
            if _int(got.get("glyph_id"), "glyph_id") != want["glyph_id"]:
                raise ValueError("glyph mismatch")
        elif kind == "control":
            if _int(got.get("opcode"), "opcode") != want["opcode"]:
                raise ValueError("control opcode mismatch")
            args = got.get("args")
            if not isinstance(args, list) or len(args) != len(want["args"]):
                raise ValueError("control args mismatch")
            for actual, required in zip(args, want["args"]):
                if _int(actual, "arg") != required:
                    raise ValueError("control args mismatch")

    return raw


def main():
    """Export explicitly selected records; never infer reachability by scanning."""
    import argparse
    import hashlib
    from pathlib import Path
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--mapping', type=Path)
    parser.add_argument('--offset', action='append', type=lambda s: int(s, 0), default=[])
    parser.add_argument('--offsets', type=Path, help='JSON array of integer file offsets')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        offsets = list(args.offset)
        if args.offsets:
            extra = json.loads(args.offsets.read_text(encoding='utf-8'))
            if not isinstance(extra, list) or any(type(x) is not int for x in extra):
                raise ValueError('--offsets requires a JSON integer array')
            offsets.extend(extra)
        if not offsets:
            raise ValueError('Select at least one explicit record offset')
        if args.out.resolve() in {p.resolve() for p in (args.rom, args.mapping, args.offsets) if p}:
            raise ValueError('Refusing to overwrite an input')
        data = args.rom.read_bytes()
        mapping = load_mapping(args.mapping) if args.mapping else {}
        records = []
        for offset in dict.fromkeys(offsets):
            record = decode_record(data, offset=offset, mapping=mapping)
            if encode_record(record) != data[offset:record['end_offset']]:
                raise ValueError(f'Roundtrip mismatch at {offset:#x}')
            records.append(record)
        result = {'kind': 'selected records; reachability not established',
                  'source_sha256': hashlib.sha256(data).hexdigest(), 'records': records,
                  'unknown_glyph_ids': sorted({g for r in records for g in r['unknown_glyph_ids']})}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps({'records': len(records), 'unknown_glyphs': len(result['unknown_glyph_ids']),
                          'all_records_byte_roundtrip': True}))
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
