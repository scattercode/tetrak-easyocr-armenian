"""The cache: where it lives, and what is allowed out of it.

The rule these tests exist to hold is that a cached ``tetrak_hy.pth`` is
never trusted on its name alone. Its filename does not change between
releases, so without a hash check an upgrade would silently keep running
the previous release's weights — and every consumer recording "weights
version = library version" would be recording a lie.

These exercise the helpers rather than ``reader()``, which needs the OCR
stack; see conftest.py for how the package is imported without it.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

RELEASED = b"the released weights"
RELEASED_SHA256 = hashlib.sha256(RELEASED).hexdigest()
SUPERSEDED = b"the previous release's weights"


@pytest.fixture
def released(tetrak, monkeypatch):
    """Pretend a release exists, pinning RELEASED as its published weights."""
    monkeypatch.setattr(tetrak, "WEIGHTS_URL", "https://example.invalid/tetrak_hy.pth")
    monkeypatch.setattr(tetrak, "WEIGHTS_SHA256", RELEASED_SHA256)
    return tetrak


@pytest.fixture
def unpublished(tetrak, monkeypatch):
    """The package with no weights published: URL and checksum both unset.

    Set here rather than read from the module, which now ships real ones.
    The state is still reachable — a code-only release before the next
    model version — and the refusal it produces is the point.
    """
    monkeypatch.setattr(tetrak, "WEIGHTS_URL", None)
    monkeypatch.setattr(tetrak, "WEIGHTS_SHA256", None)
    return tetrak


class Response:
    """The slice of ``requests.Response`` that _download_weights uses."""

    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


def cached_pth(directory: Path) -> Path:
    return directory / "tetrak_hy.pth"


class TestCachedWeights:
    def test_a_matching_file_is_used_without_a_download(
        self, released, fake_requests, tmp_path
    ) -> None:
        """The no-network path: a correct cached file is enough on its own."""
        cached_pth(tmp_path).write_bytes(RELEASED)

        # fake_requests.get refuses to be called, so reaching the network fails.
        weights = released._materialise_weights(tmp_path, None)

        assert weights == cached_pth(tmp_path)
        assert weights.read_bytes() == RELEASED

    def test_a_file_from_an_earlier_release_is_replaced(
        self, released, fake_requests, tmp_path
    ) -> None:
        """The upgrade case: same filename, different weights, no warning."""
        cached_pth(tmp_path).write_bytes(SUPERSEDED)
        fake_requests.get = lambda *args, **kwargs: Response(RELEASED)

        weights = released._materialise_weights(tmp_path, None)

        assert weights.read_bytes() == RELEASED

    def test_a_corrupted_file_is_replaced(self, released, fake_requests, tmp_path) -> None:
        """One flipped byte is as untrustworthy as the wrong weights entirely."""
        cached_pth(tmp_path).write_bytes(RELEASED[:-1] + b"!")
        fake_requests.get = lambda *args, **kwargs: Response(RELEASED)

        assert released._materialise_weights(tmp_path, None).read_bytes() == RELEASED


class TestDownloadFailures:
    def test_bytes_failing_the_checksum_leave_nothing_behind(
        self, released, fake_requests, tmp_path
    ) -> None:
        """Refusing to install them means no .pth and no stray part file."""
        fake_requests.get = lambda *args, **kwargs: Response(b"not the released weights")

        with pytest.raises(released.WeightsNotAvailableError, match="checksum"):
            released._materialise_weights(tmp_path, None)

        assert list(tmp_path.iterdir()) == []

    def test_a_failed_request_says_where_to_put_the_file(
        self, released, fake_requests, tmp_path
    ) -> None:
        def unreachable(*args, **kwargs):
            raise OSError("no route to host")

        fake_requests.get = unreachable

        with pytest.raises(released.WeightsNotAvailableError) as raised:
            released._materialise_weights(tmp_path, None)

        message = str(raised.value)
        assert str(cached_pth(tmp_path)) in message
        assert RELEASED_SHA256 in message
        assert not cached_pth(tmp_path).exists()


class TestWithoutAPublishedChecksum:
    def test_no_release_and_no_cache_names_the_cache_path(self, unpublished, tmp_path) -> None:
        with pytest.raises(unpublished.WeightsNotAvailableError) as raised:
            unpublished._materialise_weights(tmp_path, None)

        assert str(cached_pth(tmp_path)) in str(raised.value)
        assert unpublished.MODEL_REPO_URL in str(raised.value)

    def test_a_cached_file_is_not_trusted_without_a_published_checksum(
        self, unpublished, fake_requests, tmp_path
    ) -> None:
        """Nothing to verify against is a refusal, not a licence to load it."""
        cached_pth(tmp_path).write_bytes(RELEASED)

        with pytest.raises(unpublished.WeightsNotAvailableError):
            unpublished._materialise_weights(tmp_path, None)


class TestLocalWeights:
    def test_the_released_slot_is_left_alone(self, released, tmp_path) -> None:
        """A training run's .pth must not become the next reader()'s model."""
        cached_pth(tmp_path).write_bytes(RELEASED)
        mine = tmp_path / "from_training_run.pth"
        mine.write_bytes(b"an experiment")

        weights = released._materialise_weights(tmp_path, mine)

        assert weights == tmp_path / "local" / "tetrak_hy.pth"
        assert weights.read_bytes() == b"an experiment"
        assert cached_pth(tmp_path).read_bytes() == RELEASED

    def test_the_file_keeps_the_name_easyocr_demands(self, released, tmp_path) -> None:
        """EasyOCR reads <model_storage_directory>/tetrak_hy.pth, nothing else."""
        mine = tmp_path / "elsewhere" / "epoch_12.pth"
        mine.parent.mkdir()
        mine.write_bytes(b"an experiment")

        weights = released._materialise_weights(tmp_path, mine)

        assert weights.name == "tetrak_hy.pth"
        assert weights.parent != tmp_path


class TestCacheDirectory:
    def test_the_default_is_a_dot_directory_in_the_home(self, tetrak, monkeypatch) -> None:
        monkeypatch.delenv(tetrak.CACHE_DIR_ENV_VAR, raising=False)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/somewhere/home")))

        assert tetrak.cache_dir() == Path("/somewhere/home/.tetrak_hy")

    def test_the_environment_variable_wins_over_the_default(
        self, tetrak, monkeypatch, tmp_path
    ) -> None:
        monkeypatch.setenv(tetrak.CACHE_DIR_ENV_VAR, str(tmp_path / "elsewhere"))

        assert tetrak.cache_dir() == tmp_path / "elsewhere"

    def test_the_argument_wins_over_the_environment_variable(
        self, tetrak, monkeypatch, tmp_path
    ) -> None:
        monkeypatch.setenv(tetrak.CACHE_DIR_ENV_VAR, str(tmp_path / "from_the_environment"))

        assert tetrak.cache_dir(tmp_path / "from_the_argument") == tmp_path / "from_the_argument"

    def test_the_home_shorthand_and_variables_are_expanded(
        self, tetrak, monkeypatch, tmp_path
    ) -> None:
        # HOME rather than Path.home: os.path.expanduser reads the
        # environment, and it is what expands the "~" being tested here.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("A_CACHE_ROOT", str(tmp_path / "root"))
        monkeypatch.setenv(tetrak.CACHE_DIR_ENV_VAR, "$A_CACHE_ROOT/models")

        assert tetrak.cache_dir() == tmp_path / "root" / "models"
        assert tetrak.cache_dir("~/models") == tmp_path / "models"

    def test_an_empty_setting_falls_back_to_the_default(
        self, tetrak, monkeypatch, tmp_path
    ) -> None:
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        monkeypatch.setenv(tetrak.CACHE_DIR_ENV_VAR, "")

        assert tetrak.cache_dir() == tmp_path / ".tetrak_hy"

    def test_the_directory_is_created(self, tetrak, tmp_path) -> None:
        directory = tetrak._prepare_cache_dir(tmp_path / "made" / "on" / "demand")

        assert directory.is_dir()

    @pytest.mark.skipif(
        hasattr(os, "geteuid") and os.geteuid() == 0,
        reason="root ignores the permissions this checks",
    )
    def test_an_unwritable_directory_is_reported_against_its_path(self, tetrak, tmp_path) -> None:
        """Better here than as an obscure failure inside EasyOCR later."""
        readonly = tmp_path / "readonly"
        readonly.mkdir()
        readonly.chmod(0o500)

        try:
            with pytest.raises(tetrak.CacheDirectoryError) as raised:
                tetrak._prepare_cache_dir(readonly)
        finally:
            readonly.chmod(0o700)

        message = str(raised.value)
        assert str(readonly) in message
        assert tetrak.CACHE_DIR_ENV_VAR in message


class TestPackagedConfigMaterialising:
    def test_a_stale_config_is_rewritten(self, tetrak, tmp_path) -> None:
        """The yaml's character_list fixes num_class, so it must move with
        the weights rather than survive an upgrade."""
        stale = tmp_path / "tetrak_hy.yaml"
        stale.write_text("character_list: from an older version\n", encoding="utf-8")

        written = tetrak._materialise_config(tmp_path)

        packaged = Path(tetrak.__file__).parent / "tetrak_hy.yaml"
        assert written.read_text(encoding="utf-8") == packaged.read_text(encoding="utf-8")
