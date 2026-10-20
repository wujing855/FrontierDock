# Contributing

Keep the base application usable without an API account or a front-end build. Start from a fictional demo or a temporary empty workspace; do not commit real research data.

Discuss a change when it affects data ownership, source verification, public exposure or a major workflow. Routine fixes can be developed and verified directly. Users can personalize their own copy freely; the setup skill should preserve their choices.

Run Python tests, Node UI tests and the release checker. For UI changes, check journal-to-issue navigation, search, reading-state persistence and yearly statistics in a real browser. For provider changes, use mocked responses in CI and identify any account-dependent live checks separately.

Use minimal, redacted reproductions for issues. Do not request another user's full workspace, keys, provider login configuration or paper library. Keep KaTeX's original notice when changing vendored assets.
