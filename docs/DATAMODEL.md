# Data model

The Caflou API manages two broad categories of data: **transactional objects** (the records users create day-to-day) and **master data** (configuration and reference data that transactional objects refer to by ID).

---

## Transactional objects

These are the core business records. Each has a list endpoint, a detail endpoint, and typically create/update/delete endpoints.

### Company (`/companies`)

A customer, supplier, or partner organisation. The root entity in Caflou — projects and invoices are usually linked to a company.

Key fields: `name`, `company_type_id`, `company_status_id`, `company_phase_id`, `ic` (company reg. no.), `dic` (VAT number), `country_id`, tags.

### Contact (`/contacts`)

An individual person, typically associated with a company.

Key fields: `name`, `email`, `phone`, `company_id`, `position`.

### Project (`/projects`)

A unit of work, linked to a company. Contains tasks and timesheet entries.

Key fields: `name`, `company_id`, `project_type_id`, `project_status_id`, `project_priority_id`, `start_date`, `end_date`, `budget`, assigned users.

### Task (`/tasks`)

A work item inside a project.

Key fields: `name`, `project_id`, `task_type_id`, `task_status_id`, `task_priority_id`, `due_date`, `assigned_user_id`, `estimated_hours`.

### Document (`/invoices`)

A financial or commercial document. The underlying API resource is `invoices`, but the endpoint covers all document types — issued invoices, received invoices, proforma invoices, offers, order confirmations, delivery notes, credit notes (storno), tax receipts, and contracts. The `numeric_row_id` field (referencing a `numeric_rows` master data entry) determines the document type and its numbering sequence.

Contains line items (`invoice_rows`), each with a product, quantity, unit price, and VAT rate.

Key fields: `company_id`, `invoice_status_id`, `numeric_row_id`, `currency`, `issue_date`, `due_date`, `bank_account_id`, `payment_rule_id`, `invoice_rows[]`.

### Timesheet (`/timesheets`)

A logged work entry against a project or task.

Key fields: `project_id`, `task_id`, `user_id`, `date`, `hours`, `work_type_id`, `rate_type_id`, `timesheet_status_id`.

### Transfer (`/transfers`)

A cash flow entry — an income or expense record, optionally linked to an invoice.

Key fields: `company_id`, `invoice_id`, `category_id`, `amount`, `currency`, `date`, `bank_account_id`.

---

## Master data — Category A

These types have their own dedicated list/get API endpoints and are synced explicitly with `caflou masterdata sync`. They are identified by integer IDs and referenced by transactional objects.

| Type | Endpoint | Writable | Description |
|------|----------|----------|-------------|
| `vat_rates` | `/vat_rates` | Yes | VAT percentages (e.g. 21%, 12%, 0%) used on invoice line items |
| `numeric_rows` | `/numeric_rows` | Yes | Document number sequences (invoice numbering series), with `kind` field (issued, received, proforma, offer, storno, etc.) |
| `bank_accounts` | `/bank_accounts` | Yes | Bank accounts of the Caflou account holder, used on invoices and transfers |
| `hour_rates` | `/hour_rates` | Yes | Billing rates per hour, used on timesheets |
| `project_hour_rates` | `/project_hour_rates` | Yes | Hour rates scoped to specific projects |
| `payment_rules` | `/payment_rules` | Yes | Default payment terms (e.g. "30 days net") attached to invoices |
| `online_payment_accounts` | `/online_payment_accounts` | Yes | Online payment gateway configurations |
| `resources` | `/resources` | Yes | Bookable resources (rooms, equipment, vehicles) |
| `workflow_causes` | `/workflow_causes` | Yes | Reasons for workflow state transitions, scoped by entity type |
| `products` | `/products` | Yes | Product/service catalogue items that can be added as invoice line items |
| `tags` | `/tags` | No | Free-form labels that can be attached to various objects |
| `countries` | `/countries` | No | ISO country list used for company addresses |
| `account_users` | `/account_users` | No | Users who have access to the Caflou account (read-only via API) |
| `pair_models` | `/pair_models` | No | Templates for pairing financial records |
| `units` | `/settings/units` | No (via settings PATCH) | Units of measure (pieces, hours, kg, etc.) used on invoice line items |

---

## Master data — Category B

These types have **no dedicated API endpoints**. Their IDs and names appear as attributes on transactional entity records (e.g. `task_type_id` / `task_type_name` on a task). They are managed only through the Caflou web UI.

The CLI discovers and caches them by scanning entity records — either passively as a side-effect of `list`/`get` commands, or explicitly via `caflou masterdata sync` (which fetches all records from the parent entity).

| Type | Source entity | ID field | Name field |
|------|--------------|----------|------------|
| `task_types` | tasks | `task_type_id` | `task_type_name` |
| `task_statuses` | tasks | `task_status_id` | `task_status_name` |
| `task_priorities` | tasks | `task_priority_id` | `task_priority_name` |
| `project_types` | projects | `project_type_id` | `project_type_name` |
| `project_statuses` | projects | `project_status_id` | `project_status_name` |
| `project_priorities` | projects | `project_priority_id` | `project_priority_name` |
| `company_types` | companies | `company_type_id` | `company_type_name` |
| `company_statuses` | companies | `company_status_id` | `company_status_name` |
| `company_phases` | companies | `company_phase_id` | `company_phase_name` |
| `invoice_statuses` | invoices | `invoice_status_id` | `invoice_state_name` |
| `timesheet_statuses` | timesheets | `timesheet_status_id` | `timesheet_status_name` |
| `work_types` | timesheets | `work_type_id` | `work_type_name` |
| `rate_types` | timesheets | `rate_type_id` | `rate_type_name` |
| `transfer_categories` | transfers | `category_id` | `category_name` |
| `contact_types` | contacts | `contact_type_id` | `contact_type_name` |

---

## Relationships at a glance

```
Company ──< Project ──< Task
         |           └─< Timesheet
         |
         └──< Document ──< InvoiceRow ──> Product
         |              └──> NumericRow       └──> VatRate
         |              └──> BankAccount
         |              └──> PaymentRule
         |
         └──< Transfer ──> TransferCategory
                        └──> BankAccount

Task ──> TaskType, TaskStatus, TaskPriority
Project ──> ProjectType, ProjectStatus, ProjectPriority
Company ──> CompanyType, CompanyStatus, CompanyPhase
Timesheet ──> WorkType, RateType, TimesheetStatus, HourRate
```

All IDs on the right-hand side of `──>` are master data references. Category A types are synced directly from their own endpoints; Category B types are inferred from the entity records they appear on.
