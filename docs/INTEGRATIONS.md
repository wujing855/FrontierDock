# Optional integrations and verification status

Basic browsing, import, enrichment, reading state, quality reports and the Agent queue work without external services. The initial release includes provider adapters, not a guarantee that every account, website or model will work.

| Path | This release | Remaining live verification |
|---|---|---|
| Agent search / translation | Structured task queue plus validated import/enrichment | The user's Agent must have the necessary tools and execute the queue |
| Crossref | Verified-ISSN retrieval, bounded window, deposited abstract parsing | One public journal request verified during preparation; each user’s journals still need live completeness checks |
| DeepSeek | Opt-in Search clues and Fetch page storage | User account, balance, access and page parsing; Search never auto-imports papers |
| Compatible model API | Per-record original abstract translation and keyword extraction, source fingerprint, per-run request limit | User-selected endpoint, model support, translation quality, pricing/quota |
| MinerU local | Explicit command-array runner, no shell, local result folder | An existing compatible MinerU installation |
| MinerU cloud | Explicit PDF upload opt-in, task submission, separate status/download command | User token, account limits, network, actual PDF output quality |
| External scheduling | Due plan and run limits | The user's selected scheduler and Agent runner; no automatic installation |

## Credentials

Use the interactive `key set` command or these environment variables:

| Provider | Environment variable | Local key file name |
|---|---|---|
| Compatible text model | `FRONTIERDOCK_LLM_KEY` (configurable via `key_env`) | `llm.key` |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek.key` |
| MinerU | `MINERU_API_KEY` | `mineru.key` |

The local secret folder is `$XDG_CONFIG_HOME/frontierdock/secrets` or the user's `.config/frontierdock/secrets`. Files require owner-only permissions. Provider responses, authentication headers and signed upload URLs are not printed by the adapters. Keys are never delivered to the browser.

## Free-model selection

Free quota and expiration are account-specific. A model list, a successful inference, or a generic coupon cannot establish that the next call is free. No account-specific CLI, login session or preselected model is included in this repository.

For API mode with `translation.free_only: true`, supply a private `free-model-inventory.json` in the workspace. Each entry uses this shape, with the user's actual verified values:

```json
{
  "model": "provider-model-code",
  "expires_at": "2099-01-01",
  "remaining_tokens": 100000,
  "stop_when_exhausted": true,
  "free_confirmed": true,
  "text_generation": true,
  "quality_rank": 90,
  "checked_at": "2098-12-31T12:00:00+00:00"
}
```

The file is an array of entries; the dates above are illustrative, not live quota. The Agent should obtain current quota using an official provider interface available to that user, or a user-confirmed console reading. Inventory older than 24 hours is rejected. Expired, empty, non-text and unconfirmed entries are filtered out. Candidates sort by earliest expiration date, then highest task-specific quality rank, then model code. Quota rejections can advance to the next candidate within the per-run call limit; network/authentication failures stop the run. No paid model is selected outside this inventory in free-only mode.

The user must enable and verify provider-side stop-on-exhaustion protection. Local inventory cannot enforce a provider's billing rules or guarantee its counters are real-time. Quality ranks are judgments supplied by the Agent/user, not benchmarks measured by this program. Refresh quota before a batch; do not assume a new month grants every model a new allocation.

## PDF extraction

PDF parsing is optional and has no full-text annotation UI. Configure `pdf.mode` as `local` or `cloud`. This application's conservative file-size cap is 20 MB, independent of the provider's published limits.

```sh
python3 -m frontierdock pdf --workspace my-research --file paper.pdf
```

Cloud mode additionally requires `--allow-cloud`, which authorizes sending that selected PDF to MinerU. It returns an extraction ID; poll explicitly with `pdf-status --id ID`. The adapter writes Markdown to `extractions/`, never auto-imports extracted text as an Abstract, and does not unpack remote archive paths into the filesystem. Original-page checks remain necessary for formulas, tables, OCR and quotations.

## Official references

- [DeepSeek Search reference](https://api-docs.deepseek.com/api/search/) and [Search/Fetch guide](https://api-docs.deepseek.com/guides/search/).
- [Crossref REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) and [filter documentation](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/).
- [MinerU API documentation](https://mineru.net/doc/docs/index_en/).

Provider APIs change. Recheck the relevant official documentation when an adapter fails; do not silently bypass access restrictions or account limits.
