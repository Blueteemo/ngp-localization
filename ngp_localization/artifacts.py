"""Publish a complete artifact set without overwriting files or following links.

A fresh/empty directory is replaced by one fully staged directory rename. Existing
nonempty directories are accepted only for byte-identical, no-write rebuilds.
Changed outputs require a new destination, preserving prior builds and saves.
"""
import os
from pathlib import Path
import secrets
import stat


def publish_artifacts(directory, files):
    directory = Path(directory)
    if not files or any(Path(n).name != n or n in ('.', '..') for n in files):
        raise ValueError('Artifacts require simple filenames')
    files = {n: bytes(data) for n, data in files.items()}
    directory.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    parent = os.open(directory.parent, flags)
    stage = '.build-' + secrets.token_hex(12)
    stage_fd = None
    created = False
    try:
        try:
            current = os.open(directory.name, flags, dir_fd=parent)
        except FileNotFoundError:
            current = None
        if current is not None:
            try:
                if os.listdir(current):
                    for name, expected in files.items():
                        fd = os.open(name, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), dir_fd=current)
                        with os.fdopen(fd, 'rb') as stream:
                            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or stream.read() != expected:
                                raise ValueError('Existing artifacts differ; use a new output directory')
                    return  # Never rewrite an existing valid set or its saves.
            finally:
                os.close(current)
        os.mkdir(stage, mode=0o700, dir_fd=parent)
        created = True
        stage_fd = os.open(stage, flags, dir_fd=parent)
        for name, data in files.items():
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600, dir_fd=stage_fd)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        os.fsync(stage_fd)
        # rename cannot replace a file/symlink or a nonempty directory. The parent
        # descriptor pins the actual directory even if its pathname is replaced.
        os.rename(stage, directory.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        if stage_fd is not None:
            os.close(stage_fd)
        try:
            cleanup = os.open(stage, flags, dir_fd=parent) if created else None
        except FileNotFoundError:
            cleanup = None
        if cleanup is not None:
            try:
                for name in os.listdir(cleanup): os.unlink(name, dir_fd=cleanup)
            finally:
                os.close(cleanup)
            os.rmdir(stage, dir_fd=parent)
        os.close(parent)
