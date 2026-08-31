#!/usr/bin/env python3
"""Fetch the released weights so they can be mirrored on the GitHub Release.

The Hugging Face model repository is canonical for weights (Tetrak decision
003); GitHub Releases mirror them, so a user whose network cannot reach the
Hub still has a way to get the file. This is what puts the copy there.

Reads ``WEIGHTS_URL`` and ``WEIGHTS_SHA256`` out of the package **without
importing it** — importing ``tetrak_hy`` pulls in easyocr and torch, and CI
is deliberately torch-free. The constants are read from the source with
``ast`` instead, which also means a refactor that moves them somewhere this
cannot find is a loud failure rather than a release with a silently empty
mirror.

A release whose ``WEIGHTS_URL`` is ``None`` is a code-only release: nothing
is downloaded and nothing is mirrored, which is not an error.

The download is verified against ``WEIGHTS_SHA256`` before anything is
written, on the same principle the library applies at load time — a file
that fails its checksum is refused, never warned about.

    python3 tools/mirror_weights.py --output-dir mirror
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "tetrak_hy" / "__init__.py"
WEIGHTS_NAME = "tetrak_hy.pth"
TIMEOUT_SECONDS = 300


def read_constant(name: str, source: Path = SOURCE) -> str | None:
    """The value of a module-level string constant, read without importing.

    Raises:
        LookupError: The constant is not a module-level assignment of a
            string or None — which means this tool can no longer find what
            it is supposed to mirror.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in tree.body:
        targets = []
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        elif isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]

        if name not in targets or node.value is None:
            continue
        try:
            value = ast.literal_eval(node.value)
        except ValueError as error:
            raise LookupError(f"{name} in {source} is not a literal: {error}") from error
        if value is not None and not isinstance(value, str):
            raise LookupError(f"{name} in {source} is {type(value).__name__}, not a string")
        return value

    raise LookupError(f"No module-level {name} found in {source}")


def fetch(url: str, expected_sha256: str) -> bytes:
    """Download *url* and return its bytes, or refuse them.

    Raises:
        SystemExit: The download failed, or its digest did not match.
    """
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read()
    except (urllib.error.URLError, OSError) as error:
        raise SystemExit(f"Could not download the weights from {url}: {error}") from error

    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise SystemExit(
            f"Downloaded weights failed their checksum: expected {expected_sha256}, "
            f"got {digest}. Refusing to mirror them."
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "mirror",
        help="where to write the weights and their checksum file",
    )
    args = parser.parse_args(argv)

    url = read_constant("WEIGHTS_URL")
    sha256 = read_constant("WEIGHTS_SHA256")

    if url is None or sha256 is None:
        # Both or neither, enforced by tests/test_package.py.
        print("No weights are pinned in this version — nothing to mirror.")
        return 0

    print(f"Mirroring {url}")
    payload = fetch(url, sha256)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    weights = args.output_dir / WEIGHTS_NAME
    weights.write_bytes(payload)
    # The same format `shasum -c` and `sha256sum -c` both read, so a user who
    # downloads the mirror can verify it with the tools already on their machine.
    (args.output_dir / f"{WEIGHTS_NAME}.sha256").write_text(
        f"{sha256}  {WEIGHTS_NAME}\n", encoding="utf-8"
    )

    print(f"Verified and written: {weights} ({len(payload):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
