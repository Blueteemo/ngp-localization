"""Synthetic process-control tests: no ROM, emulator, or third-party imports."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'projects/pure/scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('pure_interactions', SCRIPTS / 'interactions.py')
interactions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(interactions)


class InteractionProcessTests(unittest.TestCase):
    def test_fixed_stages_have_timeout_and_no_shell(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(interactions.subprocess, 'run') as run:
            interactions.run_stages(Path(directory), 17)
            self.assertEqual(run.call_count, 3)
            for call, stage in zip(run.call_args_list, interactions.STAGES):
                self.assertEqual(call.args[0], [sys.executable, str(SCRIPTS / 'interactions.py'), stage])
                self.assertEqual(call.kwargs, {'check': True, 'shell': False, 'timeout': 17})
            self.assertFalse((Path(directory) / 'failure.json').exists())

    def test_timeout_records_failure_and_stops_later_stages(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(interactions.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['synthetic'], 1)) as run:
            folder = Path(directory)
            with self.assertRaisesRegex(RuntimeError, 'save failed: timeout'):
                interactions.run_stages(folder, 1)
            self.assertEqual(run.call_count, 1)
            result = json.loads((folder / 'failure.json').read_text(encoding='utf-8'))
            self.assertEqual((result['status'], result['stage'], result['reason']), ('failed', 'save', 'timeout'))
            self.assertFalse((folder / 'result.json').exists())

    def test_nonzero_exit_does_not_continue(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(interactions.subprocess, 'run', side_effect=subprocess.CalledProcessError(9, ['synthetic'])) as run:
            with self.assertRaisesRegex(RuntimeError, 'nonzero_exit'):
                interactions.run_stages(Path(directory))
            self.assertEqual(run.call_count, 1)
            result = json.loads((Path(directory) / 'failure.json').read_text(encoding='utf-8'))
            self.assertEqual(result['returncode'], 9)

    def test_invalid_timeout_and_stage_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(interactions.subprocess, 'run') as run:
            for timeout in (0, -1, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    interactions.run_stages(Path(directory), timeout)
            with self.assertRaises(ValueError):
                interactions.stage('save; arbitrary command')
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
