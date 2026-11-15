"""Script-consistency fold for text this package's model has recognised.

v1's per-word error analysis (design research 010) found that roughly
half of v1's word-recall gap against ``tesseract -l hye`` is not a
recognition failure. The CTC head has no language model, so inside an
Armenian word it sometimes emits the visually identical Latin twin of an
Armenian character instead of the Armenian one -- Latin ``h`` for ``հ``,
Latin ``o`` for ``օ``, a colon for the Armenian full stop ``։``. All of
these are already in the model's charset (see the packaged
``tetrak_hy.yaml``), so this is a serialisation problem, not a training
one: folding the wrong glyph back to the right one, on the *predicted*
side only, measured net +449 words recovered (zero regressed) on the
same evaluation pages, with no retraining.

Dashes are deliberately **not** folded, despite being a homoglyph
confusion in the analysis's confusion table (23 occurrences of truth
``-`` read back as ``–``). tetrak-hy-trainer's harvested ASE transcripts
also use en dash as a genuine orthographic convention -- attaching a
grammatical case suffix to an abbreviated headword, e.g. ``Ա–ի`` -- 184
truth words do this. Re-scoring v1's saved predictions with a dash fold
in place showed why an unconditional character swap cannot tell these
apart: it broke 74 correctly-predicted ``–`` words for every 66 ``-``
words it recovered, a net *loss*. A future, better-targeted fix (e.g.
scoped to digit-adjacent tokens, where finding 3's year compounds like
``1886-ին`` live) is possible but wasn't shown to help either at that
same measurement -- left as a known gap rather than guessed at here.

Scope is deliberately narrow: **each whitespace-separated token**, folded
only when that token already contains at least one Armenian letter. A
token made up entirely of digits or punctuation (a page number, a
stray ``363)``) is left alone even when it sits next to Armenian text --
that is a known, accepted gap, not an oversight; folding indiscriminately
would risk rewriting genuine Latin or Cyrillic text that happens to share
a line with Armenian.

Folding ASCII ``.`` to U+2024 ONE DOT LEADER is deliberately **not** done
here. That character is missing from v1's charset for a different reason
(the training pipeline silently filtered every crop containing it, so the
model can never emit it at all) and folding it here would rewrite genuine
full stops. It is fixed by widening the charset, not by this fold.

**Latin against Cyrillic** (brief 014). v7 is the first model trained to
read Cyrillic, and the glyphs that Latin and Cyrillic share -- ``а`` and
``a``, ``р`` and ``p``, ``с`` and ``c`` -- are one shape with two
characters in its charset. Which one it emits is a coin toss the training
mix loaded towards Cyrillic, so on the bilingual Armenian-English
dictionary it printed ``роог`` for ``poor`` and ``еуe`` for ``eye`` on
pages with no Cyrillic at all. A token with no Armenian letter is now
read as one script: the letters only one script has (``w``, ``l``,
``ж``, ``я``) decide it, and the shared glyphs are written in that
script. A token made only of shared glyphs is decided by the text
around it -- the whole string given to :func:`fold_script`, or
``context`` when the caller has more of the page than the one token --
and only when that text is overwhelmingly one script; a token that has
unshared letters of both scripts is left alone, as is one with no
context to decide it. ``г`` for ``r`` is included on the Cyrillic side
because the model confuses them that way round, though they are not the
same glyph. Re-scoring v7's and v6's saved readings of all eighteen
evaluation registers with this rule moved four of v7's up and none of
either model's down: the dictionary's English words 711 -> 718 of 982
with the stray Cyrillic tokens halved, the Soviet encyclopedia's Latin
113 -> 122 of 179, and a word each on the medical encyclopedia and the
Tumanyan notes. The rest of the dictionary's regression was plain Latin
misreads, fixed in training rather than here.

**Three scripts, one decision per token** (brief 014, issue #17). Every
token is read as Armenian, Latin or Cyrillic, or left undecided, and
only then are its glyphs written in that script. A token with any
Armenian letter is Armenian whatever else it holds: the ground truth
keeps no token that mixes Armenian with Cyrillic, so a Cyrillic letter
inside one can never be meant, and the Cyrillic copies of the glyphs the
Latin table already folds -- ``о`` and ``О`` for ``օ`` and ``Օ``, ``Н``
for ``Հ`` -- are folded the same way. Nothing else is: on v7's readings
of the eighteen evaluation registers, 43 Armenian tokens carried a
Cyrillic letter, not one of them a shared glyph, and the commonest
(``в`` for ``տ``, six times on the dictionary) is a shape confusion for
training to fix, not a script one. A token with no Armenian letter is
Latin or Cyrillic by the letters only one script has, or by its context
when it has none, as above. So the ``h``, ``o`` and colon folds never
touch a Cyrillic token: ``о`` in one stays ``о`` and a Latin ``o`` in one
is written ``о``, not ``օ``; a colon after a Russian word stays a colon;
and a Latin ``h`` beside unshared Cyrillic letters makes a token of two
scripts, which is left as read.

**եւ and և.** The two-letter sequence and the ligature (U+0587) are one
word printed two ways: classical presses mostly set the two sorts,
reformed presses the ligature, and the ground truth keeps what each page
prints. The fold treats them as one by never choosing between them: both
are Armenian letters for the token's script, and neither is rewritten
into the other, so a reader gets the page's own form. Of the 2,442 tokens
v7 emitted with either form on the eighteen registers, nine matched the
page's word only once the two forms were scored as one, and the metric
(``accuracy.normalise`` in Tetrak and the trainer) does score them so.
The word list's look-up key reads them as one too, so
:mod:`tetrak_hy.lexicon` never corrects a word from one form to the other.
"""

from __future__ import annotations

import re
import unicodedata

# Ա–Ֆ (uppercase), ա–ֆ (lowercase), և (the ligature) -- the same three
# ranges tetrak-hy-trainer's charset.py builds ARMENIAN_UPPER/LOWER from.
_ARMENIAN_LETTERS = (
    frozenset(chr(code) for code in range(0x0531, 0x0557))
    | frozenset(chr(code) for code in range(0x0561, 0x0587))
    | {"և"}
)

# Predicted character -> the Armenian form it is confused with, per the
# error analysis's confusion table, with the Cyrillic copy of each shared
# glyph beside the Latin one (brief 014): о and О are the shape of o and
# O, Н the shape of H. Every value is deliberately absent from these keys,
# so applying the fold twice is a no-op. No dash entry: see the module
# docstring for why an unconditional swap does more harm than good on
# this corpus.
_ARMENIAN_LOOKALIKES = {
    "h": "հ",
    "H": "Հ",
    "Н": "Հ",
    "o": "օ",
    "O": "Օ",
    "о": "օ",
    "О": "Օ",
    ":": "։",
}
_TO_ARMENIAN = str.maketrans(_ARMENIAN_LOOKALIKES)

_TOKEN = re.compile(r"\S+")

# Armenian letters the model reads for the digit 2 in bold and italic
# faces. ``Չ`` and ``շ`` share the digit's top curve and foot, and the
# Faustus of Byzantium index -- page numbers set in bold italic -- came out
# as "Չ51", "ՉՉ3", "22շ". Inside a token that is otherwise numbers and
# punctuation, neither letter can be meant, so they are read as the digit
# (brief 013: Faustus word recall 0.908 -> 0.916, no other register moved).
_DIGIT_TWO_LOOKALIKES = str.maketrans({"Չ": "2", "շ": "2"})


# Shared glyphs, keyed by the character the model emitted. The Cyrillic
# side also carries г -> r, a confusion the model makes in that direction
# only. A letter in neither table belongs to one script alone and is what
# decides a token's script; a token with such letters from both scripts
# is genuinely mixed and is left as read.
_CYRILLIC_TO_LATIN = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "г": "r",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "Х": "X",
}  # fmt: skip
_LATIN_TO_CYRILLIC = {
    "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "y": "у", "x": "х",
    "A": "А", "B": "В", "E": "Е", "K": "К", "M": "М", "H": "Н", "O": "О", "P": "Р",
    "C": "С", "T": "Т", "X": "Х",
}  # fmt: skip
_TO_LATIN = str.maketrans(_CYRILLIC_TO_LATIN)
_TO_CYRILLIC = str.maketrans(_LATIN_TO_CYRILLIC)

ARMENIAN = "armenian"
LATIN = "latin"
CYRILLIC = "cyrillic"
_WRITTEN_IN = {ARMENIAN: _TO_ARMENIAN, LATIN: _TO_LATIN, CYRILLIC: _TO_CYRILLIC}
_LATIN_LETTER = re.compile(r"[A-Za-z]")
_CYRILLIC_LETTER = re.compile(r"[\u0400-\u04ff]")

# How many unshared letters of one script a text needs for each of the
# other before a token of shared glyphs alone is read as that script.
# v7's reading of a dictionary page has hundreds of unshared Latin
# letters against a handful of stray Cyrillic ones; a page of Russian
# notes the reverse. Anything closer is left undecided.
_DOMINANCE = 4


def _unshared_counts(text: str) -> tuple[int, int]:
    """How many letters of *text* belong to Latin alone, and to Cyrillic alone."""
    latin = sum(1 for letter in _LATIN_LETTER.findall(text) if letter not in _LATIN_TO_CYRILLIC)
    cyrillic = sum(
        1 for letter in _CYRILLIC_LETTER.findall(text) if letter not in _CYRILLIC_TO_LATIN
    )
    return latin, cyrillic


def _dominant_script(context: str) -> str | None:
    """``"latin"``, ``"cyrillic"`` or ``None`` for *context*'s non-Armenian tokens."""
    others = [
        token
        for token in context.split()
        if not any(character in _ARMENIAN_LETTERS for character in token)
    ]
    latin, cyrillic = _unshared_counts(" ".join(others))
    if latin and latin >= _DOMINANCE * cyrillic:
        return LATIN
    if cyrillic and cyrillic >= _DOMINANCE * latin:
        return CYRILLIC
    return None


def _token_script(token: str, context_script: str | None) -> str | None:
    """The one script *token* is read in, or ``None`` when nothing can say.

    An Armenian letter makes it Armenian, whatever else it holds. Otherwise
    the letters only Latin or only Cyrillic has decide it; a token with
    such letters of both scripts is genuinely of two, and one with none
    of either (shared glyphs alone, or no letters at all) follows its
    context.
    """
    if any(character in _ARMENIAN_LETTERS for character in token):
        return ARMENIAN
    if not (_LATIN_LETTER.search(token) or _CYRILLIC_LETTER.search(token)):
        return None
    latin, cyrillic = _unshared_counts(token)
    if latin and cyrillic:
        return None
    return LATIN if latin else CYRILLIC if cyrillic else context_script


def _is_numeric_token(token: str) -> bool:
    """A number with its punctuation, allowing for ``Չ``/``շ`` misread for 2."""
    return any(character.isdigit() for character in token) and all(
        character.isdigit() or character in "Չշ" or unicodedata.category(character).startswith("P")
        for character in token
    )


def _fold_token(token: str, context_script: str | None = None) -> str:
    if _is_numeric_token(token):
        return token.translate(_DIGIT_TWO_LOOKALIKES)
    script = _token_script(token, context_script)
    return token.translate(_WRITTEN_IN[script]) if script else token


def fold_script(text: str, *, context: str | None = None) -> str:
    """Fold cross-script homoglyphs in *text* onto the script each token is in.

    Args:
        text: Recognised text -- typically one string from
            ``easyocr.Reader.readtext``. Whitespace between tokens is
            preserved exactly; only the tokens themselves change.
        context: More of the same page, when the caller has it: the text
            of every region, say, while *text* is one region's. It decides
            whether a Latin-or-Cyrillic token made only of shared glyphs
            is read as Latin or as Cyrillic. When omitted, *text* itself is
            the context.

    Returns:
        *text* with each token written in the one script it is read in:
        every Latin or Cyrillic lookalike in an Armenian-containing token
        folded to its Armenian form, and every other token that mixes
        Latin and Cyrillic, or could be either, written in the one script
        it belongs to. Digits, punctuation and tokens that are genuinely
        of two scripts are returned unchanged, and so are ``եւ`` and
        ``և``, which are one word printed two ways.
    """
    script = _dominant_script(text if context is None else context)
    return _TOKEN.sub(lambda match: _fold_token(match.group(), script), text)
