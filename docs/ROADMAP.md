# Roadmap

## Current state

The CLI supports:
- Read operations for all major transactional objects
- Full CRUD for documents (`caflou document create/update/delete/template`)
- A local master data cache with passive enrichment
- ID↔name cache for projects, companies, documents, contacts with `find` commands
- `comment` command group with full CRUD plus read/like

See [README.md](../README.md) for full usage.

---

## Planned: Office coordinator workflow improvements

Identified from mapping typical workflows (inbound invoice, customer inquiry, issuing invoice).
Priority order based on frequency and effort.

### 1. Typed cross-entity filter flags on `list` commands ✅ / ❌

Every coordinator workflow goes: `find` company/project → list related objects. Currently all `list`
commands only expose raw `--filter key=value`, which requires knowing exact API key names.

Proposed typed flags:

| Command | Flag | API filter key |
|---|---|---|
| `task list` | `--project-id` | `project_id` |
| `task list` | `--company-id` | `company_id` |
| `timesheet list` | `--project-id` | `project_id` |
| `timesheet list` | `--task-id` | `task_id` |
| `project list` | `--company-id` | `company_id` |
| `document list` | `--company-id` | `to_company_id` |
| `transfer list` | `--company-id` | `company_id` |
| `transfer list` | `--project-id` | `project_id` |
| `comment list` | `--project-id` / `--task-id` | via `--type` + `--entity-id` |

### 2. Inline flag-based `task create`

Creating a follow-up task currently requires template → edit JSON → create (3 steps). The most
common case needs one command:

```
caflou task create --name "Call client back" --project-id 123
```

Keep `--from-file` for complex cases; add first-class flags for `--name`, `--project-id`,
`--company-id`, `--type-id`, `--status-id`, `--priority-id`, `--user-id`, `--description`.

### 3. `project show` — aggregate summary view

Single command to get a full picture of a project:
- Company, status, dates, progress
- Open tasks (count + recent list)
- Recent comments
- Unpaid invoices linked to the project

Requires multiple API calls. Most useful single compound command for the lookup half of workflows.

### 4. Inline flag-based `transfer create`

Recording a payment against an invoice currently requires a JSON template. Should support:

```
caflou transfer create --kind expense --name "Pay supplier" --value 5000 --invoice-id 456 --company-id 789
```

Keep `--from-file` for complex cases.

### 5. `contact find` — ✅ Done

Implemented alongside project/company/document find. Searches contacts by name with cache-first
strategy. Cache populated passively whenever contacts are listed or fetched.

---

## Planned: Write operations for Category A master data

Several master data types can be created and updated via the API. The `masterdata` command group could be extended with `create` and `update` subcommands per type.

| Type | Create | Update | Delete |
|------|--------|--------|--------|
| `vat_rates` | POST /vat_rates | PATCH /vat_rates/{id} | DELETE /vat_rates/{id} |
| `numeric_rows` | POST /numeric_rows | PATCH /numeric_rows/{id} | DELETE /numeric_rows/{id} |
| `bank_accounts` | POST /bank_accounts | PATCH /bank_accounts/{id} | DELETE /bank_accounts/{id} |
| `hour_rates` | POST /hour_rates | PATCH /hour_rates/{id} | DELETE /hour_rates/{id} |
| `project_hour_rates` | POST /project_hour_rates | PATCH /project_hour_rates/{id} | DELETE /project_hour_rates/{id} |
| `payment_rules` | POST /payment_rules | PATCH /payment_rules/{id} | DELETE /payment_rules/{id} |
| `online_payment_accounts` | POST /online_payment_accounts | PATCH /online_payment_accounts/{id} | DELETE /online_payment_accounts/{id} |
| `resources` | POST /resources | PATCH /resources/{id} | DELETE /resources/{id} |
| `workflow_causes` | POST /workflow_causes | PATCH /workflow_causes/{id} | DELETE /workflow_causes/{id} |
| `products` | POST /products | PATCH /products/{id} | DELETE /products/{id} |

The following Category A types are read-only in the API (no write endpoints exist): `tags`, `countries`, `account_users`, `pair_models`, `units`.

Category B types (task types, project statuses, etc.) have no API endpoints at all and are managed only through the Caflou web UI.

---

## Unimplemented resources (discovered via web app traffic analysis)

These resources exist in the API and are used by the web app but have no CLI commands yet.
All support standard `get` / `list` operations; scope support is noted where confirmed.
See `docs/WEB_APP_REQUESTS_ANALYSIS.md` for details.

| Resource | Endpoint | Scope support | Notes |
|---|---|---|---|
| Contracts | `contracts` | company, project | Contracts / agreements linked to company or project |
| Email messages | `email_messages` | company | Email correspondence history per company |
| Events | `events` | company, project | Calendar events |
| Time entries | `time_entries` | company, project | Individual time tracking records |
| Timesheets | `timesheets` | company | Timesheet summaries |
| Uploads | `uploads` | company, project | File attachments per company or project |
| Budget items | `budget_items` | project | Project budget line items |
| Milestones | `projects/{id}/milestones` | — (nested) | Project milestones |
| To-dos | `to_dos` | — | Global to-do list |
| Task to-dos | `task_todos` | — | Task-level checklist items |
| Payments | `payments` | — | Payment records (distinct from `transfers`) |
| Inventory records | `inventory_records` | — | Stock movements |
| Products | `products` | — | Product catalog |
| Product sets | `product_sets` | — | Product bundles |
| Bank connections | `bank_connections` | — | Bank account integrations |
| Resources | `resources` | — | Resource / capacity management |

---

## Other potential improvements

- **`caflou auth refresh`** — explicit token refresh without re-entering credentials
- **Differential sync hints** — the API has no `updated_since` filter; webhooks (`PATCH /settings/update_webhooks`) are the proper mechanism for receiving change notifications
- **`--output` format flag** — support CSV in addition to table/JSON
- **Shell completion** — Typer supports generating completion scripts for bash/zsh/fish
- **Transactional object cache** — the document list endpoint appears to return full record data (not just summary fields), which would allow building a local cache similar to master data. Before implementing, verify: (a) whether all document kinds return the same attribute set in list vs. get responses, (b) whether other transactional objects (projects, tasks, etc.) behave the same way. If confirmed, a `caflou document sync` command (analogous to `masterdata sync`) could dramatically reduce API calls for read-heavy workflows.
