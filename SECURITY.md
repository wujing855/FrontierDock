# Security and disclosure

This release is a local, single-user application. The server binds only to loopback; it is not designed for public hosting or shared accounts. Do not remove the host/origin checks or expose its port without adding and reviewing authentication and deployment controls.

Never post credentials, signed upload/download links, workspaces, private papers or raw account diagnostics in public issues. If a secret is exposed, revoke it at its provider and remove it from future releases; removing a working-tree file alone does not remove Git history.

An Agent should first reproduce defects using synthetic data. Report the affected version, minimal steps and redacted error code. Ask the maintainer for a private reporting channel before transmitting sensitive details; no private contact address is invented by this project.

The release checker is an accidental-disclosure guard, not a proof of complete security. Review source, archive contents and staged Git files before publishing.
