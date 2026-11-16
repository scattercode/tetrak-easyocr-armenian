"""The released word list: pinned, verified and cached exactly as the weights are."""

from __future__ import annotations

import gzip
import hashlib

import pytest

LIST = gzip.compress("աբ\t5\nգդ\t1\n".encode())
LIST_SHA256 = hashlib.sha256(LIST).hexdigest()
CLASSICAL = gzip.compress("նաւ\t9\nգդ\t1\n".encode())
CLASSICAL_SHA256 = hashlib.sha256(CLASSICAL).hexdigest()


class Response:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


@pytest.fixture
def released(tetrak, monkeypatch):
    """The modern list released and the classical one not: the v6 state.

    The package has pinned both since v7, so the classical pair is cleared
    here rather than assumed absent; ``classical_released`` sets it back.
    """
    monkeypatch.setattr(tetrak, "WORDLIST_URL", "https://example.invalid/wordlist.tsv.gz")
    monkeypatch.setattr(tetrak, "WORDLIST_SHA256", LIST_SHA256)
    monkeypatch.setattr(tetrak, "CLASSICAL_WORDLIST_URL", None)
    monkeypatch.setattr(tetrak, "CLASSICAL_WORDLIST_SHA256", None)
    return tetrak


@pytest.fixture
def classical_released(released, monkeypatch):
    monkeypatch.setattr(
        released, "CLASSICAL_WORDLIST_URL", "https://example.invalid/wordlist-classical.tsv.gz"
    )
    monkeypatch.setattr(released, "CLASSICAL_WORDLIST_SHA256", CLASSICAL_SHA256)
    return released


def serve(url: str, *args, **kwargs) -> Response:
    return Response(CLASSICAL if "classical" in url else LIST)


def test_url_and_checksum_are_set_together(tetrak) -> None:
    assert (tetrak.WORDLIST_URL is None) == (tetrak.WORDLIST_SHA256 is None)
    assert (tetrak.CLASSICAL_WORDLIST_URL is None) == (tetrak.CLASSICAL_WORDLIST_SHA256 is None)


def test_an_unreleased_list_is_refused(tetrak, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(tetrak, "WORDLIST_URL", None)
    monkeypatch.setattr(tetrak, "WORDLIST_SHA256", None)
    with pytest.raises(tetrak.WeightsNotAvailableError, match="No tetrak_hy word list"):
        tetrak.wordlist_path(tmp_path)


def test_a_download_is_verified_cached_and_loaded(released, fake_requests, tmp_path) -> None:
    fake_requests.get = lambda *args, **kwargs: Response(LIST)
    assert released.wordlist(tmp_path) == {"աբ"}
    # Cached: a second call must not reach the network.
    fake_requests.get = None
    assert released.wordlist_path(tmp_path).read_bytes() == LIST


def test_a_tampered_download_is_refused(released, fake_requests, tmp_path) -> None:
    fake_requests.get = lambda *args, **kwargs: Response(b"not the list")
    with pytest.raises(released.WeightsNotAvailableError, match="failed their checksum"):
        released.wordlist_path(tmp_path)
    assert not (tmp_path / released.WORDLIST_NAME).exists()


def test_without_a_classical_release_the_modern_list_is_used_alone(
    released, fake_requests, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(released, "CLASSICAL_WORDLIST_URL", None)
    monkeypatch.setattr(released, "CLASSICAL_WORDLIST_SHA256", None)
    fake_requests.get = serve
    assert released.wordlist(tmp_path) == {"աբ"}
    with pytest.raises(released.WeightsNotAvailableError, match="No tetrak_hy classical word list"):
        released.classical_wordlist_path(tmp_path)


def test_with_both_released_the_lexicon_is_their_union(
    classical_released, fake_requests, tmp_path
) -> None:
    fake_requests.get = serve
    assert classical_released.wordlist(tmp_path) == {"աբ", "նաւ"}
    assert (tmp_path / classical_released.CLASSICAL_WORDLIST_NAME).read_bytes() == CLASSICAL
    # Both cached: a second call must not reach the network.
    fake_requests.get = None
    assert classical_released.wordlist(tmp_path) == {"աբ", "նաւ"}


def test_a_tampered_classical_download_is_refused(
    classical_released, fake_requests, tmp_path
) -> None:
    fake_requests.get = lambda url, *a, **k: Response(LIST)  # the modern bytes for both
    with pytest.raises(classical_released.WeightsNotAvailableError, match="failed their checksum"):
        classical_released.wordlist(tmp_path)
    assert not (tmp_path / classical_released.CLASSICAL_WORDLIST_NAME).exists()
