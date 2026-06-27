import datetime
import json
from pathlib import Path
from typing import Optional

import typer

CACHE_DIR = Path.home() / ".config" / "caflou-cli" / "cache"
STALE_DAYS = 7


# ── normalizers (defined first so they can be referenced in CATEGORY_A) ───────

def _normalize_account_user(record: dict) -> dict:
    """Flatten account_user so name/email surface from the nested user object.
    Stores user_id (the ID used in entity filters) alongside the account_user id."""
    user = record.get("user") or {}
    return {
        **record,
        "name": user.get("name") or record.get("name"),
        "email": record.get("email") or user.get("email"),
        "user_id": user.get("id") or record.get("user_id"),
    }


# ── Category A: dedicated endpoints ──────────────────────────────────────────
# endpoint: API path; paginated: uses standard list pagination; display: table columns
# normalize (optional): transform fn applied to each record before storing

CATEGORY_A: dict[str, dict] = {
    "vat_rates":             {"endpoint": "vat_rates",              "paginated": True,  "display": ["id", "name", "value"]},
    "numeric_rows":          {"endpoint": "numeric_rows",           "paginated": True,  "display": ["id", "name", "kind"]},
    "bank_accounts":         {"endpoint": "bank_accounts",          "paginated": True,  "display": ["id", "name"]},
    "account_users":         {"endpoint": "account_users",          "paginated": True,  "display": ["user_id", "name", "email", "role_name"], "normalize": _normalize_account_user},
    "products":              {"endpoint": "products",               "paginated": True,  "display": ["id", "name"]},
    "tags":                  {"endpoint": "tags",                   "paginated": True,  "display": ["id", "name"]},
    "countries":             {"endpoint": "countries",              "paginated": False, "display": ["id", "name"]},
    "hour_rates":            {"endpoint": "hour_rates",             "paginated": True,  "display": ["id", "name"]},
    "project_hour_rates":    {"endpoint": "project_hour_rates",     "paginated": True,  "display": ["id", "name"]},
    "payment_rules":         {"endpoint": "payment_rules",         "paginated": True,  "display": ["id", "name"]},
    "pair_models":           {"endpoint": "pair_models",            "paginated": True,  "display": ["id", "name"]},
    "online_payment_accounts":{"endpoint": "online_payment_accounts","paginated": True, "display": ["id", "name"]},
    "resources":             {"endpoint": "resources",              "paginated": True,  "display": ["id", "name"]},
    "workflow_causes":       {"endpoint": "workflow_causes",        "paginated": True,  "display": ["id", "name", "entity_type_name"]},
    "units":                 {"endpoint": "settings/units",         "paginated": True,  "display": ["id", "name"]},
}

# ── Category B: harvested from existing entity records ────────────────────────
# source: entity endpoint to scan; id_field/name_field: field names in the record

CATEGORY_B: dict[str, dict] = {
    "task_types":          {"source": "tasks",      "id_field": "task_type_id",       "name_field": "task_type_name"},
    "task_statuses":       {"source": "tasks",      "id_field": "task_status_id",      "name_field": "task_status_name"},
    "task_priorities":     {"source": "tasks",      "id_field": "task_priority_id",    "name_field": "task_priority_name"},
    "project_types":       {"source": "projects",   "id_field": "project_type_id",     "name_field": "project_type_name"},
    "project_statuses":    {"source": "projects",   "id_field": "project_status_id",   "name_field": "project_status_name"},
    "project_priorities":  {"source": "projects",   "id_field": "project_priority_id", "name_field": "project_priority_name"},
    "company_types":       {"source": "companies",  "id_field": "company_type_id",     "name_field": "company_type_name"},
    "company_statuses":    {"source": "companies",  "id_field": "company_status_id",   "name_field": "company_status_name"},
    "company_phases":      {"source": "companies",  "id_field": "company_phase_id",    "name_field": "company_phase_name"},
    "invoice_statuses":    {"source": "invoices",   "id_field": "invoice_status_id",   "name_field": "invoice_state_name"},
    "timesheet_statuses":  {"source": "timesheets", "id_field": "timesheet_status_id", "name_field": "timesheet_status_name"},
    "work_types":          {"source": "timesheets", "id_field": "work_type_id",        "name_field": "work_type_name"},
    "rate_types":          {"source": "timesheets", "id_field": "rate_type_id",        "name_field": "rate_type_name"},
    "transfer_categories": {"source": "transfers",  "id_field": "category_id",         "name_field": "category_name"},
    "contact_types":       {"source": "contacts",   "id_field": "contact_type_id",     "name_field": "contact_type_name"},
}

ALL_TYPES = set(CATEGORY_A) | set(CATEGORY_B)

# Maps entity name -> list of (id_field, name_field, cache_name) for passive enrichment
PASSIVE_ENRICHMENT: dict[str, list[tuple[str, str, str]]] = {
    "tasks": [
        ("task_type_id",       "task_type_name",       "task_types"),
        ("task_status_id",     "task_status_name",     "task_statuses"),
        ("task_priority_id",   "task_priority_name",   "task_priorities"),
    ],
    "projects": [
        ("project_type_id",     "project_type_name",     "project_types"),
        ("project_status_id",   "project_status_name",   "project_statuses"),
        ("project_priority_id", "project_priority_name", "project_priorities"),
    ],
    "companies": [
        ("company_type_id",   "company_type_name",   "company_types"),
        ("company_status_id", "company_status_name", "company_statuses"),
        ("company_phase_id",  "company_phase_name",  "company_phases"),
    ],
    "invoices": [
        ("invoice_status_id", "invoice_state_name", "invoice_statuses"),
    ],
    "timesheets": [
        ("timesheet_status_id", "timesheet_status_name", "timesheet_statuses"),
        ("work_type_id",        "work_type_name",        "work_types"),
        ("rate_type_id",        "rate_type_name",        "rate_types"),
    ],
    "transfers": [
        ("category_id", "category_name", "transfer_categories"),
    ],
    "contacts": [
        ("contact_type_id", "contact_type_name", "contact_types"),
    ],
}


# ── low-level cache I/O ───────────────────────────────────────────────────────

def cache_path(account_id: str, type_name: str) -> Path:
    return CACHE_DIR / account_id / f"{type_name}.json"


def load_cache(account_id: str, type_name: str) -> Optional[dict]:
    path = cache_path(account_id, type_name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def save_cache(account_id: str, type_name: str, records: list, mark_synced: bool = True) -> None:
    path = cache_path(account_id, type_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_synced_at = (load_cache(account_id, type_name) or {}).get("synced_at")
    data = {
        "synced_at": datetime.datetime.now().isoformat() if mark_synced else existing_synced_at,
        "records": records,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def warn_if_stale(account_id: str, type_name: str) -> None:
    data = load_cache(account_id, type_name)
    if not data or not data.get("synced_at"):
        return
    synced = datetime.datetime.fromisoformat(data["synced_at"])
    age = datetime.datetime.now() - synced
    if age.days >= STALE_DAYS:
        typer.echo(
            f"Warning: {type_name} cache is {age.days} days old. "
            f"Run 'caflou masterdata sync {type_name}' to refresh.",
            err=True,
        )


# ── passive enrichment (Category B side-effect) ───────────────────────────────

def enrich_b(account_id: str, cache_name: str, records: list[dict]) -> None:
    """Upsert {id, name} pairs into a Category B cache file.
    Does NOT update synced_at — reserved for explicit sync runs only."""
    if not records:
        return

    path = cache_path(account_id, cache_name)
    existing: dict[int, dict] = {}

    if path.exists():
        try:
            data = json.loads(path.read_text())
            for r in data.get("records", []):
                if r.get("id") is not None:
                    existing[r["id"]] = r
        except (json.JSONDecodeError, OSError):
            pass

    original_count = len(existing)
    for r in records:
        rid = r.get("id")
        if rid is not None and rid not in existing:
            existing[rid] = r

    if len(existing) == original_count:
        return  # nothing new — skip write

    path.parent.mkdir(parents=True, exist_ok=True)
    synced_at = (load_cache(account_id, cache_name) or {}).get("synced_at")
    path.write_text(json.dumps(
        {"synced_at": synced_at, "records": list(existing.values())},
        indent=2,
        ensure_ascii=False,
    ))


def enrich_from_entity(account_id: str, entity: str, records: list[dict]) -> None:
    """Extract all Category B pairs from a batch of entity records and enrich caches."""
    mapping = PASSIVE_ENRICHMENT.get(entity, [])
    if not mapping:
        return

    buckets: dict[str, list[dict]] = {}
    for id_field, name_field, cache_name in mapping:
        for r in records:
            rid = r.get(id_field)
            if rid is not None:
                buckets.setdefault(cache_name, []).append({"id": rid, "name": r.get(name_field)})

    for cache_name, pairs in buckets.items():
        enrich_b(account_id, cache_name, pairs)
