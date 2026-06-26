# Filtering

Filter parameters are passed with `--filter key=value` (repeatable). The CLI translates these to `filter[key]=value` query parameters in the Rails bracket notation the API uses.

**The API specification does not document any filter parameters** — only `page` and `per` are formally specified. The filters below were established by testing against the real API or reverse-engineered from the Caflou web application's URLs.

## Key patterns discovered through testing

- **ID filters require the plural form.** `company_ids=X` works; `company_id=X` is silently ignored and returns all results.
- **User IDs in filters come from the `user_id` column in `caflou masterdata list account_users`**, not the account membership ID. Each account_user record has two IDs: the account membership `id` (internal, not useful for filtering) and `user_id` (the underlying user ID used in all entity filter lookups). The `account_users` table displays `user_id` in the first column for this reason.
- **Singular boolean flags use their plural noun form.** The `unpaids=true` flag works; `unpaid=true` does not.

---

## Documents (`caflou document list`)

### Text search

| Filter | Status | Description |
|--------|--------|-------------|
| `search=text` | confirmed | Full-text search |
| `search_not=text` | from web URL | Exclude records matching text |

### Date ranges

| Filter | Status | Description |
|--------|--------|-------------|
| `issued_from=YYYY-MM-DD` | confirmed | Issue date from |
| `issued_to=YYYY-MM-DD` | confirmed | Issue date to |
| `taxable_from=YYYY-MM-DD` | from web URL | Taxable supply date from |
| `taxable_to=YYYY-MM-DD` | from web URL | Taxable supply date to |
| `payment_from=YYYY-MM-DD` | from web URL | Due date from |
| `payment_to=YYYY-MM-DD` | from web URL | Due date to |
| `payment_date_from=YYYY-MM-DD` | from web URL | Actual payment received date from |
| `payment_date_to=YYYY-MM-DD` | from web URL | Actual payment received date to |

The web UI also sends `date_of_issue_period`, `date_of_tax_period`, `date_of_payment_period`, and `payment_date_period` — these likely accept preset strings such as `this_month`, `last_month`, `this_year` but their exact values are unknown.

### Entity IDs (all require plural form)

Use IDs from the master data cache or entity list commands.

| Filter | Status | Description |
|--------|--------|-------------|
| `company_ids=ID` | confirmed | Filter by company |
| `invoice_status_ids=ID` | confirmed | Filter by document status (see `caflou masterdata list invoice_statuses`) |
| `project_ids=ID` | confirmed | Filter by linked project |
| `task_ids=ID` | from web URL | Filter by linked task |
| `user_ids=ID` | from web URL | Filter by responsible user |
| `project_user_ids=ID` | from web URL | Filter by project team member |
| `company_target_user_ids=ID` | from web URL | Filter by company account manager |

`numeric_row_ids` was tested and does **not** filter — documents cannot be filtered by document type/series this way.

### Amount and currency

| Filter | Status | Description |
|--------|--------|-------------|
| `price_from=amount` | from web URL | Minimum total amount |
| `price_to=amount` | from web URL | Maximum total amount |
| `currency=CZK` | confirmed | Filter by currency code |

### Boolean flags

| Filter | Status | Description |
|--------|--------|-------------|
| `unpaids=true` | confirmed | Unpaid documents only (note: plural form) |
| `receiveds=true` | confirmed | Received (incoming) documents only |
| `storno=true` | confirmed | Credit notes only |
| `tax_receipt=true` | confirmed | Tax receipts only |

### Tags

| Filter | Status | Description |
|--------|--------|-------------|
| `tags=ID` | from web URL | Tagged with (tag ID from `caflou masterdata list tags`) |
| `not_in_tags=ID` | from web URL | Not tagged with |

### Other

| Filter | Status | Description |
|--------|--------|-------------|
| `payment_types=value` | from web URL | Payment method (exact accepted values unknown) |
| `filterId=ID` | from web URL | Saved filter ID (visible in the web UI URL when a saved filter is active) |

---

## Companies (`caflou company list`)

| Filter | Status | Description |
|--------|--------|-------------|
| `search=text` | confirmed | Full-text search by name |
| `company_type_ids=ID` | confirmed | Filter by type — use plural form (see `caflou masterdata list company_types`) |
| `company_status_ids=ID` | confirmed | Filter by status — use plural form (see `caflou masterdata list company_statuses`) |
| `company_phase_ids=ID` | confirmed | Filter by phase — use plural form (see `caflou masterdata list company_phases`) |
| `country_id=ID` | unverified | Filter by country — correct key form unknown (see `caflou masterdata list countries`) |
| `tags=ID` | unverified | Tagged with |

---

## Contacts (`caflou contact list`)

| Filter | Status | Description |
|--------|--------|-------------|
| `search=text` | confirmed | Full-text search by name or email |
| `company_ids=ID` | confirmed | Filter by company — use plural form |

---

## Projects (`caflou project list`)

| Filter | Status | Description |
|--------|--------|-------------|
| `search=text` | confirmed | Full-text search by name |
| `company_ids=ID` | confirmed | Filter by company — use plural form |
| `project_status_ids=ID` | confirmed | Filter by status — use plural form (see `caflou masterdata list project_statuses`) |
| `project_type_ids=ID` | confirmed | Filter by type — use plural form (see `caflou masterdata list project_types`) |
| `project_priority_ids=ID` | confirmed | Filter by priority — use plural form (see `caflou masterdata list project_priorities`) |
| `user_ids=ID` | confirmed | Filter by assigned user — use plural form; use the `user_id` column from `caflou masterdata list account_users` |
| `tags=ID` | unverified | Tagged with |

---

## Tasks (`caflou task list`)

| Filter | Status | Description |
|--------|--------|-------------|
| `search=text` | confirmed | Full-text search by name |
| `project_ids=ID` | confirmed | Filter by project — use plural form |
| `task_type_ids=ID` | confirmed | Filter by type — use plural form (see `caflou masterdata list task_types`) |
| `task_status_ids=ID` | confirmed | Filter by status — use plural form (see `caflou masterdata list task_statuses`) |
| `task_priority_ids=ID` | confirmed | Filter by priority — use plural form (see `caflou masterdata list task_priorities`) |
| `user_ids=ID` | confirmed | Filter by assigned user — use plural form; use the `user_id` column from `caflou masterdata list account_users` |

Date-based filtering for tasks has not been verified. Neither `due_date_from/to`, `start_time_from/to`, nor `end_time_from/to` produced filtered results.

---

## Timesheets (`caflou timesheet list`)

The test account has no timesheet records. All filters below are inferred from the data model and have not been verified.

| Filter | Status | Description |
|--------|--------|-------------|
| `project_ids=ID` | unverified | Filter by project |
| `task_ids=ID` | unverified | Filter by task |
| `user_ids=ID` | unverified | Filter by user |
| `work_type_ids=ID` | unverified | Filter by work type (see `caflou masterdata list work_types`) |
| `timesheet_status_ids=ID` | unverified | Filter by status (see `caflou masterdata list timesheet_statuses`) |
| `date_from=YYYY-MM-DD` | unverified | Entry date from |
| `date_to=YYYY-MM-DD` | unverified | Entry date to |

---

## Transfers (`caflou transfer list`)

| Filter | Status | Description |
|--------|--------|-------------|
| `company_ids=ID` | confirmed | Filter by company — use plural form |
| `category_ids=ID` | confirmed | Filter by category — use plural form (see `caflou masterdata list transfer_categories`) |
| `payment_date_from=YYYY-MM-DD` | confirmed | Payment date from |
| `payment_date_to=YYYY-MM-DD` | confirmed | Payment date to |
| `currency=CZK` | confirmed | Filter by currency code |
| `date_from=YYYY-MM-DD` | not working | Transfer entry date from — tested, silently ignored |
| `bank_account_ids=ID` | not working | Filter by bank account — tested, silently ignored |
| `invoice_ids=ID` | not working | Filter by linked document — tested, silently ignored |
