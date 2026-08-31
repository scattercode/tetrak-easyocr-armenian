"""Script-consistency fold for text this package's model has recognised.

v1's per-word error analysis (tetrak's
``product/research/armenian-v1-error-analysis.md``) found that roughly
half of v1's word-recall gap against ``tesseract -l hye`` is not a
recognition failure. The CTC head has no language model, so inside an
Armenian word it sometimes emits the visually identical Latin or
typographic twin of an Armenian character instead of the Armenian one --
Latin ``h`` for ``հ``, Latin ``o`` for ``օ``, a colon for the Armenian full
stop ``։``, an en or em dash for a hyphen. All of these are already in the
model's charset (see the packaged ``tetrak_hy.yaml``), so this is a
serialisation problem, not a training one: folding the wrong glyph back to
the right one, on the *predicted* side only, measured +0.10 word recall on
the same evaluation pages with no retraining.

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
"""

from __future__ import annotations

import re

# Ա–Ֆ (uppercase), ա–ֆ (lowercase), և (the ligature) -- the same three
# ranges tetrak-hy-trainer's charset.py builds ARMENIAN_UPPER/LOWER from.
_ARMENIAN_LETTERS = (
    frozenset(chr(code) for code in range(0x0531, 0x0557))
    | frozenset(chr(code) for code in range(0x0561, 0x0587))
    | {"և"}
)

# Predicted character -> the Armenian or canonical form it is confused
# with, per the error analysis's confusion table. Every value is deliberately
# absent from these keys, so applying the fold twice is a no-op.
_HOMOGLYPHS = {
    "h": "հ",
    "H": "Հ",
    "o": "օ",
    "O": "Օ",
    ":": "։",
    "–": "-",  # en dash
    "—": "-",  # em dash
}

_TOKEN = re.compile(r"\S+")


def _fold_token(token: str) -> str:
    if not any(character in _ARMENIAN_LETTERS for character in token):
        return token
    return "".join(_HOMOGLYPHS.get(character, character) for character in token)


def fold_script(text: str) -> str:
    """Fold cross-script homoglyphs in *text* onto their Armenian form.

    Args:
        text: Recognised text -- typically one string from
            ``easyocr.Reader.readtext``. Whitespace between tokens is
            preserved exactly; only the tokens themselves change.

    Returns:
        *text* with every homoglyph in each Armenian-containing token
        folded to its Armenian or canonical form. A token with no
        Armenian letter of its own is returned unchanged, as is *text* as
        a whole when it contains no Armenian letters at all.
    """
    return _TOKEN.sub(lambda match: _fold_token(match.group()), text)
