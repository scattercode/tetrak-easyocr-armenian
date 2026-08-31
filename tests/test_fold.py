"""The script-consistency fold -- see fold.py's module docstring for what
it folds, at what scope, and why. Pure string handling, no easyocr or
torch needed, so this runs in CI without any stand-in."""

from __future__ import annotations

from tetrak_hy.fold import fold_script


class TestHomoglyphs:
    def test_folds_latin_h_when_the_token_has_an_armenian_letter(self) -> None:
        assert fold_script("hայաստան") == "հայաստան"

    def test_folds_capital_latin_h(self) -> None:
        assert fold_script("Hայաստան") == "Հայաստան"

    def test_folds_latin_o_when_the_token_has_an_armenian_letter(self) -> None:
        assert fold_script("oրեր") == "օրեր"

    def test_folds_capital_latin_o(self) -> None:
        assert fold_script("Oրեր") == "Օրեր"

    def test_folds_colon_to_armenian_full_stop(self) -> None:
        assert fold_script("Երևան:") == "Երևան։"

    def test_does_not_fold_en_dash(self) -> None:
        """Deliberate: the transcripts use en dash as a genuine
        orthographic convention (case-suffix attachment, e.g. "Ա–ի") far
        more often than the model confuses it for a hyphen. See the
        module docstring for the measured regression this would cause."""
        assert fold_script("Ա–ի") == "Ա–ի"

    def test_does_not_fold_em_dash(self) -> None:
        assert fold_script("1886—ին") == "1886—ին"

    def test_folds_every_homoglyph_once_a_token_has_one_armenian_letter(self) -> None:
        # a single Armenian letter anywhere in the token is enough to fold
        # every homoglyph in that same token, not just the ones beside it
        assert fold_script("h:oԱ") == "հ։օԱ"


class TestScopeIsPerToken:
    def test_latin_word_next_to_armenian_text_is_left_alone(self) -> None:
        text = "Երևանում history:"
        assert fold_script(text) == "Երևանում history:"

    def test_pure_latin_string_is_untouched(self) -> None:
        assert fold_script("history: 1907") == "history: 1907"

    def test_cyrillic_string_is_untouched(self) -> None:
        # Cyrillic bibliography lines are out of scope (finding 1) -- no
        # Armenian letters means no fold, by construction.
        assert fold_script("История: 1907") == "История: 1907"

    def test_punctuation_only_token_next_to_armenian_is_not_folded(self) -> None:
        """Documents a deliberate, known gap: a token entirely of digits
        and punctuation (no Armenian letter of its own) is not folded even
        when it sits next to Armenian text, e.g. a stray "363):" would stay
        as EasyOCR read it rather than becoming "363)։". Folding indiscrim-
        inately by line risks rewriting genuine Latin/Cyrillic text sharing
        a detected region with Armenian words."""
        assert fold_script("Ուսումնասիրություն 363):") == "Ուսումնասիրություն 363):"

    def test_whitespace_between_tokens_is_preserved_exactly(self) -> None:
        assert fold_script("hայ  oրեր") == "հայ  օրեր"


class TestNoArmenianLetters:
    def test_empty_string(self) -> None:
        assert fold_script("") == ""

    def test_digits_only(self) -> None:
        assert fold_script("1907") == "1907"


class TestIdempotence:
    def test_folding_twice_matches_folding_once(self) -> None:
        text = "hայ oրեր Երևան: 1886–ին"
        once = fold_script(text)
        assert fold_script(once) == once
