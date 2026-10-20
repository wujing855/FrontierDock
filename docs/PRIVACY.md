# Privacy and local data

FrontierDock serves only its static UI and a small local API. It binds to loopback and has no built-in telemetry, account login, remote fonts or CDN. This is a single-user local application, not an authenticated multi-user service. Do not expose its port publicly or through a tunnel without implementing and reviewing appropriate access controls.

Workspaces contain potentially private journal preferences, bibliographies, reading history, conflicts, prompts, model-derived text and local reports. Keep the entire workspace private. The default `.gitignore` is a precaution; a differently named workspace still must not be committed. Use the release builder, which selects only known source directories and file types.

Keys belong outside the source/workspace, in user-level owner-only files or environment variables. Do not share the secret folder, command environment, provider account configuration, terminal screenshots containing credentials, browser state or application login sessions.

Outgoing traffic occurs only when a user/Agent selects and runs integrations. Crossref receives journal identifiers and date queries. DeepSeek receives the submitted search query or target URL. A configured text API receives the paper title, original abstract and derivation instructions. MinerU cloud receives only a specifically selected PDF after cloud upload is explicitly allowed. Reading state is not sent by these adapters. External providers apply their own privacy, retention and billing rules.

A public demo must use fictional, clearly labelled records. Do not reuse screenshots of a personal workbench. Software licensing does not grant permission to redistribute third-party papers, abstracts, translated text or paid content.

The source release is prepared from an explicit allowlist and checked for credentials, private paths and runtime files. This reduces accidental disclosure; it does not justify adding personal files to the repository later. Inspect the archive contents and staged Git diff before every public upload. Publish a fresh repository history containing only the public source.
