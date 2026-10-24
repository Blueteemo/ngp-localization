import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from .patch import apply_file, sha256


def main():
    p = argparse.ArgumentParser(description="NGP localization helpers; see projects/ for game adapters")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor", help="Read-only environment report")
    d.add_argument("--rom", type=Path)
    h = sub.add_parser("hash")
    h.add_argument("file", type=Path)
    a = sub.add_parser("apply", help="Apply a locally generated, guarded manifest")
    a.add_argument("--rom", type=Path, required=True)
    a.add_argument("--manifest", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.command == "hash":
            print(sha256(args.file.read_bytes()))
        elif args.command == "apply":
            print(apply_file(args.rom, args.manifest, args.out))
        else:
            result = {"python": sys.version.split()[0], "python_supported": sys.version_info >= (3,11),
                      "packages": {name: bool(importlib.util.find_spec(name)) for name in ("PIL", "numpy")},
                      "commands": {name: shutil.which(name) for name in ("git", "cmake", "ffmpeg", "ffprobe")},
                      "native_root_configured": bool(os.getenv("NGP_NATIVE_ROOT")),
                      "beetle_core_configured": bool(os.getenv("NGP_BEETLE_CORE")),
                      "note": "Missing optional tools are not proof of emulator readiness; run the selected adapter."}
            if args.rom:
                result["rom"] = {"size": args.rom.stat().st_size, "sha256": sha256(args.rom.read_bytes())}
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as error:
        p.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
