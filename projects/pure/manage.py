#!/usr/bin/env python3
"""Portable command entry point for the frozen Pure P05 adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile
import io

PROJECT = Path(__file__).resolve().parent
REPO = PROJECT.parents[1]
BASE_SHA = "5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d"


def fonts(source=None):
    lock = json.loads((PROJECT / "assets/fonts.lock.json").read_text())
    for size, entry in lock.items():
        target = PROJECT / f"assets/fusion{size}" / entry["filename"]
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == entry["sha256"]:
            print(f"{size}px font already verified")
            continue
        if source:
            candidates = [source / f"fusion{size}" / entry["filename"], source / entry["filename"]]
            local = next((p for p in candidates if p.is_file()), None)
            if not local:
                raise ValueError(f"Missing {entry['filename']} under --from-dir")
            data = local.read_bytes()
        else:
            print(f"Downloading pinned Fusion {size}px release", flush=True)
            with urllib.request.urlopen(entry["url"], timeout=90) as response:
                archive = response.read(100 * 1024 * 1024 + 1)
            if hashlib.sha256(archive).hexdigest() != entry["archive_sha256"]:
                raise ValueError("Font release archive SHA-256 mismatch")
            with zipfile.ZipFile(io.BytesIO(archive)) as z:
                matches = [n for n in z.namelist() if Path(n).name == entry["filename"]]
                if len(matches) != 1:
                    raise ValueError("Ambiguous font archive")
                data = z.read(matches[0])
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Font file SHA-256 mismatch; do not update the lock to hide it")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        print(f"{size}px font verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fonts")
    f.add_argument("--from-dir", type=Path)
    for name in ("build", "validate", "menus", "persistence", "signature", "transition", "record", "estimate"):
        q = sub.add_parser(name)
        q.add_argument("--rom", type=Path, required=name in ("build", "estimate"))
        q.add_argument("--out", type=Path, default=PROJECT / "private/p05")
        if name in ("validate", "transition"):
            q.add_argument("--core", choices=("med", "native"), default="med")
        q.add_argument("--native-root", type=Path)
        q.add_argument("--beetle-core", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "fonts":
            fonts(args.from_dir)
            return
        env = os.environ.copy()
        env["PURE_OUTPUT"] = str(args.out.resolve())
        if args.rom:
            if args.command in ("build", "estimate"):
                if hashlib.sha256(args.rom.read_bytes()).hexdigest() != BASE_SHA:
                    raise ValueError("Wrong Japanese baseline SHA-256; no alternative ROM will be guessed")
                env["PURE_BASELINE"] = str(args.rom.resolve())
            else:
                env["PURE_ROM"] = str(args.rom.resolve())
        if args.native_root:
            env["NGP_NATIVE_ROOT"] = str(args.native_root.resolve())
        if args.beetle_core:
            env["NGP_BEETLE_CORE"] = str(args.beetle_core.resolve())
        script = "build_p05.py" if args.command == "build" else args.command + ".py"
        command = [sys.executable, str(PROJECT / "scripts" / script)]
        if args.command in ("validate", "transition"):
            command.append(args.core)
        args.out.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, env=env, check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
