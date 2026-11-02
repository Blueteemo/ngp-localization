"""P06 save/load confirmation regression in three separate OS processes."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from environment import EVIDENCE, ROM, BEETLE_CORE

P = EVIDENCE / 'p06-interactions'
STAGES = ('save', 'load', 'verify')
DEFAULT_STAGE_TIMEOUT = 300.0
EXPECTED_SHA = os.environ.get('PURE_EXPECTED_SHA', '12ac7406dbb255e20c682fa11c001ffa37cc626830f3b0310e2bb02554995fa7')


def stage(name):
    if name not in STAGES:
        raise ValueError('Unknown stage')
    from libretro_frontend import Core
    c = Core(BEETLE_CORE, ROM, P / 'persistent')
    log = []
    def shot(label):
        c.screenshot(P / (label + '.png'))
        value = int.from_bytes(c.memory()[0x256:0x25a], 'little')
        log.append({'name': label, 'script': hex(value), 'frame': c.frames})
        return value
    try:
        c.run(1200); c.press(0, 3, 150); c.press(0, 3, 300)
        if name == 'save':
            shot('title_menu')
            c.press(0, 3, 1200); c.press(0, 3, 600)
            expected = shot('saved_story')
            c.press(3, 3, 500); c.press(0, 3, 500)
            slots = shot('save_slots')
            c.press(0, 3, 500); shot('save_yes')
            c.save_state(P / 'save_confirm.state')
            c.press(5); shot('save_no'); c.press(0, 3, 600)
            assert shot('save_cancelled') == slots
            c.load_state(P / 'save_confirm.state'); c.press(0, 3, 600)
            shot('save_completed')
            (P / 'expected.json').write_text(json.dumps({'saved': expected}), encoding='utf-8')
        else:
            expected = json.loads((P / 'expected.json').read_text(encoding='utf-8'))
            c.press(5); c.press(0, 3, 600)
            slots = shot(name + '_slots')
            c.press(0, 3, 500); shot(name + '_yes')
            if name == 'load':
                c.save_state(P / 'load_confirm.state')
                c.press(5); shot('load_no'); c.press(0, 3, 600)
                assert shot('load_cancelled') == slots
                c.load_state(P / 'load_confirm.state')
            c.press(0, 3, 900)
            loaded = shot(name + '_story')
            assert loaded == expected['saved' if name == 'load' else 'overwritten']
            if name == 'load':
                c.press(0, 3, 300); nextptr = shot('next_page')
                assert nextptr != loaded
                c.press(3, 3, 500); c.press(0, 3, 500); c.press(0, 3, 500)
                shot('overwrite_yes'); c.press(0, 3, 600); shot('overwrite_completed')
                expected['overwritten'] = nextptr
                (P / 'expected.json').write_text(json.dumps(expected), encoding='utf-8')
    finally:
        c.close()
    (P / f'{name}.json').write_text(json.dumps({'pid': os.getpid(), 'log': log}, indent=2), encoding='utf-8')


def run_stages(folder, timeout=DEFAULT_STAGE_TIMEOUT):
    """Bound each fresh process; retain a non-success report on timeout/failure."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Stage timeout must be finite and positive')
    for name in STAGES:
        try:
            # Fixed interpreter/script/stage argv, no shell or user command input.
            subprocess.run([sys.executable, str(Path(__file__).resolve()), name],
                           check=True, shell=False, timeout=timeout)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
            failure = {'status': 'failed', 'stage': name,
                       'reason': 'timeout' if isinstance(error, subprocess.TimeoutExpired) else 'nonzero_exit',
                       'timeout_seconds': timeout,
                       'returncode': getattr(error, 'returncode', None)}
            (folder / 'failure.json').write_text(json.dumps(failure, indent=2), encoding='utf-8')
            raise RuntimeError(f'Regression stage {name} failed: {failure["reason"]}') from error


def main():
    if not __debug__:
        raise RuntimeError("Regression checks require Python without -O")
    before = hashlib.sha256(ROM.read_bytes()).hexdigest()
    if before != EXPECTED_SHA:
        raise ValueError('Regression ROM does not match the expected SHA-256')
    if len(sys.argv) == 2:
        if sys.argv[1] not in STAGES:
            raise ValueError('Unknown stage')
        stage(sys.argv[1])
    elif len(sys.argv) == 1:
        timeout = float(os.environ.get('PURE_STAGE_TIMEOUT', DEFAULT_STAGE_TIMEOUT))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Stage timeout must be finite and positive')
        # Never remove an existing save/evidence directory automatically.
        P.mkdir(parents=True, exist_ok=False)
        run_stages(P, timeout)
        runs = {name: json.loads((P / f'{name}.json').read_text(encoding='utf-8')) for name in STAGES}
        assert len({r['pid'] for r in runs.values()}) == 3
        result = {'rom_sha256': before, 'core_sha256': hashlib.sha256(BEETLE_CORE.read_bytes()).hexdigest(),
                  'separate_os_processes': True, 'positions': json.loads((P / 'expected.json').read_text(encoding='utf-8')),
                  'stages': runs}
        if hashlib.sha256(ROM.read_bytes()).hexdigest() != before:
            raise RuntimeError('ROM changed during regression')
        (P / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k != 'stages'}))
    else:
        raise ValueError('Expected no arguments or one fixed stage name')
    assert hashlib.sha256(ROM.read_bytes()).hexdigest() == before, 'ROM changed during regression'


if __name__ == '__main__':
    main()
