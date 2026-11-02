"""Public build defaults, exercised with synthetic files and a mocked adapter."""
import hashlib
import contextlib
import io
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pure_manage', ROOT / 'projects/pure/manage.py')
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class ManageEntryTests(unittest.TestCase):
    def test_default_build_selects_p06_with_private_config(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            rom = folder / 'synthetic.bin'
            rom.write_bytes(b'synthetic baseline fixture')
            config = folder / 'synthetic.json'
            config.write_text('{}', encoding='utf-8')
            argv = ['manage.py', 'build', '--rom', str(rom), '--text-config', str(config)]
            with patch.object(manage, 'PROJECT', folder), patch.object(manage, 'BASE_SHA', hashlib.sha256(rom.read_bytes()).hexdigest()), patch.object(sys, 'argv', argv), patch.object(manage.subprocess, 'run') as run:
                manage.main()
                self.assertEqual(run.call_args.args[0][-1], str(folder / 'scripts/build_p06.py'))
                env = run.call_args.kwargs['env']
                self.assertEqual(env['PURE_OUTPUT'], str(folder / 'private/p06'))
                self.assertEqual(env['PURE_P06_TEXT_CONFIG'], str(config))

    def test_default_build_requires_config_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            argv = ['manage.py', 'build', '--rom', str(folder / 'absent.bin')]
            with patch.object(manage, 'PROJECT', folder), patch.object(sys, 'argv', argv), patch.object(manage.subprocess, 'run') as run:
                with contextlib.redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as raised:
                    manage.main()
                self.assertIn("P06 requires --text-config", errors.getvalue())
                self.assertEqual(raised.exception.code, 2)
                run.assert_not_called()
                self.assertFalse((folder / 'private').exists())

    def test_historical_p05_remains_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            rom = folder / 'synthetic.bin'
            rom.write_bytes(b'synthetic baseline fixture')
            argv = ['manage.py', 'build', '--version', 'p05', '--rom', str(rom)]
            with patch.object(manage, 'PROJECT', folder), patch.object(manage, 'BASE_SHA', hashlib.sha256(rom.read_bytes()).hexdigest()), patch.object(sys, 'argv', argv), patch.object(manage.subprocess, 'run') as run:
                manage.main()
                self.assertEqual(run.call_args.args[0][-1], str(folder / 'scripts/build_p05.py'))
                self.assertEqual(run.call_args.kwargs['env']['PURE_OUTPUT'], str(folder / 'private/p05'))


if __name__ == '__main__':
    unittest.main()
