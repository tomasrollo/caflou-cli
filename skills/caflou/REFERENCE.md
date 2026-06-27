# Caflou CLI — Full Reference

Working directory: `/Users/tomas/Documents/projects/caflou_ai`
All commands: `uv run caflou <group> <command> [options]`

---

## auth

```bash
caflou auth login [--email E] [--password P] [--account NAME]
caflou auth whoami
```

Config stored at `~/.config/caflou-cli/config.json`. Token and default account ID are set on login. Override per-command with `--account NAME_OR_ID` or env vars `CAFLOU_TOKEN` / `CAFLOU_ACCOUNT_ID`.

---

## company

```bash
caflou company list [--filter key=val] [--all] [--json] [--page N] [--per N]
caflou company get <id> [--json]
caflou company template [--account A]
caflou company create --from-file company.json [--json]
caflou company update <id> [--name NAME] [--status-id ID] [--from-file F] [--json]
caflou company delete <id> [--force] [--json]
```

`kind`: `legal_entity` or `individual`.

---

## contact

```bash
caflou contact list [--filter key=val] [--all] [--json]
caflou contact get <id> [--json]
caflou contact template
caflou contact create --from-file contact.json [--json]   # company_id required in body
caflou contact update <id> [--name NAME] [--from-file F] [--json]
caflou contact delete <id> [--force] [--json]
```

**Important**: All write operations route through `/companies/{company_id}/contacts`. The CLI auto-fetches `company_id` for update/delete. Include `company_id` in the JSON body for create.

---

## project

```bash
caflou project list [--filter key=val] [--all] [--json]
caflou project get <id> [--json]
caflou project template
caflou project create --from-file project.json [--json]
caflou project update <id> [--name NAME] [--status-id ID] [--progress 0-100] [--finished/--no-finished] [--from-file F] [--json]
caflou project delete <id> [--force] [--json]
```

---

## task

```bash
caflou task list [--filter key=val] [--all] [--json]
caflou task get <id> [--json]
caflou task template
caflou task create --from-file task.json [--json]
caflou task update <id> [--name NAME] [--status-id ID] [--progress 0-100] [--finished/--no-finished] [--from-file F] [--json]
caflou task delete <id> [--force] [--json]
```

Useful filters: `project_id`, `company_id`, `user_id`, `task_status_id`.

---

## document

```bash
caflou document list [--filter key=val] [--all] [--json]
caflou document list --filter search=DD15260067   # search by document number
caflou document get <id> [--json]
caflou document template <kind>                   # generates JSON skeleton
caflou document create --from-file doc.json [--json]
caflou document update <id> [--paid/--no-paid] [--payment-date YYYY-MM-DD] [--from-file items.json] [--json]
caflou document delete <id> [--force] [--json]
```

**Kind values** (use in template and create):

| Logical kind | API kind | Financial? | Needs supplier? |
|---|---|---|---|
| `issued` | `issued` | yes | no |
| `received` | `received` | yes | yes |
| `proforma` | `proforma` | yes | no |
| `proforma_received` | `proforma_received` | yes | yes |
| `offer` | `offer` | no | no |
| `offer_received` | `offer_received` | no | yes |
| `order_issued` | `order_issued` | no | yes |
| `order_received` | `order_received` | no | no |
| `delivery` | `delivery` | no | no |
| `storno` | → `issued` | yes | no |
| `storno_received` | → `received` | yes | yes |
| `contract` | → `issued` | yes | no |
| `contract_received` | → `received` | yes | yes |
| `tax_receipt` | → `issued` | yes | no |
| `tax_receipt_received` | → `issued` | yes | yes |

Financial kinds require `date_of_tax` and `date_of_payment`. Supplier kinds require `from_company_id`. The template includes all required fields and the `create` command validates them before calling the API.

Document number filtering: `--filter number=X` is silently ignored by the API; use `--filter search=X` instead.

---

## timesheet

```bash
caflou timesheet list [--filter key=val] [--all] [--json]
caflou timesheet get <id> [--json]
caflou timesheet template
caflou timesheet create --from-file entry.json [--json]
caflou timesheet update <id> [--hours N] [--status-id ID] [--from-file F] [--json]
caflou timesheet delete <id> [--force] [--json]
```

`rate_type_id` is mandatory for create — run `caflou masterdata list rate_types` to find valid IDs. Required body fields: `name`, `hours`, `value`, `unit`, `rate_type_id`, `start_time`, `end_time`.

---

## transfer

```bash
caflou transfer list [--filter key=val] [--all] [--json]
caflou transfer get <id> [--json]
caflou transfer template [income|expense]
caflou transfer create --from-file transfer.json [--json]
caflou transfer update <id> [--paid/--no-paid] [--payment-date YYYY-MM-DD] [--real-value N] [--json]
caflou transfer delete <id> [--force] [--json]
```

**Note**: `--paid/--no-paid` maps to the `done` field in the API (the spec documents it as `paid` but the actual field name is `done`). The CLI handles the translation automatically.

---

## comment

```bash
caflou comment list [--type TYPE] [--entity-id ID] [--filter key=val] [--all] [--json]
caflou comment get <id> [--json]
caflou comment create --type TYPE --entity-id ID --text "..." [--private] [--notify USER_ID]... [--reply-to COMMENT_ID] [--json]
caflou comment create --from-file comment.json [--json]
caflou comment update <id> --text "New text" [--json]
caflou comment delete <id> [--force] [--json]
caflou comment read <id> [--read/--no-read] [--json]   # mark read/unread
caflou comment like <id> [--json]                       # toggle like
```

`--type` values (capitalised Rails class names): `Task`, `Project`, `Invoice`, `Company`, `Contact`, `Transfer`, `Timesheet`.

Filtering uses direct query params (not bracket-notation) for `--type` and `--entity-id`. Any `--filter key=val` flags are sent alongside as `filter[key]=val`.

---

## masterdata

```bash
caflou masterdata sync [TYPE]          # populate cache (omit TYPE to sync all)
caflou masterdata list TYPE            # show cached records
caflou masterdata status               # show what's cached and when last synced
caflou masterdata clear [TYPE]         # delete cache file(s)
```

**Category A** (dedicated endpoints): `vat_rates`, `numeric_rows`, `bank_accounts`, `hour_rates`, `project_hour_rates`, `payment_rules`, `online_payment_accounts`, `resources`, `workflow_causes`, `products`, `tags`, `countries`, `account_users`, `pair_models`, `units`.

**Category B** (harvested from entity records): `task_types`, `task_statuses`, `task_priorities`, `project_types`, `project_statuses`, `project_priorities`, `company_types`, `company_statuses`, `company_phases`, `invoice_statuses`, `timesheet_statuses`, `work_types`, `rate_types`, `transfer_categories`, `contact_types`.

Category B is also populated automatically as a side-effect of list/get commands (passive enrichment). Cache lives at `~/.config/caflou-cli/cache/{account_id}/{type}.json` and is considered stale after 7 days.

---

## Common filters by entity

| Entity | Useful filter keys |
|---|---|
| task | `project_id`, `company_id`, `user_id`, `task_status_id` |
| project | `company_id`, `project_status_id` |
| company | `name`, `company_status_id` |
| contact | `company_id` |
| document | `search` (number lookup), `company_id`, `invoice_status_id`, `kind` |
| timesheet | `project_id`, `task_id`, `user_id` |
| transfer | `company_id`, `invoice_id`, `kind` (`income`/`expense`) |
| comment | `--type` + `--entity-id` (direct params, not `--filter`) |
