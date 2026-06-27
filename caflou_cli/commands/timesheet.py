import json
import sys
from datetime import date, datetime, timezone, timedelta
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, load_cache
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
)

app = typer.Typer(help="Timesheet commands.")

_LIST_HEADERS = ["ID", "DATE", "HOURS", "PROJECT", "TASK"]


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("date") or "-",
        r.get("hours") or "-",
        r.get("project_name") or "-",
        r.get("task_name") or "-",
    ]


def _parse_filters(raw: list[str]) -> dict:
    filters: dict = {}
    for f in raw:
        if "=" not in f:
            error(f"Invalid filter '{f}'. Use key=value format.")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters


def _read_json_input(from_file: Optional[str]) -> dict:
    if not from_file:
        error("Provide input via --from-file <path> or --from-file - (stdin).")
    try:
        if from_file == "-":
            raw = sys.stdin.read()
        else:
            raw = open(from_file).read()
        return json.loads(raw)
    except FileNotFoundError:
        error(f"File not found: {from_file}")
    except json.JSONDecodeError as e:
        error(f"Invalid JSON: {e}")


# ── read commands ─────────────────────────────────────────────────────────────

@app.command("list")
def timesheet_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List timesheets."""
    client = get_client(account)
    filters = _parse_filters(filter)

    if all_pages:
        results = client.list_all("timesheets", filters=filters)
        enrich_from_entity(client.account_id, "timesheets", results)
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.list("timesheets", page=page, per=per, filters=filters)
        results = data.get("results", [])
        enrich_from_entity(client.account_id, "timesheets", results)
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])


@app.command("get")
def timesheet_get(
    id: int = typer.Argument(..., help="Timesheet ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a timesheet entry."""
    client = get_client(account)
    data = client.get(f"timesheets/{id}")
    enrich_from_entity(client.account_id, "timesheets", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


# ── template command ──────────────────────────────────────────────────────────

@app.command("template")
def timesheet_template(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Print a minimal JSON skeleton for timesheet entry creation.

    Example:
        caflou timesheet template > new_entry.json
        caflou timesheet create --from-file new_entry.json
    """
    client = get_client(account)

    def first_id(cache_type: str) -> Optional[int]:
        cache = load_cache(client.account_id, cache_type)
        if cache:
            recs = cache.get("records", [])
            if recs:
                return recs[0]["id"]
        return None

    rate_type_id = first_id("rate_types")
    work_type_id = first_id("work_types")
    timesheet_status_id = first_id("timesheet_statuses")

    today = date.today().isoformat()
    start = f"{today}T09:00:00+02:00"
    end = f"{today}T10:00:00+02:00"

    notes = [
        "Remove this _comment key before submitting.",
        "Required fields: name, hours, value, unit, rate_type_id, start_time, end_time.",
        "rate_type_id is mandatory — run 'caflou masterdata sync rate_types' then 'caflou masterdata list rate_types' to find valid IDs.",
        "start_time and end_time are ISO 8601 datetimes (e.g. 2026-06-27T09:00:00+02:00).",
        "unit is typically 'hour'. value is the monetary amount (hours × hourly rate).",
        "See 'caflou masterdata list work_types/timesheet_statuses' for optional field IDs.",
    ]

    skeleton = {
        "_comment": " ".join(notes),
        "name": "Work log entry",
        "start_time": start,
        "end_time": end,
        "hours": 1.0,
        "unit": "hour",
        "value": 0.0,
        "currency": "CZK",
        "rate_type_id": rate_type_id,
        "work_type_id": work_type_id,
        "timesheet_status_id": timesheet_status_id,
        "project_id": None,
        "task_id": None,
        "user_id": None,
        "description": "",
    }

    typer.echo(json.dumps(skeleton, ensure_ascii=False, indent=2))


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def timesheet_create(
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with timesheet data, or '-' to read from stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new timesheet entry from a JSON body.

    Required fields: name, hours, value, unit, rate_type_id, start_time, end_time.
    Use 'caflou timesheet template' to generate a skeleton.

    Example:
        caflou timesheet template > entry.json
        caflou timesheet create --from-file entry.json
    """
    data = _read_json_input(from_file)
    data.pop("_comment", None)

    client = get_client(account)
    result = client.post("timesheets", data)

    if json_output:
        print_json(result)
    else:
        typer.echo(f"Created timesheet entry {result.get('id')} — {result.get('name')}", err=True)
        print_record(result)


@app.command("update")
def timesheet_update(
    id: int = typer.Argument(..., help="Timesheet entry ID."),
    hours: Optional[float] = typer.Option(None, "--hours", help="Updated number of hours."),
    status_id: Optional[int] = typer.Option(
        None, "--status-id", help="New timesheet status ID (see 'caflou masterdata list timesheet_statuses')."
    ),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with fields to update, or '-' for stdin. Merged with any explicit flags.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update a timesheet entry.

    The API supports updating: hours and status.

    Examples:
        caflou timesheet update 12345 --hours 2.5
        caflou timesheet update 12345 --status-id <id>
        caflou timesheet update 12345 --from-file changes.json
    """
    payload: dict = {}

    if from_file is not None:
        payload.update(_read_json_input(from_file))
        payload.pop("_comment", None)

    if hours is not None:
        payload["hours"] = hours
    if status_id is not None:
        payload["status"] = status_id

    if not payload:
        error("Nothing to update. Provide --hours, --status-id, or --from-file.")

    client = get_client(account)
    result = client.patch(f"timesheets/{id}", payload)

    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def timesheet_delete(
    id: int = typer.Argument(..., help="Timesheet entry ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a timesheet entry. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    if not force:
        entry = client.get(f"timesheets/{id}")
        name = entry.get("name") or f"id={id}"
        hours = entry.get("hours") or "?"
        d = entry.get("date") or ""
        confirmed = typer.confirm(
            f"Delete timesheet entry '{name}' ({hours}h on {d})?", default=False
        )
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"timesheets/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted timesheet entry {id}.")
