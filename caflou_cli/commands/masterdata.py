import datetime
import shutil
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import (
    ALL_TYPES, CATEGORY_A, CATEGORY_B, STALE_DAYS,
    cache_path, enrich_b, load_cache, save_cache, warn_if_stale,
)
from caflou_cli.output import error, print_json, print_table

app = typer.Typer(help="Local master data cache commands.")


# ── helpers ───────────────────────────────────────────────────────────────────

def _resolve_account_id(client) -> str:
    return client._account_id


def _sync_category_a(client, type_name: str) -> int:
    cfg = CATEGORY_A[type_name]
    endpoint = cfg["endpoint"]
    normalize = cfg.get("normalize")

    try:
        if cfg["paginated"]:
            raw = client.list_all(endpoint)
        else:
            raw = client.get(endpoint)
            if isinstance(raw, dict):
                raw = raw.get("results", [raw])
            if not isinstance(raw, list):
                raw = []
    except SystemExit:
        typer.echo(f"  {type_name}: failed (API error)", err=True)
        return 0

    records = [normalize(r) for r in raw] if normalize else raw
    save_cache(_resolve_account_id(client), type_name, records, mark_synced=True)
    return len(records)


def _sync_category_b(client, type_name: str) -> int:
    cfg = CATEGORY_B[type_name]
    source = cfg["source"]
    id_field = cfg["id_field"]
    name_field = cfg["name_field"]

    try:
        records = client.list_all(source)
    except SystemExit:
        typer.echo(f"  {type_name}: failed (API error)", err=True)
        return 0

    pairs: dict[int, dict] = {}
    for r in records:
        rid = r.get(id_field)
        if rid is not None:
            pairs[rid] = {"id": rid, "name": r.get(name_field)}

    account_id = _resolve_account_id(client)
    save_cache(account_id, type_name, list(pairs.values()), mark_synced=True)
    return len(pairs)


def _display_records(type_name: str, records: list, json_output: bool) -> None:
    if json_output:
        print_json(records)
        return

    cfg = CATEGORY_A.get(type_name) or CATEGORY_B.get(type_name)
    columns = cfg.get("display", ["id", "name"]) if cfg else ["id", "name"]
    headers = [c.upper() for c in columns]
    rows = [[str(r.get(c, "-") or "-") for c in columns] for r in records]
    print_table(headers, rows)


# ── commands ──────────────────────────────────────────────────────────────────

@app.command("sync")
def masterdata_sync(
    type_name: Optional[str] = typer.Argument(None, help="Master data type to sync. Omit to sync all."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
) -> None:
    """Sync master data from the API into the local cache."""
    client = get_client(account)
    account_id = _resolve_account_id(client)

    types_to_sync: list[str]
    if type_name:
        if type_name not in ALL_TYPES:
            error(f"Unknown type '{type_name}'. Valid types: {', '.join(sorted(ALL_TYPES))}")
        types_to_sync = [type_name]
    else:
        types_to_sync = sorted(ALL_TYPES)

    results = []
    for t in types_to_sync:
        if not json_output:
            typer.echo(f"Syncing {t}...", err=True)

        if t in CATEGORY_A:
            count = _sync_category_a(client, t)
        else:
            count = _sync_category_b(client, t)

        results.append({"type": t, "records": count, "status": "ok"})

    if json_output:
        print_json(results)
    else:
        typer.echo(f"Done. Synced {len(results)} type(s) for account {account_id}.")


@app.command("list")
def masterdata_list(
    type_name: str = typer.Argument(..., help="Master data type to list."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List cached records for a master data type."""
    if type_name not in ALL_TYPES:
        error(f"Unknown type '{type_name}'. Valid types: {', '.join(sorted(ALL_TYPES))}")

    client = get_client(account)
    account_id = _resolve_account_id(client)

    warn_if_stale(account_id, type_name)

    data = load_cache(account_id, type_name)
    if data is None:
        error(f"No cache for '{type_name}'. Run 'caflou masterdata sync {type_name}' first.", 1)

    records = data.get("records", [])
    _display_records(type_name, records, json_output)


@app.command("clear")
def masterdata_clear(
    type_name: Optional[str] = typer.Argument(None, help="Type to clear. Omit to clear all."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Delete cached master data file(s)."""
    client = get_client(account)
    account_id = _resolve_account_id(client)

    if type_name:
        if type_name not in ALL_TYPES:
            error(f"Unknown type '{type_name}'.")
        path = cache_path(account_id, type_name)
        if path.exists():
            path.unlink()
            typer.echo(f"Cleared {type_name}.")
        else:
            typer.echo(f"{type_name}: no cache file found.")
    else:
        account_cache_dir = cache_path(account_id, "x").parent
        if account_cache_dir.exists():
            shutil.rmtree(account_cache_dir)
            typer.echo(f"Cleared all cached master data for account {account_id}.")
        else:
            typer.echo("No cache found.")


@app.command("status")
def masterdata_status(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show what is cached, how many records, and when last synced."""
    client = get_client(account)
    account_id = _resolve_account_id(client)

    rows = []
    for t in sorted(ALL_TYPES):
        data = load_cache(account_id, t)
        if data is None:
            synced_at = "-"
            count = "-"
            age = "-"
            stale = ""
        else:
            records = data.get("records", [])
            count = str(len(records))
            raw_synced = data.get("synced_at")
            if raw_synced:
                synced_dt = datetime.datetime.fromisoformat(raw_synced)
                synced_at = synced_dt.strftime("%Y-%m-%d %H:%M")
                days = (datetime.datetime.now() - synced_dt).days
                age = f"{days}d"
                stale = " !" if days >= STALE_DAYS else ""
            else:
                synced_at = "enriched only"
                age = "-"
                stale = ""

        category = "A" if t in CATEGORY_A else "B"
        rows.append({
            "type": t,
            "category": category,
            "records": count,
            "synced_at": synced_at,
            "age": age + stale,
        })

    if json_output:
        print_json(rows)
    else:
        print_table(
            ["TYPE", "CAT", "RECORDS", "SYNCED", "AGE"],
            [[r["type"], r["category"], r["records"], r["synced_at"], r["age"]] for r in rows],
        )
