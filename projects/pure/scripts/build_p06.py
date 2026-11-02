"""Build P06 with user-supplied private text; no translated prompts are embedded."""
import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory


def load_field_suffixes(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate configuration key')
            result[key] = value
        return result
    value = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
    if not isinstance(value, dict) or set(value) != {'field_suffixes'}:
        raise ValueError('Expected a private field_suffixes object')
    fields = value['field_suffixes']
    if not isinstance(fields, dict) or set(fields) != {'0x91958', '0x91b2d'}:
        raise ValueError('Private P06 configuration must contain exactly its two prompt offsets')
    if any(not isinstance(text, str) for text in fields.values()):
        raise ValueError('Private prompt values must be strings')
    return fields


def validate_output_paths(config, output):
    from ngp_localization.paths import ensure_distinct_paths
    output = Path(output)
    ensure_distinct_paths([config], [output, output / "Pure_P06.ngc", output / "P06_patch.json"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text-config', type=Path, default=os.environ.get('PURE_P06_TEXT_CONFIG'))
    args = parser.parse_args()
    if args.text_config is None:
        parser.error('Supply --text-config or PURE_P06_TEXT_CONFIG; game text stays private')
    from environment import OUTPUT
    validate_output_paths(args.text_config, OUTPUT)
    fields = load_field_suffixes(args.text_config)
    from build_source import build
    with TemporaryDirectory(prefix='pure-p05-seed-') as temporary:
        seed = build('p05', output=temporary)
        build('p06', seed=seed, field_suffixes=fields)


if __name__ == '__main__':
    main()
