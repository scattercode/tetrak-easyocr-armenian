"""Importing tetrak_hy in a torch-free environment.

CI installs tooling only — no easyocr, no torch, no requests — but the
cache and weights helpers are ordinary file handling with no OCR in them,
so they are worth pinning there. Two stand-ins make that possible:

- ``easyocr``, which the package imports at module level for the ``Model``
  re-export, is stubbed only when the real one is absent. A local run
  therefore still exercises the real re-export, and the tests guarded with
  ``importorskip`` still skip in CI rather than passing against a fake.
- ``requests`` is always stubbed, whether or not it is installed: these
  tests must never reach the network.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

# CI does not install the package; the tests run against the source tree.
SOURCE_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _easyocr_stand_in() -> dict[str, types.ModuleType]:
    """The modules `from easyocr.model.vgg_model import Model` looks up."""
    easyocr = types.ModuleType("easyocr")
    model = types.ModuleType("easyocr.model")
    vgg_model = types.ModuleType("easyocr.model.vgg_model")
    vgg_model.Model = type("Model", (), {})
    model.vgg_model = vgg_model
    easyocr.model = model
    return {
        "easyocr": easyocr,
        "easyocr.model": model,
        "easyocr.model.vgg_model": vgg_model,
    }


@pytest.fixture
def tetrak(monkeypatch):
    """The imported package, with easyocr stood in for if it is not installed."""
    try:
        import easyocr  # noqa: F401
    except ImportError:
        for name, module in _easyocr_stand_in().items():
            monkeypatch.setitem(sys.modules, name, module)

    import tetrak_hy

    return tetrak_hy


@pytest.fixture
def fake_requests(monkeypatch):
    """A stand-in ``requests`` whose ``get`` each test sets for itself.

    It refuses to be called by default, so a test that expects no download
    fails loudly if one happens.
    """
    module = types.ModuleType("requests")

    def refuse(*args, **kwargs):
        raise AssertionError("the network was used when it should not have been")

    module.get = refuse
    monkeypatch.setitem(sys.modules, "requests", module)
    return module
