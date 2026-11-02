"""Protect inputs and sibling outputs from path, symlink and hardlink aliases."""
from pathlib import Path


def ensure_distinct_paths(inputs, outputs):
    known = [Path(p) for p in inputs]
    for output in map(Path, outputs):
        for other in known:
            same = output.resolve() == other.resolve()
            if not same and output.exists() and other.exists():
                same = output.samefile(other)
            if same:
                raise ValueError(f'Refusing aliased input/output paths: {output} and {other}')
        known.append(output)
