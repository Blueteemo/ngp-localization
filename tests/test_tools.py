import hashlib
import random
import tempfile
import unittest
from pathlib import Path
from ngp_localization.glyph12 import pack,unpack
from ngp_localization.patch import apply,apply_file


class GlyphTests(unittest.TestCase):
    def test_known_pixel_mapping(self):
        self.assertEqual(pack(1<<143), b'\x80'+bytes(17))
        self.assertEqual(pack(1<<139), b'\x40'+bytes(17))
        self.assertEqual(unpack(bytes([128])+bytes(17)),1<<143)

    def test_all_single_pixels(self):
        for bit in range(144):
            self.assertEqual(unpack(pack(1<<bit)),1<<bit)

    def test_random_roundtrip(self):
        rng=random.Random(20261024)
        for _ in range(100):
            raw=rng.randbytes(18)
            self.assertEqual(pack(unpack(raw)),raw)

    def test_bad_inputs(self):
        for x in (-1,1<<144):
            with self.assertRaises(ValueError):pack(x)
        with self.assertRaises(ValueError):unpack(bytes(17))


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.manifest={'base_sha256':hashlib.sha256(b'hello').hexdigest(),'output_sha256':hashlib.sha256(b'hallo').hexdigest(),'patches':[{'offset':1,'before':'65','after':'61'}]}

    def test_apply(self):self.assertEqual(apply(b'hello',self.manifest),b'hallo')

    def test_wrong_baseline(self):
        with self.assertRaises(ValueError):apply(b'other',self.manifest)

    def test_out_of_bounds(self):
        self.manifest['patches'][0]['offset']=-1
        with self.assertRaises(ValueError):apply(b'hello',self.manifest)

    def test_output_hash(self):
        self.manifest['output_sha256']='0'*64
        with self.assertRaises(ValueError):apply(b'hello',self.manifest)

    def test_refuse_input_overwrite(self):
        with tempfile.TemporaryDirectory()as d:
            rom=Path(d)/'original';rom.write_bytes(b'hello')
            with self.assertRaises(ValueError):apply_file(rom,Path(d)/'unused.json',rom)
            self.assertEqual(rom.read_bytes(),b'hello')


if __name__=='__main__':unittest.main()
