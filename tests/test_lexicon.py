"""Lexicon-aided decoding, on hand-built probability matrices.

Pure Python, so these run in the torch-free CI. Each matrix is a list of
frames over a five-class alphabet; a frame is written as the class that
wins it plus, where it matters, a runner-up and its probability.
"""

from __future__ import annotations

import math
import types

import pytest

from tetrak_hy import lexicon

CHARACTER = ["[blank]", " ", "ա", "բ", "գ", "դ", ",", "x"]
BLANK, SPACE, A, B, G, D, COMMA, X = range(len(CHARACTER))


def frame(winner: int, runner_up: int | None = None, runner_p: float = 0.0) -> list[float]:
    row = [1e-6] * len(CHARACTER)
    row[winner] = 1.0 - runner_p
    if runner_up is not None:
        row[runner_up] = runner_p
    total = sum(row)
    return [p / total for p in row]


def word(*classes: int) -> list[list[float]]:
    """A word read cleanly: each class, then a blank."""
    frames = []
    for c in classes:
        frames += [frame(c), frame(BLANK)]
    return frames


def decoder(words: set[str], tau: float = lexicon.DEFAULT_TAU) -> lexicon.LexiconDecoder:
    return lexicon.LexiconDecoder(CHARACTER, [0], frozenset(words), tau=tau)


# "աբ" read with "դ" as the runner-up for "բ": greedy says աբ, the n-best has ադ.
AMBIGUOUS = [frame(A), frame(BLANK), frame(B, D, 0.3), frame(BLANK)]


class TestCorrection:
    def test_a_word_in_the_list_is_left_alone(self) -> None:
        assert decoder({"աբ", "ադ"}).decode(AMBIGUOUS) == "աբ"

    def test_an_unknown_word_takes_a_close_listed_reading(self) -> None:
        assert decoder({"ադ"}).decode(AMBIGUOUS) == "ադ"

    def test_a_distant_listed_reading_is_refused(self) -> None:
        """log(0.7) - log(0.3) is about 0.85; a threshold below it keeps the greedy reading."""
        assert decoder({"ադ"}, tau=0.5).decode(AMBIGUOUS) == "աբ"
        assert math.log(0.7 / 0.3) > 0.5

    def test_no_listed_reading_keeps_the_greedy_one(self) -> None:
        assert decoder({"գգ"}).decode(AMBIGUOUS) == "աբ"


class TestWhatIsNeverTouched:
    def test_words_without_an_armenian_letter(self) -> None:
        mat = [frame(X), frame(BLANK), frame(X, A, 0.4)]
        assert decoder({"xա"}).decode(mat) == "xx"

    def test_one_letter_words(self) -> None:
        assert decoder({"դ"}).decode([frame(B, D, 0.4)]) == "բ"

    def test_the_words_around_a_correction_and_the_spaces_between_them(self) -> None:
        mat = word(G, G) + [frame(SPACE), frame(SPACE)] + AMBIGUOUS + [frame(SPACE)] + word(X)
        assert decoder({"ադ"}).decode(mat) == "գգ ադ x"

    def test_a_correction_keeps_the_words_punctuation(self) -> None:
        """A candidate that also drops the trailing comma is not a correction of the word."""
        mat = AMBIGUOUS + [frame(COMMA, BLANK, 0.45)]
        assert decoder({"ադ"}).decode(mat) == "ադ,"


class TestWordList:
    def test_rare_words_are_dropped_and_keys_are_bare(self, tmp_path) -> None:
        path = tmp_path / "words.tsv"
        path.write_text("Աբ,\t5\nգդ\t1\nդդ\n", encoding="utf-8")
        assert lexicon.load_wordlist(path) == {"աբ", "դդ"}

    def test_a_compressed_list_is_read(self, tmp_path) -> None:
        import gzip

        path = tmp_path / "words.tsv.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write("աբ\t3\n")
        assert lexicon.load_wordlist(path) == {"աբ"}

    def test_the_armenian_comma_is_punctuation_not_a_letter(self) -> None:
        """U+055D sits between the Armenian letter ranges; it must not join the key."""
        assert lexicon.core("գրել՝") == "գրել"


def test_use_lexicon_replaces_the_readers_beam_search_hook() -> None:
    converter = types.SimpleNamespace(character=CHARACTER, ignore_idx=[0], decode_beamsearch=None)
    reader = types.SimpleNamespace(converter=converter)
    installed = lexicon.use_lexicon(reader, frozenset({"ադ"}))
    assert converter.decode_beamsearch is installed
    assert installed([AMBIGUOUS], beamWidth=5) == ["ադ"]


@pytest.mark.parametrize("tau", [0.0, lexicon.DEFAULT_TAU])
def test_a_clean_reading_decodes_to_itself(tau: float) -> None:
    assert decoder(set(), tau=tau).decode(word(A, B, G)) == "աբգ"
