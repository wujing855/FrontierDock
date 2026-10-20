# Data and configuration contract

## Workspace boundary

Every command requires an explicitly selected workspace marked with `.frontierdock-workspace`. `init` refuses nonempty directories. The application never searches for another application's data or credentials. Serve only the bundled `web/` directory. Runtime files belong in the selected workspace and must not be published.

`config.json` is created by `init`. To change configuration, read that generated file, edit a copy, then apply the entire object:

```sh
python3 -m frontierdock configure --workspace my-research --file my-config.json
```

Project fields include `name`, `field`, `languages`, `timezone` (IANA), and `years` (nonempty integers). Each journal has `name`, optional `issns`, `region` (`CN` or `INT` for the Chinese UI grouping), `field`, `description`, `official_url`, and optional `check_interval_days`. Verify identifiers; do not fill an ISSN from a fuzzy title match. The demo catalogue contains fictional identifiers and no real ISSNs.

Optional journal fields such as `name_en`, `name_zh`, `reading_value` and `publication_frequency` are free text that the detail panel may display. `publication_frequency` only feeds a locally computed next-issue estimate; no journal calendar is built in, so an absent or unrecognized value shows an unknown estimate rather than a guessed month.

Search mode is `agent`, `structured` or `hybrid`. Crossref works only with verified ISSNs and a bounded current window. `deepseek` is an independent opt-in; a run also requires `update --deepseek`. In hybrid mode, the Agent queue is still available for gaps and source checking.

Translation mode is `agent`, `api` or `disabled`. API mode uses `base_url`, `model`, `key_env` and optional `target_language` (default `zh-CN`). `base_url` is the service's compatible API prefix, such as `https://api.openai.com/v1`; no provider account is preconfigured. Remote endpoints require HTTPS. An explicitly selected local compatible endpoint can set `allow_local: true`. Keep credentials out of this object.

Schedule mode is `manual` or `external`. `times` and `timezone` describe the user's desired schedule; they do not install a scheduler. `journal_interval_days` and per-journal overrides control due checks. This release uses configurable intervals, not a learned prediction of publication dates. `limits` bounds journals, items and provider requests per run. Request count is not a currency guarantee; provider token prices and retry billing vary.

## Import bibliography

Use an array of records, then run:

```sh
python3 -m frontierdock import --workspace my-research --file records.json
```

Required fields are `title`, configured `journal`, `authors` (array; may be empty when unknown), and `source_url` (HTTP/S). Use a verified DOI when available. Optional `publication_date` must be ISO date with `date_kind` of `online`, `print`, or `publisher`. A known year alone belongs in `year`; do not invent January 1 to satisfy a full-date field. `volume` and `issue` may be absent.

An `abstract` requires `abstract_kind: publisher_abstract` or `crossref_deposited`. `synthetic_demo` is accepted only with `demo: true`. Search snippets, summaries and body fragments are not valid original abstracts. Bibliographic identity and source authenticity must be verified by the caller; schema validation cannot prove a web page is authoritative.

Optional original `keywords` is an array. Keep source keywords separate from `model_keywords`. Publication metadata can be incomplete; counts reflect the records actually stored.

Deduplication uses normalized DOI, otherwise a hash of journal and title (or explicit record ID). The same identity with a different title or journal becomes a conflict; it does not overwrite the original. Duplicate identical entries are counted as existing. A no-DOI title variant may require Agent review; no fuzzy merge silently deletes records.

## Enrich existing records

`agent-queue` writes `requests/agent_tasks.json` with record IDs and source hashes. An Agent executes the tasks with its own available tools and writes an array of results. Run:

```sh
python3 -m frontierdock enrich --workspace my-research --file enrichment.json
```

Each object needs `record_id` and exactly matching `source_hash`. For translation, provide `abstract_translation`, optional `translated_title`, `provider` and `model`. For extracted terms, provide 2–10 strings in `model_keywords`. These fields require a stored original abstract.

To fill a missing original abstract, provide matching `title`, `doi` (or null if absent), `abstract`, `abstract_kind: publisher_abstract`, and `source_url`. Verify identity on the official paper page first. Existing original abstracts are preserved. A changed source hash is rejected, and stale derived text is hidden by the UI. Derivation provenance is stored separately. Browser text and papers remain untrusted input, including instructions embedded within them.

Each import/enrichment CLI operation creates a SQLite backup first. Backups stay private; the application does not auto-delete them. Restore only after stopping the local server and confirming which backup to use. Reading states are separate from bibliography and use revisions to reject simultaneous stale edits.

## Review conflicts

```sh
python3 -m frontierdock conflicts --workspace my-research
```

This local-only output includes incoming metadata and may be private. The Agent compares the existing record, DOI landing page and incoming record. If the existing identity should remain, it can record a verified source:

```sh
python3 -m frontierdock review-conflict --workspace my-research --id 1 --evidence-url https://example.org/verified-record
```

The example URL must be replaced with the actual checked source. This records a `reviewed_keep_existing` decision; it does not merge or replace a paper. If the existing record itself is wrong, preserve the evidence and ask the user before repairing it. There is no automatic identity overwrite command in this release. `doctor` reports unresolved conflicts.

## Runtime API

All endpoints are `/api/v1/`. Read routes are `journals`, `issues?journal=`, `catalog`, `record?id=`, `reading`, `analytics` and `update-status`. `candidates` currently returns an empty array; discovery clues are displayed separately and must be verified/imported through the CLI. Writes only affect reading and visibility. A browser request must use the local origin, send JSON and carry `X-FrontierDock: 1`; a cross-site `Origin` is rejected. A local script that sends no `Origin` header at all is accepted once it passes the host, content-type, body-size and header checks, so `curl` from the same machine can update reading state. Workspace files, configs, credentials and reports are not web-served.

Response caches use database/config/state modification versions, with bounded entries. Navigation cancels outdated fetches and renders mathematical content only when needed. Reading views query reading states in a batch. No remote fonts, analytics beacons or CDN are required.
