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


class TestDigitTwo:
    """``Չ`` and ``շ`` read for the digit 2 in bold and italic numbers (brief 013)."""

    def test_a_page_number_is_read_as_digits(self) -> None:
        assert fold_script("Չ51, ՉՉ3, 22շ") == "251, 223, 222"

    def test_punctuation_around_the_number_is_kept(self) -> None:
        assert fold_script("(Եր. Չ84).") == "(Եր. 284)."

    def test_an_armenian_word_with_the_letter_is_untouched(self) -> None:
        assert fold_script("Չորս շատ") == "Չորս շատ"

    def test_the_letter_alone_is_not_a_number(self) -> None:
        assert fold_script("Չ, շ") == "Չ, շ"


class TestLatinAgainstCyrillic:
    """A token with no Armenian letter is written in one script (brief 014).

    v7 reads Cyrillic, so the glyphs Latin and Cyrillic share come out in
    either script; on the Armenian-English dictionary it printed ``роог``
    for ``poor`` on pages with no Cyrillic at all."""

    def test_a_shared_glyph_token_follows_the_latin_text_around_it(self) -> None:
        text = "poverty, n. աղքատութիւն. роог, a. աղքատ. еуe, n. աչք"
        assert fold_script(text) == "poverty, n. աղքատութիւն. poor, a. աղքատ. eye, n. աչք"

    def test_an_unshared_latin_letter_decides_the_token_by_itself(self) -> None:
        # ``l`` is Latin alone, so the token is Latin whatever surrounds it.
        assert fold_script("cоal") == "coal"
        assert fold_script("Ярмарка cоal") == "Ярмарка coal"

    def test_an_unshared_cyrillic_letter_decides_the_token_by_itself(self) -> None:
        # ``ж`` is Cyrillic alone: the Latin ``a`` the model emitted inside it folds.
        assert fold_script("жaра") == "жара"

    def test_ge_is_read_as_r_in_a_latin_token(self) -> None:
        assert fold_script("the еаг and the роог") == "the ear and the poor"

    def test_a_token_of_shared_glyphs_follows_cyrillic_text(self) -> None:
        text = "Пушкин писал о сосо"
        assert fold_script("Пушкин писал o coco", context=text) == "Пушкин писал о сосо"

    def test_a_token_with_unshared_letters_of_both_scripts_is_left_alone(self) -> None:
        assert fold_script("wыil ingenious") == "wыil ingenious"

    def test_no_context_means_no_decision(self) -> None:
        # ``coco`` is all shared glyphs and nothing around it says which script.
        assert fold_script("coco") == "coco"
        assert fold_script("сосо") == "сосо"

    def test_balanced_text_decides_nothing(self) -> None:
        assert fold_script("жил was сосо") == "жил was сосо"

    def test_context_overrides_the_text_itself(self) -> None:
        page = "\n".join(["Pride and Prejudice"] * 3)
        assert fold_script("роог", context=page) == "poor"

    def test_an_armenian_token_is_still_folded_the_old_way(self) -> None:
        assert fold_script("hայ and еаг") == "հայ and ear"

    def test_genuine_russian_text_is_untouched(self) -> None:
        text = "Собрание сочинений в десяти томах. Том 5. Москва, 1960"
        assert fold_script(text) == text

    def test_folding_twice_matches_folding_once(self) -> None:
        text = "poverty, n. аղքատ. роог, a. аղքատ. еуe, n. աչք wыil"
        once = fold_script(text)
        assert fold_script(once) == once
