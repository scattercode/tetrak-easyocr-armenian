"""Armenian language support for EasyOCR, as a custom recognition network.

Two lines to use it::

    import tetrak_hy
    reader = tetrak_hy.reader()          # an easyocr.Reader, Armenian-ready
    reader.readtext("scan.png")

This package's import name, ``tetrak_hy``, is also the EasyOCR network
name: EasyOCR resolves ``recog_network="tetrak_hy"`` with
``importlib.import_module``, which finds this installed package, whose
``Model`` attribute (below) is the recognition architecture. That is the
whole loading contract — no architecture file is copied anywhere at
runtime. The remaining two pieces, the network config
(``tetrak_hy.yaml``, shipped as package data) and the trained weights
(``tetrak_hy.pth``, downloaded from this project's GitHub Releases), are
materialised into a cache directory by :func:`reader`.

The model is produced by
`tetrak-hy-trainer <https://github.com/scattercode/tetrak-hy-trainer>`_;
this package ships it. `Tetrak <https://tetrak.dev/>`_ is its first
consumer.
"""

from __future__ import annotations

import hashlib
import shutil
from importlib import resources
from pathlib import Path

# The architecture EasyOCR instantiates: its own generation2 network
# (VGG feature extractor, two BiLSTM layers, CTC head), re-exported so the
# weights are loaded by exactly the class they were trained for. This
# import requires easyocr (and its torch) — which is always present, since
# the only reason to import this package is to use it with EasyOCR.
from easyocr.model.vgg_model import Model  # noqa: F401

NETWORK_NAME = "tetrak_hy"

# Filled in by the first weights release; None means "not yet released".
# Each release updates both together — a URL without its checksum must
# never ship.
WEIGHTS_URL: str | None = None
WEIGHTS_SHA256: str | None = None


class WeightsNotAvailableError(RuntimeError):
    """Raised when no trained weights are released or supplied."""


def cache_dir() -> Path:
    """The directory the network config and weights are materialised into."""
    return Path.home() / ".tetrak_hy"


def _materialise_config(directory: Path) -> Path:
    """Copy the packaged ``tetrak_hy.yaml`` into *directory*."""
    destination = directory / f"{NETWORK_NAME}.yaml"
    if not destination.exists():
        source = resources.files(__package__) / f"{NETWORK_NAME}.yaml"
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def _materialise_weights(directory: Path, weights_path: Path | str | None) -> Path:
    """Place ``tetrak_hy.pth`` in *directory*, from a local file or the release.

    Args:
        directory: The cache directory.
        weights_path: A local ``.pth`` to use instead of the released
            weights — for training runs and pre-release testing.

    Raises:
        WeightsNotAvailableError: No local path was given and no release
            exists yet (or the download failed its checksum).
    """
    destination = directory / f"{NETWORK_NAME}.pth"

    if weights_path is not None:
        shutil.copyfile(weights_path, destination)
        return destination

    if destination.exists():
        return destination

    if WEIGHTS_URL is None or WEIGHTS_SHA256 is None:
        raise WeightsNotAvailableError(
            "No trained tetrak_hy weights have been released yet. "
            "Pass weights_path= to use a local model, or watch "
            "https://github.com/scattercode/tetrak-easyocr-armenian/releases"
        )

    import requests

    response = requests.get(WEIGHTS_URL, timeout=300)
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    if digest != WEIGHTS_SHA256:
        raise WeightsNotAvailableError(
            f"Downloaded weights failed their checksum: expected "
            f"{WEIGHTS_SHA256}, got {digest}. Refusing to install them."
        )
    destination.write_bytes(response.content)
    return destination


def reader(weights_path: Path | str | None = None, **reader_kwargs):
    """Return an ``easyocr.Reader`` configured with the Armenian model.

    Args:
        weights_path: Optional local ``.pth`` overriding the released
            weights.
        **reader_kwargs: Passed through to ``easyocr.Reader`` — ``gpu=``,
            ``verbose=`` and friends.

    Returns:
        A ready ``easyocr.Reader``.

    Raises:
        WeightsNotAvailableError: See :func:`_materialise_weights`.
    """
    import easyocr

    directory = cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    _materialise_config(directory)
    _materialise_weights(directory, weights_path)

    # ["en"], not ["hy"]: EasyOCR reads a per-language character file for
    # every requested language and ships none for Armenian, so ["hy"]
    # raises FileNotFoundError. The file is irrelevant to a custom model —
    # the decode filter is set(model charset) − set(lang_char), and
    # lang_char always includes this model's full character_list, so the
    # filter is empty whichever language is requested. Hidden here so no
    # user ever has to know.
    return easyocr.Reader(
        ["en"],
        recog_network=NETWORK_NAME,
        user_network_directory=str(directory),
        model_storage_directory=str(directory),
        **reader_kwargs,
    )
