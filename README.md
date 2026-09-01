# tetrak-easyocr-armenian

Armenian language support for [EasyOCR](https://github.com/JaidedAI/EasyOCR)
— a trained recognition model, installable as a custom network.

> **Status: alpha, shipping v3 weights.** `reader()` downloads a trained
> model and works out of the box. v3 is v2 fine-tuned on real crops cut
> from scanned pages, and with `fold_script()` it reads **0.771 word
> recall on real scans — ahead of `tesseract -l hye` at 0.662 and of
> Marker at 0.766, and two points behind Calfa's `hye-calfa-n` at
> 0.789.** Calfa's model, measured on the same pages, is the strongest
> Armenian OCR here; it is CC BY-NC 4.0. This one is the strongest
> **permissively licensed** reader of the script measured on this
> material. The model on its own reads 0.736, so apply the fold (one
> line, below). Character similarity is a separate and much weaker
> story, because on two-column pages that metric measures reading order
> more than recognition. The numbers are on the
> [model card](https://huggingface.co/tetrak/easyocr-armenian).
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
synthetic line crops: text from human-proofread pages of the Armenian
Soviet Encyclopedia on
[Armenian Wikisource](https://hy.wikisource.org/) (CC BY-SA 3.0),
rendered in Armenian faces at real scan sizes and degraded to look
scanned. v2 was trained on that synthetic data alone; **v3 adds a
fine-tune on 6,097 real crops** cut from 30 human-proofread scans and
labelled from their transcripts, mixed with the synthetic set so the
model adapts to real print without forgetting the breadth it started
with. That is what closed the gap: it targets the shape confusions on
degraded letterpress that a cleanly rendered font cannot teach.

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
The architecture re-exported here is EasyOCR's (Apache 2.0).

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
