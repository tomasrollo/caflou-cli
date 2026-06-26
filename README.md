# caflou-cli

A command-line interface for [Caflou](https://www.caflou.com) API. Designed for scripting, AI agents, and quick terminal access to your Caflou data.

## Installation

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv tool install git+https://github.com/tomasrollo/caflou-cli
```

Or for local development:

```bash
git clone https://github.com/tomasrollo/caflou-cli
cd caflou-cli
uv sync
uv run caflou --help
```

## Authentication

```bash
caflou auth login
```

You will be prompted for your email and password. The CLI stores a JWT token in `~/.config/caflou-cli/config.json` (valid for 7 days). Credentials can also be provided via environment variables:

| Variable          | Purpose                          |
|-------------------|----------------------------------|
| `CAFLOU_EMAIL`    | Login email (also `CAFLOU_USERNAME`) |
| `CAFLOU_PASSWORD` | Login password                   |
| `CAFLOU_TOKEN`    | Pre-existing Bearer token        |
| `CAFLOU_ACCOUNT_ID` | Account ID override            |

If you have access to multiple Caflou accounts, you are prompted to select a default at login. Use `--account` on any command to switch accounts at runtime (accepts account ID or a substring of the account name).

```bash
caflou auth whoami          # show current auth status and available accounts
```

## Command groups

### `auth` — Authentication

```bash
caflou auth login           # authenticate and store token
caflou auth whoami          # show token status and account list
```

### `company` — Companies

```bash
caflou company list         # list companies (paginated)
caflou company get <id>     # get full company details
```

### `contact` — Contacts

```bash
caflou contact list
caflou contact get <id>
```

### `invoice` — Invoices

```bash
caflou invoice list
caflou invoice get <id>
```

### `project` — Projects

```bash
caflou project list
caflou project get <id>
```

### `task` — Tasks

```bash
caflou task list
caflou task get <id>
```

### `timesheet` — Timesheet entries

```bash
caflou timesheet list
caflou timesheet get <id>
```

### `transfer` — Cash flow transfers

```bash
caflou transfer list
caflou transfer get <id>
```

### `masterdata` — Local master data cache

Master data (VAT rates, statuses, categories, etc.) is cached locally per account and used for ID lookups when creating records.

```bash
caflou masterdata sync              # sync all 29 master data types from the API
caflou masterdata sync vat_rates    # sync a single type
caflou masterdata list vat_rates    # show cached records for a type
caflou masterdata status            # overview: all types, record counts, last sync time
caflou masterdata clear             # delete all cached master data for the current account
caflou masterdata clear vat_rates   # delete a single type's cache
```

The cache lives at `~/.config/caflou-cli/cache/{account_id}/{type}.json`. A warning is printed if a cache file is more than 7 days old.

## Global flags

All list/get commands accept these flags:

| Flag | Description |
|------|-------------|
| `--account <id-or-name>` | Override the default account |
| `--json` | Output raw JSON instead of formatted tables |
| `--page <n>` | Page number (default: 1) |
| `--per <n>` | Items per page (default: 20, max: 1000) |
| `--all` | Fetch all pages (warns if total exceeds 500) |
| `--filter key=value` | Filter results (repeatable) |

## Filtering

Use `--filter` to pass Caflou API filters. The key should match the filter field name as documented by the API:

```bash
caflou invoice list --filter invoice_status_id=110714
caflou task list --filter project_id=12345 --filter task_status_id=67890
caflou timesheet list --all --filter date_from=2024-01-01 --filter date_to=2024-12-31
```

## JSON output for scripting

All commands support `--json` for machine-readable output suitable for piping to `jq` or use by AI agents:

```bash
caflou masterdata list vat_rates --json | jq '.[] | {id, name, value}'
caflou invoice list --all --json | jq '[.[] | {id, number, company_name}]'
```

## Config file

Stored at `~/.config/caflou-cli/config.json`:

```json
{
  "token": "...",
  "token_expires_at": 1234567890,
  "default_account_id": "12345",
  "accounts": [
    {"id": "12345", "name": "My Company"}
  ]
}
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Authentication error |
| 3 | Resource not found |
| 4 | Permission denied |
