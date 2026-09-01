# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

