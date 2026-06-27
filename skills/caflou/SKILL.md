---
name: caflou
description: Interact with the Caflou project management platform via caflou-cli, a Python CLI tool installed in the ~/Documents/projects/caflou_ai project. Use when the user wants to read or write Caflou data — tasks, projects, companies, contacts, documents (invoices), timesheets, transfers, comments — or when they ask to look something up, create a record, or automate something in Caflou.
---

# Caflou CLI

CLI tool for the Caflou project management API.

## Prerequisites

Python and `uv` package manager must be installed on users computer.
If the command `caflou` is not available, install the caflou cli first by running `uv tool install git+https://github.com/tomasrollo/caflou-cli`

## Command groups

| Group | What it covers |
|---|---|
| `auth` | Login, whoami |
| `company` | Companies (customers, suppliers) |
| `contact` | Contacts (people inside companies) |
| `project` | Projects |
| `task` | Tasks inside projects |
| `document` | Invoices, offers, delivery notes, contracts, etc. (`/invoices` API) |
| `timesheet` | Work log entries |
| `transfer` | Cashflow entries (income / expense) |
| `comment` | Comments on any entity |
| `masterdata` | Local cache of reference data (statuses, types, VAT rates, etc.) |

## Core patterns

**Read**
```bash
caflou task list                          # paginated table
caflou task list --all                    # all pages
caflou task list --filter project_id=123  # filter
caflou task list --json                   # raw JSON
caflou task get 42                        # single record
```

**Write**
```bash
caflou task template > task.json          # generate skeleton
# edit task.json, then:
caflou task create --from-file task.json
caflou task update 42 --name "New name"   # flag-based update
caflou task delete 42 --force
```

**Comments** (non-standard filtering — uses direct params not bracket notation)
```bash
caflou comment list --type Project --entity-id 600865
caflou comment create --type Task --entity-id 12345 --text "LGTM"
caflou comment read 42        # mark as read
caflou comment like 42        # toggle like
```

**Master data** (IDs for statuses, types, VAT rates, etc.)
```bash
caflou masterdata sync           # populate local cache from API
caflou masterdata list task_statuses
caflou masterdata list vat_rates
```

## Key quirks — read before writing

- **Document `kind`**: `storno`, `contract`, `tax_receipt` are translated to `issued`/`received` by the CLI before POST. Always use the logical kind name (e.g. `storno`) in JSON — the CLI translates it.
- **Contact write ops** require `company_id` in the body; the CLI routes to the company-nested API path automatically.
- **Transfer `--paid/--no-paid`** maps to the `done` field in the API (not `paid`).
- **`commented_type`** is a capitalised Rails class name: `Task`, `Project`, `Invoice`, `Company`, `Contact`, `Transfer`, `Timesheet`.
- **Document financial kinds** (`issued`, `received`, `proforma`, `storno`, `contract`, `tax_receipt`) require `date_of_tax` and `date_of_payment` fields — the template includes them, `create` validates them.
- **Timesheets** require `rate_type_id`; run `caflou masterdata list rate_types` to find valid IDs.

## Finding IDs

When you need the ID for a status, type, or other reference value:
```bash
caflou masterdata sync              # first time only
caflou masterdata list task_statuses
caflou masterdata list project_statuses
caflou masterdata list numeric_rows  # document number series
caflou masterdata list account_users # user IDs for assignment
```

For entity IDs (company, project, task):
```bash
caflou company list --filter name=Acme
caflou project list --filter company_id=123
caflou task list --filter project_id=456
```

See [REFERENCE.md](REFERENCE.md) for the full command and flag reference.
