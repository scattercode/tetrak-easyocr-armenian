# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/scattercode/tetrak-easyocr-armenian/security/advisories/new)
(Security tab → "Report a vulnerability"). Do not open a public issue for a
security problem.

We aim to acknowledge reports within seven days. This is a small
collaborative project, not a company with a security team — but we take
reports seriously and will keep you informed as we investigate.

## Supported versions

Only the latest release receives fixes. There are no maintenance branches.

## Weights integrity

A `.pth` file is a pickle, and loading an untrusted one executes code. This
package therefore downloads weights only from its own GitHub Releases and
verifies them against a pinned SHA-256 checksum before use — a failed
checksum refuses installation rather than warning. If you fetch weights by
hand, verify the checksum published in the release notes yourself.

## What we do ourselves

- The full resolved dependency tree is pinned in `uv.lock` and scanned by
  Trivy on every push and weekly on a schedule; Dependabot keeps the lock
  and the workflow actions current.
- Every weights release ships with a provenance record: data recipe, fonts,
  crop counts, training config and git SHAs.
