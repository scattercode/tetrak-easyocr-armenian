# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

