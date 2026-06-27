# Roadmap

## Current state

The CLI supports:
- Read operations for all major transactional objects
- Full CRUD for documents (`caflou document create/update/delete/template`)
- A local master data cache with passive enrichment

See [README.md](../README.md) for full usage.

---

## Planned: Write operations for remaining transactional objects

The following command groups have `create`, `update`, and `delete` stubs that currently print "not implemented". The Caflou API supports full CRUD for all of them.

| Command group | Create | Update | Delete |
|---------------|--------|--------|--------|
| `company`     | POST /companies | PATCH /companies/{id} | DELETE /companies/{id} |
| `contact`     | POST /contacts | PATCH /contacts/{id} | DELETE /contacts/{id} |
| `project`     | POST /projects | PATCH /projects/{id} | DELETE /projects/{id} |
| `timesheet`   | POST /timesheets | PATCH /timesheets/{id} | DELETE /timesheets/{id} |
| `transfer`    | POST /transfers | PATCH /transfers/{id} | DELETE /transfers/{id} |

**Notes from document implementation applicable to others:**
- The API spec's `required` field list is incomplete — validate against actual API errors during implementation.
- The PATCH endpoint for documents only exposes 3 fields (`paid`, `payment_date`, `invoice_items_attributes`); other entities may similarly have restricted update surfaces.

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

## Other potential improvements

- **`caflou auth refresh`** — explicit token refresh without re-entering credentials
- **Differential sync hints** — the API has no `updated_since` filter; webhooks (`PATCH /settings/update_webhooks`) are the proper mechanism for receiving change notifications
- **`--output` format flag** — support CSV in addition to table/JSON
- **Shell completion** — Typer supports generating completion scripts for bash/zsh/fish
- **Transactional object cache** — the document list endpoint appears to return full record data (not just summary fields), which would allow building a local cache similar to master data. Before implementing, verify: (a) whether all document kinds return the same attribute set in list vs. get responses, (b) whether other transactional objects (projects, tasks, etc.) behave the same way. If confirmed, a `caflou document sync` command (analogous to `masterdata sync`) could dramatically reduce API calls for read-heavy workflows.
