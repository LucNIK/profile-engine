<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 John Luke NIKABOU (LucNIK) -->

# Security policy

## Supported versions

Only the latest `v1` release receives security fixes.

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/LucNIK/profile-engine/security/advisories/new),
not in a public issue. You will get an answer within 72 hours.

## Design principles

- Issue titles and player names written by visitors are parsed with strict patterns and never reach a shell:
  every action input is passed through environment variables.
- The engine only uses the workflow's own short-lived `GITHUB_TOKEN`; it never stores or prints it.
- Rendered SVGs embed their fonts and load no external resource.
