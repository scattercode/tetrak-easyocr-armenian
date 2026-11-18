"""The released weights still read what brief 014 trained them for.

Two crops, one word each, from pages the model never trained on: a
classical-orthography word with a free-standing ``ւ`` (*աւելի*, Khrimian's
Works) and a Russian word from the apparatus of Tumanyan's academic
edition (*короба*). v6 read neither: it had no Cyrillic class, and it was
trained on reformed print alone. v8 is a fine-tune of v7 that reads a few
fewer Russian words than v7 did, so the Cyrillic crop is the one to watch
at each release. Needs easyocr and the network, so it runs
locally and skips in CI, like ``TestWithEasyocrInstalled``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RELEASED_VERSION = "v8"
RELEASED_COMMIT = "03f3f1d30b14b80bf3a04a72699be056b0113fd3"


@pytest.fixture(scope="module")
def released_reader():
    # conftest registers a stand-in ``easyocr`` module when the real one is
    # absent, so importorskip alone is not enough: the stand-in has no Reader.
    easyocr = pytest.importorskip("easyocr")
    if not hasattr(easyocr, "Reader"):
        pytest.skip("the real easyocr is not installed")
    import tetrak_hy

    return tetrak_hy.reader(verbose=False, lexicon=True)


def read_word(reader, image: Path) -> str:
    import tetrak_hy

    texts = reader.readtext(str(image), detail=0, paragraph=False, decoder="beamsearch")
    return tetrak_hy.fold_script(" ".join(texts)).strip(" .,")


def test_the_pins_name_the_release_at_one_commit(tetrak) -> None:
    assert tetrak.WEIGHTS_VERSION == RELEASED_VERSION
    for url in (tetrak.WEIGHTS_URL, tetrak.WORDLIST_URL, tetrak.CLASSICAL_WORDLIST_URL):
        assert url is not None and f"/resolve/{RELEASED_COMMIT}/" in url


def test_a_classical_spelling_is_read_as_printed(released_reader) -> None:
    assert read_word(released_reader, FIXTURES / "classical.png") == "աւելի"


def test_a_russian_word_is_read_in_cyrillic(released_reader) -> None:
    assert read_word(released_reader, FIXTURES / "cyrillic.png") == "короба"
