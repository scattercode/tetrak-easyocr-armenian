"""The released weights read what brief 014 trained them for.

Two crops, one word each, from pages the model never trained on: a
classical-orthography word with a free-standing ``ւ`` (*աւելի*, Khrimian's
Works) and a Russian word from the apparatus of Tumanyan's academic
edition (*короба*). v6 read neither: it had no Cyrillic class, and it was
trained on reformed print alone. Needs easyocr and the network, so it runs
locally and skips in CI, like ``TestWithEasyocrInstalled``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
V7_COMMIT = "1d7b076caf2555d3dd7ae56997877fc3b27d166b"


@pytest.fixture(scope="module")
def released_reader():
    pytest.importorskip("easyocr")
    import tetrak_hy

    return tetrak_hy.reader(verbose=False, lexicon=True)


def read_word(reader, image: Path) -> str:
    import tetrak_hy

    texts = reader.readtext(str(image), detail=0, paragraph=False, decoder="beamsearch")
    return tetrak_hy.fold_script(" ".join(texts)).strip(" .,")


def test_the_pins_name_v7_at_one_commit(tetrak) -> None:
    assert tetrak.WEIGHTS_VERSION == "v7"
    for url in (tetrak.WEIGHTS_URL, tetrak.WORDLIST_URL, tetrak.CLASSICAL_WORDLIST_URL):
        assert url is not None and f"/resolve/{V7_COMMIT}/" in url


def test_a_classical_spelling_is_read_as_printed(released_reader) -> None:
    assert read_word(released_reader, FIXTURES / "classical.png") == "աւելի"


def test_a_russian_word_is_read_in_cyrillic(released_reader) -> None:
    assert read_word(released_reader, FIXTURES / "cyrillic.png") == "короба"
