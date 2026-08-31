"""Armenian language support for EasyOCR, as a custom recognition network.

Two lines to use it::

    import tetrak_hy
    reader = tetrak_hy.reader()          # an easyocr.Reader, Armenian-ready
    reader.readtext("scan.png")

:func:`fold_script` folds a recognised string's cross-script homoglyphs
(Latin ``h`` for ``հ``, a colon for ``։``, en/em dash for a hyphen) onto
their Armenian form -- worth applying to every recognised string, since it
recovers word recall the CTC head's lack of a language model otherwise
costs. See its own docstring for what it does and does not fold, and why::

    text = tetrak_hy.fold_script(text)

This package's import name, ``tetrak_hy``, is also the EasyOCR network
name: EasyOCR resolves ``recog_network="tetrak_hy"`` with
``importlib.import_module``, which finds this installed package, whose
``Model`` attribute (below) is the recognition architecture. That is the
whole loading contract — no architecture file is copied anywhere at
runtime. The remaining two pieces, the network config
(``tetrak_hy.yaml``, shipped as package data) and the trained weights
(``tetrak_hy.pth``, downloaded from the project's Hugging Face model
repository), are materialised by :func:`reader` into a cache directory
— ``~/.tetrak_hy`` by default, or wherever ``TETRAK_HY_HOME`` or
``reader(cache_dir=...)`` points.

Cached weights are re-verified against :data:`WEIGHTS_SHA256` on every
call, so upgrading this package can never leave you running the previous
release's model, and a corrupted file is replaced rather than loaded.

The model is produced by
`tetrak-hy-trainer <https://github.com/scattercode/tetrak-hy-trainer>`_;
this package ships it. `Tetrak <https://tetrak.dev/>`_ is its first
consumer.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from importlib import resources
from pathlib import Path

# The architecture EasyOCR instantiates: its own generation2 network
# (VGG feature extractor, two BiLSTM layers, CTC head), re-exported so the
# weights are loaded by exactly the class they were trained for. This
# import requires easyocr (and its torch) — which is always present, since
# the only reason to import this package is to use it with EasyOCR.
from easyocr.model.vgg_model import Model  # noqa: F401

from .fold import fold_script  # noqa: F401

try:
    # Written by hatch-vcs at build/install time. CI deliberately never
    # builds or installs this package (see tests/conftest.py) and imports
    # it straight from the source tree instead, where this file has never
    # been generated.
    from ._version import __version__
except ImportError:
    __version__ = "0+unknown"

NETWORK_NAME = "tetrak_hy"

# Environment variable naming the cache directory, for machines where
# ~/.tetrak_hy is unwritable, shared or simply the wrong place.
CACHE_DIR_ENV_VAR = "TETRAK_HY_HOME"

# Locally supplied weights are kept in their own subdirectory of the cache.
# EasyOCR reads the weights from `<model_storage_directory>/tetrak_hy.pth`
# and nowhere else, so a directory of its own is the only way to keep a
# training run's .pth out of the released weights' slot.
LOCAL_SUBDIR = "local"

# Weights are published to the Hugging Face model repository, which is
# canonical for them; the library pins one Hub revision per released model
# version. The page carries the provenance record and the checksum below.
MODEL_REPO_URL = "https://huggingface.co/tetrak/easyocr-armenian"

# The model version these weights are, as tagged on the Hub. The URL below
# resolves the tag's commit rather than the tag itself: a tag can be moved,
# a commit cannot, so what ships here is exactly what was reviewed.
WEIGHTS_VERSION = "v1"

# Filled in by the first weights release; None means "not yet released".
# Each release updates both together — a URL without its checksum must
# never ship.
WEIGHTS_URL: str | None = (
    "https://huggingface.co/tetrak/easyocr-armenian/resolve/"
    "ac7df15cb01629f5d6e0bba4fcf57213117a3c82/tetrak_hy.pth"
)
WEIGHTS_SHA256: str | None = "62de0cbe37e772ce62929c8cb35eae1ccf8cef120b0a4da1723306afea328d0f"


class WeightsNotAvailableError(RuntimeError):
    """Raised when no verified weights are released, supplied or cached."""


class CacheDirectoryError(RuntimeError):
    """Raised when the cache directory cannot be created or written to."""


def cache_dir(override: Path | str | None = None) -> Path:
    """The directory the network config and weights are materialised into.

    Resolved in order: *override*, the ``TETRAK_HY_HOME`` environment
    variable, then ``~/.tetrak_hy``. A value from either of the first two
    may use ``~`` and environment variables of its own.

    Args:
        override: An explicit directory, taking precedence over everything.

    Returns:
        The resolved path, which is not created here — see :func:`reader`.
    """
    setting = override if override is not None else os.environ.get(CACHE_DIR_ENV_VAR)
    if not setting:
        return Path.home() / f".{NETWORK_NAME}"
    return Path(os.path.expandvars(os.path.expanduser(str(setting))))


def _prepare_cache_dir(override: Path | str | None) -> Path:
    """Resolve the cache directory, create it, and confirm we can write to it.

    Checked here so an unwritable directory is reported against the path
    and the setting that chose it, rather than surfacing later as an
    obscure failure inside EasyOCR.

    Raises:
        CacheDirectoryError: The directory cannot be created or written to.
    """
    directory = cache_dir(override)
    remedy = f"Set ${CACHE_DIR_ENV_VAR} or pass reader(cache_dir=...) to put it somewhere writable."

    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise CacheDirectoryError(
            f"Cannot create the tetrak_hy cache directory {directory}: {error}. {remedy}"
        ) from error

    if not os.access(directory, os.W_OK | os.X_OK):
        raise CacheDirectoryError(
            f"The tetrak_hy cache directory {directory} is not writable. {remedy}"
        )

    return directory


def _materialise_config(directory: Path) -> Path:
    """Write the packaged ``tetrak_hy.yaml`` into *directory*.

    Rewritten whenever it differs from the packaged copy. The yaml's
    ``character_list`` fixes the model's ``num_class``, so a stale one left
    behind by an earlier version would not match freshly downloaded
    weights.
    """
    destination = directory / f"{NETWORK_NAME}.yaml"
    source = resources.files(__package__) / f"{NETWORK_NAME}.yaml"
    packaged = source.read_text(encoding="utf-8")

    if not destination.exists() or destination.read_text(encoding="utf-8") != packaged:
        destination.write_text(packaged, encoding="utf-8")

    return destination


def _sha256(path: Path) -> str:
    """The SHA-256 of a file, read in blocks rather than held in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_atomically(destination: Path, payload: bytes) -> None:
    """Write *payload* to *destination* via a temporary file beside it.

    A half-written ``.pth`` would fail its checksum on the next call and be
    re-downloaded, but it would also be handed to EasyOCR by anything that
    reads the cache directly, so the file only ever appears complete.
    """
    descriptor, temporary = tempfile.mkstemp(
        dir=destination.parent, prefix=f"{destination.name}.", suffix=".part"
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _download_weights(destination: Path) -> None:
    """Fetch the released weights, verify them, and put them at *destination*.

    Nothing is written until the checksum matches, so a failed download
    leaves no ``.pth`` behind for the next call to trust.

    Raises:
        WeightsNotAvailableError: The download failed, or its bytes did not
            match :data:`WEIGHTS_SHA256`.
    """
    import requests

    try:
        response = requests.get(WEIGHTS_URL, timeout=300)
        response.raise_for_status()
    except Exception as error:
        raise WeightsNotAvailableError(
            f"Could not download the tetrak_hy weights from {WEIGHTS_URL}: {error}. "
            f"If this machine has no outbound access, fetch them elsewhere and save "
            f"them as {destination}; they are verified against SHA-256 "
            f"{WEIGHTS_SHA256} on every load, so a correct copy is never "
            f"re-downloaded. The weights and their checksum are published at "
            f"{MODEL_REPO_URL}"
        ) from error

    digest = hashlib.sha256(response.content).hexdigest()
    if digest != WEIGHTS_SHA256:
        raise WeightsNotAvailableError(
            f"Downloaded weights failed their checksum: expected {WEIGHTS_SHA256}, "
            f"got {digest}. Refusing to install them."
        )

    _write_atomically(destination, response.content)


def _materialise_weights(directory: Path, weights_path: Path | str | None) -> Path:
    """Place a verified ``tetrak_hy.pth`` and return the path EasyOCR loads.

    The released weights are cached at ``<directory>/tetrak_hy.pth`` and
    hashed against :data:`WEIGHTS_SHA256` on every call: a cached file is
    never trusted on its name alone. An upgrade that ships new weights, a
    truncated download and a tampered file therefore all lead to a fresh,
    verified download rather than a silently wrong model. A file that does
    match is returned untouched, so a machine with no outbound access works
    once the weights are in place.

    A *weights_path* is copied into ``<directory>/local/`` instead, leaving
    the released weights' cache entry alone — a training run cannot become
    what the next plain ``reader()`` call loads. It goes in a directory of
    its own because EasyOCR insists on the filename; the returned path's
    parent is what :func:`reader` passes as ``model_storage_directory``, so
    EasyOCR caches its detector model beside whichever weights are in use.

    Args:
        directory: The resolved cache directory.
        weights_path: A local ``.pth`` to use instead of the released
            weights — for training runs and pre-release testing.

    Returns:
        The path of the ``.pth`` EasyOCR should load.

    Raises:
        WeightsNotAvailableError: No local path was given and no verified
            weights could be obtained.
    """
    if weights_path is not None:
        local_directory = directory / LOCAL_SUBDIR
        local_directory.mkdir(parents=True, exist_ok=True)
        destination = local_directory / f"{NETWORK_NAME}.pth"
        shutil.copyfile(weights_path, destination)
        return destination

    destination = directory / f"{NETWORK_NAME}.pth"

    if WEIGHTS_URL is None or WEIGHTS_SHA256 is None:
        raise WeightsNotAvailableError(
            f"No trained tetrak_hy weights have been released yet, so there is no "
            f"published checksum to verify {destination} against — and this package "
            f"never loads weights it cannot check. Pass weights_path= to use a local "
            f"model, or watch {MODEL_REPO_URL}"
        )

    if destination.exists() and _sha256(destination) == WEIGHTS_SHA256:
        return destination

    _download_weights(destination)
    return destination


def reader(
    weights_path: Path | str | None = None,
    cache_dir: Path | str | None = None,
    **reader_kwargs,
):
    """Return an ``easyocr.Reader`` configured with the Armenian model.

    The network config and weights are materialised into the cache
    directory on first use. Cached weights are hashed and compared with
    :data:`WEIGHTS_SHA256` every time, and re-downloaded when they do not
    match, so upgrading this package picks up the weights that came with
    it. Weights that do match are used as they are, without touching the
    network.

    Args:
        weights_path: Optional local ``.pth`` overriding the released
            weights — for training runs and pre-release testing. It is
            copied into a ``local/`` subdirectory of the cache rather than
            over the released weights, so it does not become what the next
            plain ``reader()`` call loads. EasyOCR caches its detector model
            beside the weights in use, so the first call passing this
            downloads a second copy of the detector.
        cache_dir: Where to materialise the config and weights. Defaults to
            ``$TETRAK_HY_HOME``, and then to ``~/.tetrak_hy``.
        **reader_kwargs: Passed through to ``easyocr.Reader`` — ``gpu=``,
            ``verbose=`` and friends.

    Returns:
        A ready ``easyocr.Reader``.

    Raises:
        CacheDirectoryError: See :func:`_prepare_cache_dir`.
        WeightsNotAvailableError: See :func:`_materialise_weights`.
    """
    import easyocr

    directory = _prepare_cache_dir(cache_dir)
    _materialise_config(directory)
    weights = _materialise_weights(directory, weights_path)

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
        model_storage_directory=str(weights.parent),
        **reader_kwargs,
    )
