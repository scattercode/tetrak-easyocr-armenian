# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.0] - 2026-11-18

### Changed

- V8 weights, v7 fine-tuned on books set in italics (#32)

## [0.12.0] - 2026-11-16

### Changed

- V7 weights, both orthographies and Cyrillic, with two word lists (#31)

## [0.11.0] - 2026-11-15

### Changed

- Decide a token's script three ways and keep եւ and և as set (#30)

## [0.10.0] - 2026-11-15

### Changed

- Bump ruff from 0.17.3 to 0.17.4 (#28)
- Decode against the modern and classical lists together (#29)

## [0.9.0] - 2026-11-15

### Changed

- Bump ruff from 0.16.5 to 0.16.8 (#11)
- Bump actions/download-artifact from 7 to 8 (#9)
- Cover the word list and the public Hub in CLAUDE.md and the release skill (#13)
- Bump ruff from 0.16.8 to 0.16.9 (#14)
- Move the house rules to AGENTS.md for any coding agent (#15)
- Bump ruff from 0.16.9 to 0.16.10 (#16)
- Move the lock past the pillow, filelock and certifi advisories (#23)
- Bump setuptools from 84.0.0 to 84.1.0 (#21)
- Bump ruff from 0.16.10 to 0.17.2 (#22)
- Bump pytest from 9.1.1 to 9.2.0 (#25)
- Bump ruff from 0.17.2 to 0.17.3 (#24)
- Grant permissions per job and pass the branch through env (#26)
- Read a Latin-or-Cyrillic token in the one script it belongs to (#27)

## [0.8.0] - 2026-10-03

### Changed

- V6 weights and lexicon-aided decoding (#12)

## [0.7.0] - 2026-09-04

### Changed

- Ship the v5 weights -- both dialects, eight registers, new charset (#8)

## [0.6.0] - 2026-09-03

### Changed

- V3 is the strongest permissively licensed reader, not the strongest
- Correct the fold description and point at the release skill
- Take the version computation from the shared release pipeline
- Run the pre-push suite through the project's own interpreter
- Ship the v5 weights -- both dialects, eight registers, new charset (#7)

## [0.5.0] - 2026-09-01

### Changed

- Ship the v3 weights, the real-crop fine-tune

## [0.4.1] - 2026-09-01

### Fixed

- Register the easyocr stand-in before collection, not only in a fixture

## [0.4.0] - 2026-09-01

### Changed

- Mirror the released weights onto the GitHub Release
- Fold cross-script homoglyphs onto Armenian in recognised text
- Ship the v2 weights, first release to pass tesseract -l hye

### Fixed

- Stop folding en/em dash in fold_script, measured net harmful

## [0.3.0] - 2026-08-31

### Changed

- Download the v1 weights from the Hugging Face model repository

## [0.2.0] - 2026-08-30

### Added

- Add manual TestPyPI dry-run workflow (#5)

### Changed

- Publish wheels to PyPI via Trusted Publisher (#6)

## [0.1.2] - 2026-08-30

### Changed

- Bump actions/checkout from 4 to 7 (#1)
- Bump actions/upload-artifact from 4 to 7 (#2)
- Bump actions/setup-python from 5 to 7 (#3)

### Fixed

- Verify cached weights on every load, and allow relocating the cache (#4)

## [0.1.1] - 2026-08-30

### Fixed

- Raise the Python floor to 3.10 so the lock resolves patched releases

## [0.1.0] - 2026-08-30

### Added

- Add contributing and security policies

### Changed

- Scaffold the library -- package-as-network loading, no weights yet
- Derive the package version from the git tag via hatch-vcs
- Pin the full dependency tree in uv.lock
- Automate releases and the changelog from the commit history
- Scan dependencies with Trivy and keep them current with Dependabot

