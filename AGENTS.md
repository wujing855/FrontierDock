# FrontierDock contributor guidance

Read README.md and docs/DATA_CONTRACT.md before changing behavior. Keep work focused and preserve local user edits. Use independent temporary workspaces for tests.

Never inspect or import credentials or data from another application. Runtime workspaces, keys, accounts, scholarly documents, reading states, logs and local paths must stay out of source, screenshots, Git history and release archives. Run scripts/release.py --check before packaging or publishing.

For first-run assistance, read skills/frontierdock-setup/SKILL.md. Offer progressive choices; users control journals, sources, translations, schedule and interface. Do not hardcode a discipline, journal catalogue, model vendor, developer account, filesystem root or launch service.

Research integrity is part of application behavior. Search summaries are clues. Original abstracts need source identity checks. Do not invent dates or issue numbers. Keep existing records on identity conflicts. Fingerprint all derived text against its original title/abstract. Partial retrieval must remain visibly partial.

Validate changes with standard-library tests and the Node UI tests. Check real browser behavior for interface changes. Optional integration mock tests do not prove account access, free quota or cloud extraction works. Keep these limitations explicit.

Publishing, global installation, scheduling, cloud uploads and paid provider calls require the user's relevant authorization. Routine reversible local fixes within an authorized task can proceed without repeated approval. Do not auto-submit diagnostics or user data to external trackers.
