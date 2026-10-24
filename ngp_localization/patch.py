"""Guarded, size-preserving patch application; no commercial patch is bundled."""
import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply(data: bytes, manifest: dict) -> bytes:
    if sha256(data) != manifest["base_sha256"]:
        raise ValueError("Wrong original ROM SHA-256")
    result = bytearray(data)
    for patch in manifest["patches"]:
        offset = patch["offset"]
        before = bytes.fromhex(patch["before"])
        after = bytes.fromhex(patch["after"])
        if not isinstance(offset, int) or offset < 0 or offset + len(before) > len(result):
            raise ValueError("Patch outside ROM bounds")
        if len(before) != len(after) or result[offset:offset+len(before)] != before:
            raise ValueError(f"Patch guard failed at {offset:#x}")
        result[offset:offset+len(after)] = after
    if sha256(result) != manifest["output_sha256"]:
        raise ValueError("Output SHA-256 mismatch")
    return bytes(result)


def apply_file(original: Path, manifest: Path, output: Path) -> str:
    if output.resolve() in (original.resolve(), manifest.resolve()):
        raise ValueError("Refusing to overwrite an input file")
    result = apply(original.read_bytes(), json.loads(manifest.read_text(encoding="utf-8")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)
    return sha256(result)
