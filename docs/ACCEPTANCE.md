# Initial source-release acceptance

Version 0.1.0 was checked in an isolated local workspace on macOS. No account credentials or real research records are required for these checks.

- 51 standard-library Python tests passed, including protected initialization, DOI conflicts, abstract provenance, stale source fingerprints, reading revisions, due checks, request budgets, a local compatible-API HTTP round trip, explicit cloud-upload consent, local-host API restrictions and release exclusions.
- 7 Node UI logic checks passed, covering escaping, dynamic years, incomplete issue labels, configurable timezone, reading filters, recent-paper ordering and journal details placement.
- The setup skill's frontmatter and structure passed its validator.
- Real-browser checks covered home, journal cards, issue directory, per-issue paper list, translated-title search, original/translated abstract display, reading save/remove/restore and single-year keyword statistics.
- One public Crossref journal request returned a DOI-backed record and an explicit partial-window warning. This is a connectivity/adapter check, not a completeness audit of any journal.
- The release builder scanned the selected public files for likely credentials and private machine paths, and excluded runtime databases, local configuration, logs, backups, user data and Git history.

Compatible model and MinerU behavior is covered by synthetic/mocked integration checks; no live paid account call or actual cloud PDF extraction is claimed. Account quotas, model quality, provider changes and external scheduler setup require verification by the eventual user's Agent. Linux CI is configured; a passing remote CI run is not claimed before repository publication.
