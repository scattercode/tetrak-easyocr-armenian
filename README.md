# tetrak-easyocr-armenian

Armenian language support for [EasyOCR](https://github.com/JaidedAI/EasyOCR)
— a trained recognition model, installable as a custom network.

> **Status: pre-release.** The packaging and loading path are complete and
> tested; the first trained weights have not shipped yet. Until they do,
> `reader()` raises a clear error unless you pass your own
> `weights_path=`. Watch the
> [releases](https://github.com/scattercode/tetrak-easyocr-armenian/releases).

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
[tetrak-hy-trainer](https://github.com/scattercode/tetrak-hy-trainer) —
synthetic Armenian text rendered in period fonts, fine-tuned on
human-proofread scans of the Armenian Soviet Encyclopedia from
[Armenian Wikisource](https://hy.wikisource.org/) (CC BY-SA 3.0). Every
weights release carries its provenance record: data recipe, fonts, crop
counts, training config and checksums.

Built for [Tetrak](https://tetrak.dev/), a local-first transcription
pipeline for archival material, which consumes this package as its
`easyocr-hy` backend — but nothing here depends on Tetrak.

## Licence

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). The
architecture re-exported here is EasyOCR's (Apache 2.0).

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

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow — checks,
the dependency lockfile, and what the automation expects — and
[SECURITY.md](SECURITY.md) for how to report a vulnerability.
