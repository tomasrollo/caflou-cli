# Web App API Requests Analysis

Captured from browser network inspection of the Caflou web app (June 2026).
The goal was to discover which API parameters actually work for filtering,
since the public docs only document `page` and `per`.

---

## 1. `scope_type` + `scope_id` — broader than previously known

We discovered `scope_type=company&scope_id=<id>` / `scope_type=project&scope_id=<id>` from
a previous session on the `/invoices` endpoint. The web app uses this pattern on many more
resources:

| Resource | scope_type values confirmed |
|---|---|
| `invoices` | `company`, `project` |
| `projects` | `company` |
| `contacts` | `company` |
| `transfers` | `company`, `project`, `invoice` (inferred) |
| `tasks` | **`company`**, **`project`** |
| `contracts` | `company`, `project` |
| `email_messages` | `company` |
| `events` | `company`, `project` |
| `time_entries` | `company`, `project` |
| `timesheets` | `company` |
| `uploads` | `company`, `project` |
| `budget_items` | `project` |

Key rule: `scope_type`/`scope_id` are **raw query params** (not `filter[]`-wrapped).
The `list()` method passes them via `params.update(scope)`.

### `tasks` with `scope_type=project` is particularly valuable

The web app uses:
```
tasks?scope_type=project&scope_id=573871&inherited_template=true&per=100
```

This replaces the current approach of reading `task_ids` from the project response and
issuing N individual GET calls. One list call returns all project tasks server-side.

### `tasks` with `scope_type=company` — new capability

```
tasks?scope_type=company&scope_id=1723295&filter[active]=true&per=100
```

Enables a tasks section in company context that we couldn't do before without fetching all tasks.

---

## 2. `kind` param on `/invoices` — raw, not `filter[]`-wrapped

The `/invoices` endpoint serves all document types (offers, orders, proformas, invoices,
delivery notes, stornos). The web app filters by type using a raw `kind` param:

```
invoices?kind=offer
invoices?kind=order
invoices?kind=proforma
invoices?kind=invoice
invoices?kind=delivery
```

Can be combined with `filter[]` params:
```
invoices?kind=proforma&filter[issueds]=true&filter[unpaids]=true
```

---

## 3. `filter[]` params confirmed working

The following filters appear with real values in web app requests (not empty strings),
confirming they are processed server-side:

### On `projects`
| Filter | Values seen | Notes |
|---|---|---|
| `filter[active]` | `true` | Active projects only |
| `filter[closed]` | `true` | Include closed projects |
| `filter[project_status_ids]` | comma-list of IDs | Filter by status |
| `filter[project_type_ids]` | comma-list of IDs | Filter by project type |
| `filter[user_ids]` | comma-list of user IDs | Filter by assigned user |
| `filter[not_in_tags]` | tag slug | Exclude tagged projects |

### On `tasks`
| Filter | Values seen | Notes |
|---|---|---|
| `filter[active]` | `true` | Active tasks only |
| `filter[closed]` | `true` | Include closed |
| `filter[assigned]` | `true` | Only assigned tasks |
| `filter[im_involved]` | `true` | Tasks the current user is involved in |
| `filter[task_status_ids]` | comma-list of IDs | Filter by status |
| `filter[task_type_ids]` | comma-list of IDs | Filter by task type |
| `filter[target_user_ids]` | comma-list of user IDs | Filter by assignee |

### On `companies`
| Filter | Values seen | Notes |
|---|---|---|
| `filter[active]` | `true` | Active companies only |
| `filter[company_type_ids]` | comma-list of IDs | Filter by company type |

### On `invoices` / `proformas`
| Filter | Values seen | Notes |
|---|---|---|
| `filter[issueds]` | `true` | Issued documents only |
| `filter[unpaids]` | `true` | Unpaid documents only |

### On `products`
| Filter | Values seen | Notes |
|---|---|---|
| `filter[inventory_gt_zero]` | `true` | Only items with stock |

---

## 4. Raw (non-`filter[]`) params that work

| Resource | Param | Notes |
|---|---|---|
| `companies` | `active=true` | Alternate to `filter[active]` |
| `projects` | `active=true` | Alternate to `filter[active]` |
| `projects` | `order=name` | Sort alphabetically |
| `tasks` | `inherited_template=true` | Include template-inherited tasks |
| `transfers` | `inherited_template=true` | Include template-inherited transfers |
| `invoices` | `only_write=true&ids=<id>&per=all` | Batch fetch by IDs |
| `users` | `ids=<id>&per=all` | Fetch specific users |
| `time_entries` | `timetracker=true` | Active time tracker entries |
| any | `per=all` | Fetch all results (confirmed on `elements`) |

---

## 5. `/elements` endpoint — batch master data lookup

The web app resolves IDs to names via:
```
elements?type=<Type>&ids=<id1>,<id2>&per=all
```

Types confirmed: `TaskStatus`, `TaskType`, `ProjectStatus`, `ProjectType`,
`CompanyType`, `CompanyStatus`, `CompanyPhase`, `Source`.

Also supports `types[]=X&types[]=Y` for multiple types in one call:
```
elements?types[]=CompanyStatus&types[]=CompanyPhase&per=all&company_id=1723295
```

---

## 6. New resources discovered

Resources visible in web app API traffic that are not yet covered by the CLI:

| Resource | Scope support | Notes |
|---|---|---|
| `contracts` | company, project | Contracts / agreements |
| `email_messages` | company | Email correspondence history |
| `events` | company, project | Calendar events |
| `time_entries` | company, project | Individual time tracking records |
| `timesheets` | company | Timesheet summaries |
| `uploads` | company, project | File attachments |
| `budget_items` | project | Project budget line items |
| `milestones` | — (project nested: `projects/{id}/milestones`) | Project milestones |
| `to_dos` | — | Global to-do list |
| `task_todos` | — | Task-level checklist items |
| `payments` | — | Payment records (distinct from `transfers`) |
| `inventory_records` | — | Stock movements |
| `products` | — | Product catalog |
| `product_sets` | — | Product bundles |
| `bank_connections` | — | Bank account integrations |
| `resources` | — | Resource / capacity management |
