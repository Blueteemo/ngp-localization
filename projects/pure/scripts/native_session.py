"""Thin runtime adapter around the separately obtained, pinned NgpCraft core."""
import sys
from pathlib import Path
from environment import NATIVE_ROOT, BASELINE


def _runtime():
    if not (NATIVE_ROOT / "core/native.py").is_file():
        raise RuntimeError("Missing NgpCraft checkout; see docs/environment.md or pass --native-root")
    sys.path.insert(0, str(NATIVE_ROOT))
    from core import native
    from ngpc_native import write_png as write
    return native, write


def machine(rom=BASELINE):
    native, _ = _runtime()
    bios = NATIVE_ROOT / "hle_bios/bios_hle.bin"
    if not bios.is_file():
        raise RuntimeError("Pinned project HLE BIOS is missing; do not substitute or download a real BIOS")
    m = native.NativeMachine(Path(rom).read_bytes(), bios=bios.read_bytes())
    m.set_timing_silicon(10, 8)
    m.reset()
    return m


def run(m, n, keys=0):
    result = None
    for _ in range(n):
        m.write(0xb0, bytes([keys]))
        result = m.run_frames(1)
        m.audio()
        if result.stop_status not in (0, 1, 41):
            raise RuntimeError((hex(m.cpu().pc), result.stop_status))
    return result


def press(m, key, n=3, after=60):
    run(m, n, key)
    run(m, after)


def write_png(m, path):
    _, write = _runtime()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    write(m, Path(path))
