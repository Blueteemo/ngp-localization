"""Keep portable text IO independent of the host's locale encoding."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ExplicitUtf8Tests(unittest.TestCase):
    def test_text_io_declares_utf8_in_portable_tools(self):
        names = ('ngp_localization/textmap.py', 'projects/pure/manage.py',
                 'projects/pure/scripts/interactions.py',
                 'projects/pure/scripts/ocr_candidates.py',
                 'projects/pure/scripts/story_inventory.py')
        count = 0
        for name in names:
            tree = ast.parse((ROOT / name).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr not in ('read_text', 'write_text'):
                    continue
                count += 1
                encoding = next((x.value for x in node.keywords if x.arg == 'encoding'), None)
                self.assertIsInstance(encoding, ast.Constant, f'{name}:{node.lineno}')
                self.assertEqual(encoding.value, 'utf-8', f'{name}:{node.lineno}')
        self.assertGreater(count, 0)


if __name__ == '__main__':
    unittest.main()
