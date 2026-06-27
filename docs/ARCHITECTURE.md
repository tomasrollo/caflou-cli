# Architecture

Overview of the codebase structure, key design decisions, and patterns to follow when extending the CLI.

---

## Module map

```
caflou_cli/
  main.py           — Typer app root; registers all command groups
  api.py            — HTTP client (CaflouClient), ClientProtocol, auth helpers
  config.py         — Config file read/write (~/.config/caflou-cli/config.json)
  cache.py          — Master data cache: Category A/B definitions, read/write, passive enrichment
  output.py         — All terminal output: print_table, print_record, print_json, error

  commands/
    _common.py      — Shared helpers used by all 7 entity command modules
    auth.py         — caflou auth login / whoami
    masterdata.py   — caflou masterdata sync / list / clear / status
    company.py      — caflou company …
    contact.py      — caflou contact …
    document.py     — caflou document …
    project.py      — caflou project …
    task.py         — caflou task …
    timesheet.py    — caflou timesheet …
    transfer.py     — caflou transfer …

tests/
  conftest.py       — runner fixture, isolated_cache autouse fixture
  fake_client.py    — FakeClient: in-memory ClientProtocol adapter for tests
  test_common.py
  test_task.py
  test_transfer.py
  test_contact.py
  test_document.py
```

---

## Request lifecycle

Every entity command follows the same sequence:

```
CLI args (Typer)
  → parse_filters / read_json_input    [commands/_common.py]
  → get_client(account)                [api.py] — reads token + account_id from config/env
  → client.list / get / post / patch / delete
      → CaflouClient._handle(response) [api.py] — maps HTTP status codes to error() calls
  → enrich_from_entity(...)            [cache.py] — passively populates Category B cache
  → print_table / print_record / print_json  [output.py]
```

For list commands this flow is centralized in `run_list` (`commands/_common.py`). All 7 entity command modules call `run_list` with their own `resource`, `headers`, and `row_fn` — the pagination, enrichment, and rendering logic lives in one place.

---

## Key files in detail

### `api.py`

**`ClientProtocol`** is a `typing.Protocol` that defines the interface commands depend on:

```python
class ClientProtocol(Protocol):
    account_id: str          # property
    get(path, params) -> Any
    list(resource, page, per, filters) -> dict
    list_all(resource, filters) -> list
    post(path, data) -> Any
    patch(path, data) -> Any
    delete(path) -> None
```

`CaflouClient` satisfies it structurally (no inheritance needed). `FakeClient` in `tests/` is the second adapter. Any new HTTP implementation (e.g. async, rate-limited) should satisfy this protocol rather than subclassing `CaflouClient`.

**URL pattern**: all authenticated requests go to `/api/v1/{account_id}/{path}`. The `account_id` is stored on the client and prefixed automatically — command code only passes the resource path (e.g. `"tasks"`, `"tasks/42"`).

**Error handling in `_handle`**: HTTP errors are translated to `error()` calls that print a message and call `raise typer.Exit`. There is no exception propagation — commands assume every client call either returns a value or terminates.

### `config.py`

Stores a single JSON file at `~/.config/caflou-cli/config.json` with:
- `token` — JWT Bearer token
- `default_account_id` — active account
- `accounts` — list of `{id, name}` dicts for name→ID resolution

`resolve_account_id` does fuzzy name matching so `--account KML` resolves without needing the full UUID.

### `cache.py`

The master data cache stores JSON files at `~/.config/caflou-cli/cache/{account_id}/{type_name}.json`.

**Category A** — types that have their own API endpoints (`/vat_rates`, `/numeric_rows`, etc.). Synced explicitly with `caflou masterdata sync`. Schema: `{"synced_at": "...", "records": [...]}`.

**Category B** — types with no dedicated endpoint (task statuses, project types, etc.). IDs appear as attributes on entity records (`task_status_id` / `task_status_name` on a task). Discovered two ways:
1. **Passive enrichment** — `enrich_from_entity` is called automatically in `run_list` and entity `get` commands whenever entity records are returned. It extracts `{id, name}` pairs and upserts them into the cache without updating `synced_at`.
2. **Explicit sync** — `caflou masterdata sync task_statuses` fetches all tasks, extracts the pairs, and marks `synced_at`.

`PASSIVE_ENRICHMENT` in `cache.py` maps each entity resource name to the `(id_field, name_field, cache_name)` tuples that should be harvested from it. Adding a new Category B type requires updating both `CATEGORY_B` and `PASSIVE_ENRICHMENT`.

### `commands/_common.py`

Three shared helpers used by all entity command modules:

- **`run_list`** — full list-command body: handles `--all` vs paginated, calls `enrich_from_entity`, renders table or JSON. All entity `list` commands reduce to a single `run_list(...)` call.
- **`parse_filters`** — converts `["key=value", ...]` CLI args into `{"key": "value", ...}` dict. Errors on invalid format.
- **`read_json_input`** — reads JSON from a file path or `-` for stdin. Errors if no file provided or JSON is invalid.

Never duplicate these in a new command module — always import from `_common`.

### `output.py`

All terminal output goes through this module. Key rule: **write to stderr for status/warnings, stdout for data**. This means `--json` output is reliably parseable by downstream tools like `jq`:

- `error(msg)` → stderr, then `raise typer.Exit`
- `print_pagination(data)` → stderr (`err=True`)
- Confirmation prompts → stderr
- `print_table`, `print_record`, `print_json` → stdout

---

## Patterns to follow

### Adding a new entity command group

1. Create `commands/{entity}.py`. Copy the structure of `commands/task.py` as the baseline.
2. Define `_LIST_HEADERS` and `_list_row` for the table view.
3. Implement `list` (calls `run_list`), `get`, `template`, `create`, `update`, `delete`.
4. Import and use `parse_filters`, `read_json_input`, `run_list` from `_common` — do not inline them.
5. Register the group in `main.py`: `app.add_typer(entity.app, name="entity")`.
6. If the entity has Category B master data associated with it, add entries to `CATEGORY_B` and `PASSIVE_ENRICHMENT` in `cache.py`.
7. Add tests in `tests/test_{entity}.py` using `FakeClient`.

### Update commands

Build the `payload` dict incrementally from explicit flags, merging `--from-file` first so flags override file content:

```python
payload: dict = {}
if from_file is not None:
    payload.update(read_json_input(from_file))
    payload.pop("_comment", None)
if name is not None:
    payload["name"] = name
if not payload:
    error("Nothing to update. Provide ...")
```

Always guard against empty payload with an explicit error.

### Delete commands

Fetch the record first (for the confirmation prompt) and use `--force` to skip it:

```python
if not force:
    record = client.get(f"{resource}/{id}")
    confirmed = typer.confirm(f"Delete '{record.get('name')}'?", default=False)
    if not confirmed:
        typer.echo("Aborted.")
        raise typer.Exit(0)
client.delete(f"{resource}/{id}")
```

### Template commands

The `template` command is the user's entry point for creating records. The skeleton should:
- Include a `_comment` key with field guidance
- Pre-fill IDs from cache where available (call `load_cache` for any relevant master data types)
- Strip `_comment` in `create` before POSTing (`data.pop("_comment", None)`)

---

## Known API quirks

These are actively worked-around in the code. Document new ones when discovered.

**Contact write operations require company-nested paths.** Standalone `POST /contacts` and `PATCH /contacts/{id}` return 404/500. All contact create/update/delete must use `/companies/{company_id}/contacts[/{id}]`. The CLI extracts `company_id` from the request body (create) or fetches the contact first (update/delete). See `commands/contact.py`.

**Transfer PATCH field is `done`, not `paid`.** The API spec documents the field as `paid` but the actual working field name is `done`. The CLI's `--paid/--no-paid` flag maps to `payload["done"]`. See `commands/transfer.py:transfer_update`.

**Document `kind` in POST uses broader categories.** The API's `kind` field accepts only: `issued`, `received`, `proforma`, `proforma_received`, `offer`, `offer_received`, `order_issued`, `order_received`, `delivery`. The distinct document types `storno`, `contract`, `tax_receipt` (and their `_received` variants) are submitted as `issued`/`received` — the specific type is determined by `numeric_row_id`. The `_post_kind_map` dict in `document_template` handles this mapping. See `commands/document.py`.

**Timesheet `rate_type_id` cannot be null.** The API rejects timesheet creation with a 422 if `rate_type_id` is absent or null. Rate types are a Category B type — if the account has none configured, timesheets cannot be created via API.

---

## Testing

Run all tests: `uv run pytest -v`

**`FakeClient`** (`tests/fake_client.py`) satisfies `ClientProtocol` without making HTTP calls. Seed canned responses and inspect recorded calls:

```python
fake = FakeClient().seed("LIST", "tasks", {"results": [...], ...})
with patch("caflou_cli.commands.task.get_client", return_value=fake):
    result = runner.invoke(app, ["task", "list"])
assert fake.calls[0]["method"] == "LIST"
```

**`isolated_cache`** autouse fixture (in `conftest.py`) redirects `CACHE_DIR` to a temp directory for the duration of each test. No test reads or writes real cache files.

**Patching `get_client`**: patch it at the point of import in the command module, not at the definition site:

```python
# correct:   "caflou_cli.commands.task.get_client"
# incorrect: "caflou_cli.api.get_client"
```

**`result.stdout` vs `result.output`**: when a command emits warnings to stderr alongside JSON to stdout, use `result.stdout` for JSON parsing — `result.output` is the mixed stream. This matters for commands like `document template` that warn about missing cache entries.

---

## File locations

| Resource | Path |
|----------|------|
| Config | `~/.config/caflou-cli/config.json` |
| Master data cache | `~/.config/caflou-cli/cache/{account_id}/{type_name}.json` |
| API base URL | `https://app.caflou.com/api/v1/{account_id}/` |
| OpenAPI spec | `docs/caflou_api.json` |
| Data model | `docs/DATAMODEL.md` |
| Filtering reference | `docs/FILTERING.md` |
| Refactoring log | `docs/REFACTORING.md` |
| Roadmap | `docs/ROADMAP.md` |
