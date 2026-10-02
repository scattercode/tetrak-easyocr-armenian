"""Lexicon-aided decoding: correct out-of-vocabulary words from the model's own n-best.

The recogniser's CTC head has no language model, so a word it misreads by
one letter (``դ`` for ``գ``, ``տ`` for ``ա``) is emitted as written even when
the right word was its own second choice. This decoder looks only at
words whose greedy reading is **not** in a word list, and asks the
recogniser's own probabilities for alternatives: if one of its n-best
readings of that word is in the list, and nearly as probable as the greedy
reading, it is used instead. Words already in the list, words with no
Armenian letter, and one-letter words are never touched, so the text
around a correction is the greedy text byte for byte.

Measured on Tetrak's eight held-out registers (brief 013, Stage 2) it
fixed 465 words and broke 13 at the default threshold, which was chosen
on held-out training crops rather than those pages. What it breaks is what
any lexicon breaks: proper nouns, classical spellings, an edition's own
spellings -- a word the list does not know but the page really prints.

Using it::

    reader = tetrak_hy.reader()
    words = tetrak_hy.lexicon.load_wordlist("wordlist.tsv")
    tetrak_hy.lexicon.use_lexicon(reader, words)
    reader.readtext("scan.png", decoder="beamsearch")

``decoder="beamsearch"`` is how the probabilities reach this module:
EasyOCR hands them only to its beam-search hook, which ``use_lexicon``
replaces. Without it, ``readtext`` decodes greedily as before.

Pure Python over rows of probabilities, so it runs on numpy arrays at
inference and on plain lists in tests; only out-of-vocabulary words are
beam-searched.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

#: Default acceptance threshold, in natural-log probability: a word-list
#: candidate replaces the greedy reading when it is at most this much less
#: probable. Chosen on 5,530 crops held out from training (exact-match
#: 0.956 -> 0.964); 8 tied on accuracy and broke twice as many crops, and
#: 12 broke almost as many as it fixed.
DEFAULT_TAU = 5.0

#: Beam width per word. Words are short, so a narrow beam holds the n-best.
DEFAULT_BEAM_WIDTH = 16

_ARMENIAN_LETTER = re.compile(r"[Ա-Ֆա-և]")
# Leading and trailing punctuation around a word, kept apart so a
# correction can never drop it. Letters only: U+055A-U+055F (՝ ՛ ՜ ՞) sit
# between the two Armenian letter ranges and are punctuation.
_EDGES = re.compile(r"^([^\wԱ-Ֆա-և]*)(.*?)([^\wԱ-Ֆա-և]*)$", re.S)


def core(word: str) -> str:
    """*word* without leading or trailing punctuation, lower-cased: the look-up key."""
    return _EDGES.match(word).group(2).lower()


def load_wordlist(path: Path | str, min_count: int = 2) -> frozenset[str]:
    """Words from a ``word<TAB>count`` file, keeping those seen *min_count* times.

    A word seen once in a large corpus is as likely a transcription slip as
    a word, so the default drops them.
    """
    words = set()
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            word, _, count = line.rstrip("\n").partition("\t")
            if word and (not count or int(count) >= min_count):
                words.add(core(word))
    return frozenset(words)


class LexiconDecoder:
    """Decode CTC probability matrices, correcting out-of-vocabulary words.

    Args:
        character: The converter's class list, index 0 the CTC blank --
            EasyOCR's ``reader.converter.character``.
        ignore_idx: Class indices never emitted (the blank, plus any
            separators) -- ``reader.converter.ignore_idx``.
        words: The word list, as :func:`load_wordlist` returns it.
        tau: See :data:`DEFAULT_TAU`.
        beam_width: See :data:`DEFAULT_BEAM_WIDTH`.
    """

    def __init__(
        self,
        character: Sequence[str],
        ignore_idx: Iterable[int],
        words: frozenset[str],
        tau: float = DEFAULT_TAU,
        beam_width: int = DEFAULT_BEAM_WIDTH,
    ) -> None:
        self.character = list(character)
        self.ignore = set(ignore_idx) | {0}
        self.space = self.character.index(" ") if " " in self.character else None
        self.words = words
        self.tau = tau
        self.beam_width = beam_width

    def __call__(self, mat, beamWidth: int = 5) -> list[str]:  # noqa: N803 -- EasyOCR's name
        """EasyOCR's ``decode_beamsearch`` signature: a batch of matrices in, texts out."""
        return [self.decode(m) for m in mat]

    def decode(self, mat) -> str:
        """One crop's text: the greedy reading, with out-of-vocabulary words corrected."""
        rows = mat.tolist() if hasattr(mat, "tolist") else [list(row) for row in mat]
        path = [max(range(len(row)), key=row.__getitem__) for row in rows]

        # The greedy text, with the frame span of every word in it.
        pieces: list[tuple[str, int, int] | str] = []  # (word, start, end) or a space
        word, start = "", None
        for t, c in enumerate(path):
            if c in self.ignore or (t > 0 and path[t - 1] == c):
                continue
            if c == self.space:
                if word:
                    pieces.append((word, start, t))
                    word, start = "", None
                pieces.append(" ")
            else:
                if not word:
                    start = self._segment_start(path, t)
                word += self.character[c]
        if word:
            pieces.append((word, start, len(path)))

        out = []
        for piece in pieces:
            if isinstance(piece, str):
                out.append(piece)
            else:
                text, a, b = piece
                out.append(self._correct(text, rows[a:b]))
        return "".join(out)

    def _segment_start(self, path: list[int], t: int) -> int:
        """First frame of the word whose first character is emitted at *t*.

        Blank frames before it belong to the word, back to the previous space.
        """
        while t > 0 and path[t - 1] != self.space and path[t - 1] in self.ignore:
            t -= 1
        return t

    def _correct(self, greedy: str, rows: list[list[float]]) -> str:
        key = core(greedy)
        if len(key) < 2 or not _ARMENIAN_LETTER.search(greedy) or key in self.words:
            return greedy
        candidates = self._beam(rows)
        greedy_logp = next((lp for text, lp in candidates if text == greedy), candidates[0][1])
        edges = _EDGES.match(greedy).group(1, 3)
        for text, logp in candidates:
            # Only the word may change: a candidate that also drops the
            # word's comma or quotation mark is not a correction of it.
            if core(text) in self.words and _EDGES.match(text).group(1, 3) == edges:
                return text if greedy_logp - logp <= self.tau else greedy
        return greedy

    def _beam(self, rows: list[list[float]], prune: float = 1e-3) -> list[tuple[str, float]]:
        """CTC prefix beam search over one word's frames; [(text, log p)], best first."""
        beams: dict[tuple[int, ...], tuple[float, float]] = {(): (1.0, 0.0)}
        log_scale = 0.0
        for row in rows:
            options = [c for c, p in enumerate(row) if p > prune and c not in self.ignore]
            following: dict[tuple[int, ...], list[float]] = defaultdict(lambda: [0.0, 0.0])
            for prefix, (p_blank, p_char) in beams.items():
                total = p_blank + p_char
                following[prefix][0] += total * row[0]
                for c in options:
                    p = row[c]
                    if prefix and prefix[-1] == c:
                        following[prefix][1] += p_char * p
                        following[prefix + (c,)][1] += p_blank * p
                    else:
                        following[prefix + (c,)][1] += total * p
            ranked = sorted(following.items(), key=lambda item: -(item[1][0] + item[1][1]))
            beams = {prefix: (pb, pc) for prefix, (pb, pc) in ranked[: self.beam_width]}
            # Rescaled every frame: a long word's raw probability underflows.
            top = max(pb + pc for pb, pc in beams.values())
            if top > 0:
                beams = {k: (pb / top, pc / top) for k, (pb, pc) in beams.items()}
                log_scale += math.log(top)
        scored = [
            (
                "".join(self.character[c] for c in prefix if c != self.space),
                log_scale + math.log(max(pb + pc, 1e-300)),
            )
            for prefix, (pb, pc) in beams.items()
        ]
        return sorted(scored, key=lambda item: -item[1])


def use_lexicon(reader, words: frozenset[str], tau: float = DEFAULT_TAU) -> LexiconDecoder:
    """Make *reader* correct out-of-vocabulary words when called with ``decoder="beamsearch"``.

    Replaces the reader's beam-search hook with a :class:`LexiconDecoder`
    built from its own converter, and returns it.
    """
    converter = reader.converter
    decoder = LexiconDecoder(converter.character, converter.ignore_idx, words, tau=tau)
    converter.decode_beamsearch = decoder
    return decoder
