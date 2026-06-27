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

### `document` — Documents

Covers all document types: invoices, offers, delivery notes, credit notes, etc. The document type is determined by `numeric_row_id` (the numbering series). Use `caflou masterdata list numeric_rows` to see available types and their IDs.

```bash
caflou document list
caflou document get <id>

# Create
caflou document template issued          # print a JSON skeleton for a new issued invoice
caflou document template offer           # skeleton for an offer
caflou document template received        # skeleton for a received invoice
caflou document create --from-file doc.json
caflou document create --from-file -     # read JSON from stdin

# Update (API supports: paid status, payment date, line items only)
caflou document update <id> --paid --payment-date 2024-06-01
caflou document update <id> --no-paid
caflou document update <id> --from-file items.json   # replace line items

# Delete (prompts for confirmation)
caflou document delete <id>
caflou document delete <id> --force      # skip confirmation
```

**Supported template kinds:** `issued`, `received`, `proforma`, `proforma_received`, `offer`, `offer_received`, `order_issued`, `order_received`, `delivery`, `contract`, `contract_received`, `storno`, `storno_received`, `tax_receipt`, `tax_receipt_received`

**Notes:**
- The template pre-fills `numeric_row_id` and `vat_rate_id` from the local master data cache. Run `caflou masterdata sync` first if the cache is empty.
- `date_of_tax` and `date_of_payment` are required by the API for financial document kinds (invoices, proformas, credit notes, tax receipts) but not for non-financial ones (delivery notes, offers, orders). The template includes them automatically when needed.
- Received documents (`received`, `proforma_received`, `offer_received`, `order_issued`, `storno_received`, `contract_received`, `tax_receipt_received`) require a `from_company_id` (the supplier). The template includes a `null` placeholder for these kinds.
- **The `kind` field in the JSON body does not always match the kind name you pass to `template`.** The Caflou API uses a small set of broader `kind` values (`issued`, `received`, `proforma`, etc.) and relies on `numeric_row_id` to distinguish specific document types within each category. For example, a `storno` document must be submitted with `"kind": "issued"`, and a `contract_received` with `"kind": "received"`. The template command sets the correct `kind` automatically and explains the mapping in the `_comment` field — remove `_comment` before calling `create`.
- `update` only supports the three fields the API exposes via PATCH: `paid`, `payment_date`, and `invoice_items_attributes`.

### `project` — Projects

```bash
caflou project list
caflou project get <id>

# Create
caflou project template                      # print a JSON skeleton for a new project
caflou project create --from-file project.json
caflou project create --from-file -          # read JSON from stdin

# Update
caflou project update <id> --name "New name"
caflou project update <id> --status-id <id> --finished
caflou project update <id> --progress 75
caflou project update <id> --from-file changes.json

# Delete (prompts for confirmation)
caflou project delete <id>
caflou project delete <id> --force
```

**Template fields:** `name` (required), `company_id`, `user_id` (owner), `user_ids` (team members), `project_type_id`, `project_status_id`, `project_priority_id`, `start_date`, `end_date`, `currency`, `planned_hours`, `description`. The template pre-fills type/status/priority IDs from the local master data cache.

### `task` — Tasks

```bash
caflou task list
caflou task get <id>

# Create
caflou task template                      # print a JSON skeleton for a new task
caflou task create --from-file task.json
caflou task create --from-file -          # read JSON from stdin

# Update (flags for common fields, --from-file for anything else)
caflou task update <id> --name "New name"
caflou task update <id> --status-id <id> --progress 50
caflou task update <id> --finished
caflou task update <id> --from-file changes.json

# Delete (prompts for confirmation)
caflou task delete <id>
caflou task delete <id> --force
```

**Template fields:** `name` (required), `project_id`, `company_id`, `user_id` (primary assignee), `task_type_id`, `task_status_id`, `task_priority_id`, `description`, `start_time`, `end_time`, `planned_hours`, `currency`. The template pre-fills type/status/priority IDs from the local master data cache.

### `timesheet` — Timesheet entries

```bash
caflou timesheet list
caflou timesheet get <id>
```

### `transfer` — Cash flow transfers

```bash
caflou transfer list
caflou transfer get <id>

# Create
caflou transfer template income           # print a JSON skeleton for an income transfer
caflou transfer template expense          # skeleton for an expense
caflou transfer create --from-file transfer.json
caflou transfer create --from-file -      # read JSON from stdin

# Update (API supports: done status, payment date, real value)
caflou transfer update <id> --paid --payment-date 2026-06-01
caflou transfer update <id> --no-paid
caflou transfer update <id> --real-value 9500.00

# Delete (prompts for confirmation)
caflou transfer delete <id>
caflou transfer delete <id> --force
```

**Template fields:** `name`, `kind` (`income`/`expense`), `currency`, `date`, `value` (all required), plus `category_id`, `company_id`, `project_id`, `invoice_id`, `payment_date`, `done`, `description`, `reference_number`.

**Notes:**
- `date` is the accounting/entry date; `payment_date` is when the money actually moved.
- `invoice_id` links the transfer to a document.
- `update` supports only the three fields the API exposes via PATCH: `done` (paid status), `payment_date`, and `real_value`. Note: the API spec incorrectly names this field `paid` — the actual field name is `done`.

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
| `--per <n>` | Items per page (default: 100, max: 100) |
| `--all` | Fetch all pages (warns if total exceeds 500) |
| `--filter key=value` | Filter results (repeatable) |

## Filtering

Use `--filter` to pass Caflou API filters. The key should match the filter field name as documented by the API:

```bash
caflou document list --filter invoice_status_ids=110714
caflou document list --filter company_ids=12345 --filter receiveds=true
caflou task list --filter project_ids=12345 --filter task_status_ids=67890
caflou timesheet list --all --filter date_from=2024-01-01 --filter date_to=2024-12-31
```

## JSON output for scripting

All commands support `--json` for machine-readable output suitable for piping to `jq` or use by AI agents:

```bash
caflou masterdata list vat_rates --json | jq '.[] | {id, name, value}'
caflou document list --all --json | jq '[.[] | {id, number, company_name}]'
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
