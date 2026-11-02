"""Bounded structural candidates, explicitly not script reachability analysis."""
import argparse
import hashlib
import json
from pathlib import Path
from environment import PROJECT
from ngp_localization.textmap import decode_record, encode_record, load_mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--mapping', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data = args.rom.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != '5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d':
        raise ValueError('Wrong original baseline')
    mapping = load_mapping(args.mapping) if args.mapping else {}
    lo, hi = 0x93365, 0xCA682
    records, rejected = [], []
    p = lo
    while p < hi:
        if data[p] not in (0xFD, 0xFE):
            p += 1
            continue
        try:
            record = decode_record(data[:hi], offset=p, mapping=mapping)
            if encode_record(record) != data[p:record['end_offset']]:
                raise ValueError('Roundtrip mismatch')
        except ValueError as exc:
            rejected.append({'offset':p,'reason':str(exc)}); p += 1
            continue
        records.append(record); p = record['end_offset']
    result = {'kind':'bounded structural candidates, not reachability proof', 'source_sha256':digest,
              'range':[lo,hi], 'records':records, 'rejected':rejected,
              'unknown_glyph_ids':sorted({g for r in records for g in r['unknown_glyph_ids']})}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False)
    print(json.dumps({'records':len(records),'fe':sum(r['tokens'][0]['opcode']==0xFE for r in records),
                      'rejected':len(rejected),'unknown_glyph_ids':len(result['unknown_glyph_ids'])}))


if __name__ == '__main__':main()
