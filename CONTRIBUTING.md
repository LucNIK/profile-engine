<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 John Luke NIKABOU (LucNIK) -->

# Contributing

## Commit policy (business rules)

| Rule | What it requires |
| --- | --- |
| R1 — Maintainer commits | Every commit on `main` is written and signed by the maintainer, `LucNIK <lukepulanka@gmail.com>`. |
| R2 — Single author | Commit messages carry no co-author or tool trailers. |
| R3 — Signed | Every commit and tag is signed (SSH) and shows **Verified**. `main` requires signed commits. |
| R4 — Patches, not pushes | Changes prepared elsewhere arrive as patches and are applied with `git am` on the maintainer's machine, where they are signed. |
| R5 — Fixed history | No force push and no deletion on `main`. |
| R6 — Copyright | Every source file starts with the copyright and SPDX header. |
| R7 — Security | Untrusted input never reaches a shell; no secret is ever committed. |
| R8 — Versions | `vX.Y.Z` signed tags, the `v1` tag moved to the latest release, a changelog entry and a Marketplace release for each version. |
| R9 — Quality | `python -m unittest` is green before any tag. |

R1 and R2 are enforced locally by the hooks in `.githooks/`. Enable them once per clone:

```bash
git config core.hooksPath .githooks
```

## Development

```bash
python -m profile_engine --config examples/profile.toml --out dist --offline   # sample data, no network
python -m unittest -v
```

The engine uses the Python standard library only. Keep it that way.
