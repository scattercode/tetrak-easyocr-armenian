"""The released word list: pinned, verified and cached exactly as the weights are."""

from __future__ import annotations

import gzip
import hashlib

import pytest

LIST = gzip.compress("աբ\t5\nգդ\t1\n".encode())
LIST_SHA256 = hashlib.sha256(LIST).hexdigest()


class Response:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


@pytest.fixture
def released(tetrak, monkeypatch):
    monkeypatch.setattr(tetrak, "WORDLIST_URL", "https://example.invalid/wordlist.tsv.gz")
    monkeypatch.setattr(tetrak, "WORDLIST_SHA256", LIST_SHA256)
    return tetrak


def test_url_and_checksum_are_set_together(tetrak) -> None:
    assert (tetrak.WORDLIST_URL is None) == (tetrak.WORDLIST_SHA256 is None)


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
