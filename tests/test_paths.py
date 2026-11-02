import os
from pathlib import Path
import tempfile
import unittest
from ngp_localization.paths import ensure_distinct_paths


class PathTests(unittest.TestCase):
    def test_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            ensure_distinct_paths([Path(d)/'input'], [Path(d)/'rom',Path(d)/'manifest'])

    def test_same_and_hardlink(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.write_bytes(b'original')
            link=Path(d)/'manifest';os.link(source,link)
            for output in (source,link):
                with self.assertRaises(ValueError):ensure_distinct_paths([source],[output])
            self.assertEqual(source.read_bytes(),b'original')

    def test_output_alias_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source';source.write_bytes(b'original')
            link=Path(d)/'link';link.symlink_to(source)
            with self.assertRaises(ValueError):ensure_distinct_paths([source],[link])
            with self.assertRaises(ValueError):ensure_distinct_paths([], [source,link])


if __name__=='__main__':unittest.main()
