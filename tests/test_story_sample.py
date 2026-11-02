import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
import json

SCRIPTS = Path(__file__).resolve().parents[1] / 'projects/pure/scripts'
sys.path.insert(0, str(SCRIPTS))
from build_p06 import load_field_suffixes, validate_output_paths
spec = importlib.util.spec_from_file_location('build_story_sample', SCRIPTS / 'build_story_sample.py')
sample = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sample)


class StorySampleTests(unittest.TestCase):
    def test_synthetic_slots_keep_fe_and_jump_back(self):
        slots = {'甲': 0, '乙': 1, '：': 2, '丙': 128, '…': 3}
        encoded = sample.encode_sample(slots, '甲乙：\n丙……丙……')
        self.assertEqual(encoded[:6], bytes([0xFE, 0xF0, 0, 1, 2, 0x81]))
        self.assertIn(bytes([0xF1, 0, 0xF0, 3, 3]), encoded)
        self.assertEqual(encoded[-7:], bytes([0x82, 0x83, 0x80, 0x02, 0x90, 0x33, 0x29]))

    def test_external_sample_layout_is_bounded(self):
        for value in (None, '甲'*13, '\n'.join(['甲']*5)):
            with self.assertRaises(ValueError): sample.encode_sample({'甲':0}, value)

    def test_missing_glyph_is_not_silently_replaced(self):
        with self.assertRaises(KeyError):
            sample.encode_sample({}, '自造文本')


class PrivateConfigTests(unittest.TestCase):
    def test_private_input_cannot_be_overwritten_by_output(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            for config in (out, out/"Pure_P06.ngc", out/"P06_patch.json"):
                with self.assertRaises(ValueError): validate_output_paths(config, out)
            validate_output_paths(out/"private-config.json", out)

    def test_external_config_uses_only_synthetic_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'input.json'
            good = {'field_suffixes': {'0x91958': '甲\n乙', '0x91b2d': '丙\n丁'}}
            p.write_text(json.dumps(good))
            self.assertEqual(load_field_suffixes(p), good['field_suffixes'])
            for bad in ({}, [], {'field_suffixes': {}}, {'field_suffixes': {'0x91958': 1, '0x91b2d': '甲'}}):
                p.write_text(json.dumps(bad))
                with self.assertRaises(ValueError): load_field_suffixes(p)
            p.write_text('{"field_suffixes":{},"field_suffixes":{}}')
            with self.assertRaises(ValueError): load_field_suffixes(p)


if __name__ == '__main__':
    unittest.main()
