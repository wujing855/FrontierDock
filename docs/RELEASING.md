# Releasing

Prepare a fresh public repository from this source directory, not from a private workbench checkout or its Git history. Never add a personal workspace to the release.

```sh
python3 -m unittest discover -s tests -v
node --test tests/ui.test.mjs
python3 scripts/release.py --check
python3 scripts/release.py --output ../FrontierDock-source.zip
```

The builder accepts only known source directories, file types and top-level documentation. It excludes databases, credentials, workspace files, logs, caches, local dependencies and Git history. It refuses symlinks in source and scans text for likely credentials and private machine paths. An optional private `--deny-file` adds exact identifiers to check; do not include that file in the repository.

Inspect the archive inventory, hashes, licensing and any screenshots. Test the extracted archive in a new directory, including a fresh blank workspace and fictional demo. A passing check does not verify external API access or provider free quota.

Before GitHub publication, verify the intended account and repository with the owner. Do not reuse an unrelated repository or overwrite its history. Review staged files, and publish only after receiving the owner's authorization to commit and push. Keep private handoff notes and protection-baseline reports outside the public tree.
