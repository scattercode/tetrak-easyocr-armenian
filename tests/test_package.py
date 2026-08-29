"""The loading contract, tested without torch.

CI installs [dev] only, so anything needing easyocr guards with
importorskip and runs locally instead. What CI pins is the half of the
contract that needs no OCR stack: the packaged yaml, the name constraints,
and the weights-release discipline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "src" / "tetrak_hy"


def packaged_config() -> dict:
    with (PACKAGE_DIR / "tetrak_hy.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class TestPackagedConfig:
    def test_ships_the_keys_easyocr_reads(self) -> None:
        config = packaged_config()
        assert set(config) == {"network_params", "imgH", "lang_list", "character_list"}

    def test_charset_is_armenian(self) -> None:
        characters = packaged_config()["character_list"]
        assert "Ա" in characters and "ֆ" in characters
        assert "և" in characters
        for mark in "՝՛՞՜։֊«»":
            assert mark in characters, f"missing Armenian punctuation {mark!r}"

    def test_charset_has_no_duplicates(self) -> None:
        characters = packaged_config()["character_list"]
        assert len(characters) == len(set(characters))

    def test_lang_list_authorises_the_loading_language(self) -> None:
        """reader() constructs Reader(['en']) — see CLAUDE.md — so the yaml
        must authorise 'en' or loading fails at setModelLanguage."""
        assert "en" in packaged_config()["lang_list"]
        assert "hy" in packaged_config()["lang_list"]


class TestNameContract:
    def test_the_package_name_is_the_network_name(self) -> None:
        """EasyOCR imports the network by this exact module name."""
        assert PACKAGE_DIR.name == "tetrak_hy"
        assert PACKAGE_DIR.name.isidentifier()

    def test_the_yaml_is_named_for_the_network(self) -> None:
        assert (PACKAGE_DIR / "tetrak_hy.yaml").exists()


class TestWeightsDiscipline:
    def test_url_and_checksum_move_together(self) -> None:
        """A release URL without its checksum must never ship. Reads the
        source rather than importing it, so CI needs no easyocr."""
        source = (PACKAGE_DIR / "__init__.py").read_text(encoding="utf-8")
        url_declared_empty = "WEIGHTS_URL: str | None = None" in source
        sha_declared_empty = "WEIGHTS_SHA256: str | None = None" in source
        assert url_declared_empty == sha_declared_empty, (
            "WEIGHTS_URL and WEIGHTS_SHA256 must be set (or unset) together"
        )


class TestWithEasyocrInstalled:
    """Exercised locally; skipped in torch-free CI."""

    def test_model_attribute_satisfies_the_import_contract(self) -> None:
        pytest.importorskip("easyocr")
        import tetrak_hy

        assert tetrak_hy.Model is not None
        assert tetrak_hy.NETWORK_NAME == "tetrak_hy"

    def test_reader_without_weights_fails_helpfully(self, tmp_path, monkeypatch) -> None:
        pytest.importorskip("easyocr")
        import tetrak_hy

        monkeypatch.setattr(tetrak_hy, "cache_dir", lambda: tmp_path)

        with pytest.raises(tetrak_hy.WeightsNotAvailableError, match="releases"):
            tetrak_hy.reader()
