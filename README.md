# tetrak-easyocr-armenian

Armenian language support for [EasyOCR](https://github.com/JaidedAI/EasyOCR)
— a trained recognition model, installable as a custom network.

> **Status: alpha, shipping v6 weights and a word list.** `reader()`
> downloads a trained model and works out of the box. v6 is v5 fine-tuned
> on 99,521 real crops cut from the scans of sixteen works: an encyclopedia,
> a medical encyclopedia, a bilingual dictionary, a scholarly history and
> literary editions in both dialects. With `fold_script()` and the word
> list, it leads every Armenian engine we have measured on word recall on
> three of eight held-out registers, and is within a thousandth on a
> fourth. The numbers, and the registers it still trails on, are on the
> [model card](https://huggingface.co/tetrak/easyocr-armenian).
>
> Figures published for v5 and earlier used a character-similarity metric
> later found to be wrong (difflib's `autojunk`) and are not comparable
> with v6's.
>
> **Upgrading from v0 or v1?** Do. Both were trained with 21% of their
> labels carrying quotation marks the images do not show, and with no
> class for the abbreviation dot `․` (U+2024) at all. The model card
> records both.

## Usage

```bash
pip install tetrak-easyocr-armenian
```

```python
import tetrak_hy

reader = tetrak_hy.reader()          # an easyocr.Reader, Armenian-ready
results = reader.readtext("scan.png")
```

`reader()` accepts everything `easyocr.Reader` does (`gpu=`, `verbose=`,
…) and handles the custom-network plumbing: the network config and weights
are materialised into `~/.tetrak_hy/` on first use, and the quirks of
EasyOCR's custom-model loading path (there are a few) stay our problem
rather than yours.

The weights live in the
[Hugging Face model repository](https://huggingface.co/tetrak/easyocr-armenian),
which is canonical for them, and each library version pins one immutable
Hub revision — so the model you get is decided by the version of this
package you installed, never by what happens to be current upstream.

Cached weights are verified against the release's SHA-256 every time they
are loaded, not only when they are downloaded. A file that matches is used
as it is — so a machine with no outbound access works once the weights are
in place — and one that does not, because it was corrupted or because you
have upgraded to a release carrying a new model, is replaced by a fresh
verified download.

Set `TETRAK_HY_HOME` to put the cache somewhere other than your home
directory, or choose it per call:

```python
reader = tetrak_hy.reader(cache_dir="/srv/models/tetrak_hy")
```

A local `.pth` passed as `weights_path=` is kept in a `local/`
subdirectory of the cache, so testing your own weights does not disturb
the released ones.

## Folding cross-script homoglyphs

The recognition network has no language model, so inside an Armenian word
it sometimes emits the visually identical Latin twin of an Armenian
character instead — Latin `h` for `հ`, a colon for the Armenian full stop
`։`. `fold_script()` corrects these on already-recognised text, and is
worth applying to every result:

```python
results = [
    (bbox, tetrak_hy.fold_script(text), confidence)
    for bbox, text, confidence in reader.readtext("scan.png")
]
```

It only touches a token that already contains an Armenian letter, so
Latin or Cyrillic text sharing a page is left alone. See the function's
docstring for the exact scope and what it deliberately does not fold.

## Correcting words with the word list

The network reads one character at a time, so a word it misreads by one
letter comes out as written, even when the right word was its own second
choice. `reader(lexicon=True)` downloads the released word list (1.1
million Armenian word forms, verified and cached like the weights) and
corrects out-of-vocabulary words from the model's own alternatives:

```python
reader = tetrak_hy.reader(lexicon=True)
results = [
    (bbox, tetrak_hy.fold_script(text), confidence)
    for bbox, text, confidence in reader.readtext("scan.png", decoder="beamsearch")
]
```

`decoder="beamsearch"` is how the model's probabilities reach the
correction; greedy calls are unchanged. A word is only replaced by a listed
reading the model itself found nearly as probable, and keeps its
punctuation. What it can break is what any word list breaks: proper nouns,
and classical or edition spellings the list does not know. On held-out
pages it fixed 465 words for every 13 it broke. To use your own list, pass
it to `tetrak_hy.lexicon.use_lexicon(reader, tetrak_hy.lexicon.load_wordlist(path))`.

## What it is

EasyOCR does not ship Armenian. This package adds it as a
[custom recognition network](https://github.com/JaidedAI/EasyOCR/blob/master/custom_model.md):
EasyOCR's own generation2 architecture (VGG + BiLSTM + CTC), trained for
the Armenian script — the full alphabet, the և ligature, Armenian
punctuation (՝ ՛ ՞ ՜ ։ ֊ « »), digits and basic Latin for mixed material.
Detection is untouched: EasyOCR's CRAFT detector already finds Armenian
text; reading it is what was missing.

The import name `tetrak_hy` is also the EasyOCR network name — EasyOCR
imports this package directly as the model architecture. If you prefer to
wire the `Reader` yourself:

```python
import easyocr

reader = easyocr.Reader(
    ["en"],                       # see note below
    recog_network="tetrak_hy",
    user_network_directory="~/.tetrak_hy",
    model_storage_directory="~/.tetrak_hy",
)
```

(`["en"]`, not `["hy"]`: EasyOCR looks up a per-language character file it
does not have for Armenian. The setting is decorative for custom models —
the model's own character list governs decoding — and `reader()` hides
this entirely.)

## Provenance

The model is trained by
[tetrak-hy-trainer](https://github.com/scattercode/tetrak-hy-trainer) on
synthetic line crops: text from human-proofread pages on
[Armenian Wikisource](https://hy.wikisource.org/) (CC BY-SA 3.0) —
eleven volumes of the Armenian Soviet Encyclopedia plus the collected
works of Otyan, Totovents, Baronian and Tumanyan, Faustus of Byzantium,
a popular medical encyclopedia and an Armenian–English dictionary —
rendered in fifteen Armenian faces at real scan sizes and degraded to
look scanned. v5 added a fine-tune on real crops cut from human-proofread
scans and labelled from their transcripts, mixed with the synthetic set
so the model adapts to real print without forgetting the breadth it
started with. **v6 continues that fine-tune on 99,521 real crops from
862 scans of sixteen sources**, including more volumes of the editions
v5 read least well. The widened
corpus is what taught it both dialects and several registers rather
than one encyclopedia's typography; the real-crop fine-tune is what
closed the gap on degraded letterpress that a cleanly rendered font
cannot teach.

The word list counts words in the same proofread transcripts, with the
evaluation pages excluded, and adds every word form of the
[Nayiri Armenian Lexicon](http://www.nayiri.com/nayiri-armenian-lexicon)
(© Serouj Ourishian, CC BY 4.0). It is published beside the weights as
`wordlist.tsv.gz`, under CC BY-SA 4.0 because of those sources, and is
downloaded only when `reader(lexicon=True)` or `wordlist()` asks for it.

Every weights release carries a provenance record — data recipe, fonts,
dataset revision, training config and checksums — published as
`provenance.json` beside the weights. The training data is published
too, as
[tetrak/armenian-ocr-crops](https://huggingface.co/datasets/tetrak/armenian-ocr-crops).

Built for [Tetrak](https://tetrak.dev/), a local-first transcription
pipeline for archival material, which consumes this package as its
`easyocr-hy` backend — but nothing here depends on Tetrak.

## Licence

Apache License 2.0 — see
[LICENSE](https://github.com/scattercode/tetrak-easyocr-armenian/blob/main/LICENSE)
and
[NOTICE](https://github.com/scattercode/tetrak-easyocr-armenian/blob/main/NOTICE).
The architecture re-exported here is EasyOCR's (Apache 2.0). The word list the package downloads on request is CC BY-SA 4.0, not
Apache 2.0; see above.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check src tests && ruff format --check src tests
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org/),
enforced by the hook in `.githooks/` (`git config core.hooksPath .githooks`
after cloning, or `lefthook install`). Releases and `CHANGELOG.md` are
generated from those commits automatically on every push to `main`.

See
[CONTRIBUTING.md](https://github.com/scattercode/tetrak-easyocr-armenian/blob/main/CONTRIBUTING.md)
for the full workflow — checks, the dependency lockfile, and what the
automation expects — and
[SECURITY.md](https://github.com/scattercode/tetrak-easyocr-armenian/blob/main/SECURITY.md)
for how to report a vulnerability.
