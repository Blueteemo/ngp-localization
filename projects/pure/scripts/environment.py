"""All machine-specific paths are provided at runtime, never published."""
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parents[1]
sys.path.insert(0, str(REPOSITORY))
OUTPUT = Path(os.environ.get("PURE_OUTPUT", PROJECT / "private/p05"))
EVIDENCE = OUTPUT / "evidence"
FONT_ROOT = Path(os.environ.get("PURE_FONT_ROOT", PROJECT / "assets"))
BASELINE = Path(os.environ.get("PURE_BASELINE", PROJECT / "private/Memories Off - Pure (Japan).ngc"))
ROM = Path(os.environ.get("PURE_ROM", OUTPUT / "Pure_P05.ngc"))
NATIVE_ROOT = Path(os.environ.get("NGP_NATIVE_ROOT", REPOSITORY / ".deps/NgpCraft_MCP/vendor/emulator"))
BEETLE_CORE = Path(os.environ.get("NGP_BEETLE_CORE", REPOSITORY / ".deps/beetle-ngp-libretro/mednafen_ngp_libretro.so"))
