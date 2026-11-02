import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ngp_localization.artifacts import publish_artifacts


class ArtifactTests(unittest.TestCase):
    def test_pair_is_complete_and_repeat_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'build'
            files = {'a.bin': b'abc', 'meta.json': b'{}'}
            publish_artifacts(out, files)
            before = (out/'a.bin').stat().st_mtime_ns
            (out/'save').write_bytes(b'keep')
            publish_artifacts(out, files)
            self.assertEqual((out/'a.bin').stat().st_mtime_ns, before)
            self.assertEqual((out/'save').read_bytes(), b'keep')
            with self.assertRaises(ValueError): publish_artifacts(out, {**files, 'a.bin': b'changed'})
            self.assertEqual((out/'a.bin').read_bytes(), b'abc')

    def test_empty_directory_can_receive_atomic_set(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'empty';out.mkdir()
            publish_artifacts(out, {'one':b'1','two':b'2'})
            self.assertEqual(sorted(p.name for p in out.iterdir()), ['one','two'])

    def test_write_failure_publishes_nothing_and_retry_works(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'build';real=os.fsync
            count=0
            def fail_second(fd):
                nonlocal count
                count+=1
                if count==2: raise OSError('injected disk failure')
                return real(fd)
            with patch('ngp_localization.artifacts.os.fsync', side_effect=fail_second):
                with self.assertRaises(OSError): publish_artifacts(out, {'one':b'1','two':b'2'})
            self.assertFalse(out.exists())
            self.assertEqual(list(Path(d).iterdir()), [])
            publish_artifacts(out, {'one':b'1','two':b'2'})

    def test_symlink_destination_and_symlink_artifact_are_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'target';target.mkdir();(target/'one').write_bytes(b'original')
            out=root/'link';out.symlink_to(target, target_is_directory=True)
            with self.assertRaises(OSError): publish_artifacts(out, {'one':b'new'})
            self.assertEqual((target/'one').read_bytes(), b'original')
            pair=root/'pair';pair.mkdir();(pair/'one').symlink_to(target/'one')
            with self.assertRaises(OSError): publish_artifacts(pair, {'one':b'original'})
            self.assertEqual((target/'one').read_bytes(), b'original')

    def test_destination_replaced_after_check_cannot_overwrite_victim(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'build';victim=root/'victim';victim.write_bytes(b'safe')
            real=os.rename
            def race(src,dst,**kwargs):
                out.symlink_to(victim)
                return real(src,dst,**kwargs)
            with patch('ngp_localization.artifacts.os.rename',side_effect=race):
                with self.assertRaises(OSError):publish_artifacts(out,{'one':b'new','two':b'2'})
            self.assertEqual(victim.read_bytes(),b'safe')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO test')
    def test_existing_fifo_is_rejected_without_waiting_for_a_writer(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'build';out.mkdir();os.mkfifo(out/'one')
            program = "from ngp_localization.artifacts import publish_artifacts; import sys; publish_artifacts(sys.argv[1], {'one':b'expected'})"
            result=subprocess.run([sys.executable, '-c', program, str(out)], capture_output=True, timeout=3)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'Existing artifacts differ',result.stderr)
            self.assertTrue((out/'one').exists())

    def test_names_cannot_escape(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ('../bad','/absolute','.', '..'):
                with self.assertRaises(ValueError):publish_artifacts(Path(d)/'out',{n:b'x'})
