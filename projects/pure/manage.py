#!/usr/bin/env python3
"""P06 build entry point; historical adapters remain for regression."""
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
    lock = json.loads((PROJECT / "assets/fonts.lock.json").read_text(encoding='utf-8'))
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
    for name in ("build", "validate", "menus", "persistence", "signature", "transition", "record", "estimate", "interactions", "story-sample"):
        q = sub.add_parser(name)
        q.add_argument("--rom", type=Path, required=name in ("build", "estimate", "story-sample"))
        q.add_argument("--out", type=Path)
        if name == "build":
            q.add_argument("--version", choices=("p05", "p06"), default="p06", help="P06 by default; P05 is retained for historical regression")
            q.add_argument("--text-config", type=Path)
        if name == "story-sample":
            q.add_argument("--text-file", type=Path, required=True)
        if name in ("validate", "transition"):
            q.add_argument("--core", choices=("med", "native"), default="med")
        q.add_argument("--native-root", type=Path)
        q.add_argument("--beetle-core", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "fonts":
            fonts(args.from_dir)
            return
        version = getattr(args, "version", "story-sample" if args.command == "story-sample" else "p06" if args.command == "interactions" else "p05")
        args.out = args.out or PROJECT / f"private/{version}"
        env = os.environ.copy()
        env["PURE_OUTPUT"] = str(args.out.resolve())
        if args.command == "build" and version == "p06":
            if args.text_config is None:
                raise ValueError("P06 requires --text-config with private prompt data")
            env["PURE_P06_TEXT_CONFIG"] = str(args.text_config.resolve())
        elif args.command == "build" and args.text_config is not None:
            raise ValueError("--text-config is only used by P06")
        if args.command == "story-sample":
            env["PURE_SAMPLE_TEXT_FILE"] = str(args.text_file.resolve())
        if args.command == "interactions" and not args.rom:
            env["PURE_ROM"] = str((args.out / "Pure_P06.ngc").resolve())
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
        script = f"build_{version}.py" if args.command == "build" else "build_story_sample.py" if args.command == "story-sample" else args.command + ".py"
        command = [sys.executable, str(PROJECT / "scripts" / script)]
        if args.command in ("validate", "transition"):
            command.append(args.core)
        args.out.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, env=env, check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
