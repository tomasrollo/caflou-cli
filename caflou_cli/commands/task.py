import json
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, load_cache
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
)
from caflou_cli.commands._common import parse_filters, read_json_input

app = typer.Typer(help="Task management commands.")

_LIST_HEADERS = ["ID", "NAME", "PROJECT", "STATUS", "TYPE"]


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("name", "-"),
        r.get("project_name") or "-",
        r.get("task_status_name") or "-",
        r.get("task_type_name") or "-",
    ]


# ── read commands ─────────────────────────────────────────────────────────────

@app.command("list")
def task_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List tasks."""
    client = get_client(account)
    filters = parse_filters(filter)

    if all_pages:
        results = client.list_all("tasks", filters=filters)
        enrich_from_entity(client.account_id, "tasks", results)
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.list("tasks", page=page, per=per, filters=filters)
        results = data.get("results", [])
        enrich_from_entity(client.account_id, "tasks", results)
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])


@app.command("get")
def task_get(
    id: int = typer.Argument(..., help="Task ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a task."""
    client = get_client(account)
    data = client.get(f"tasks/{id}")
    enrich_from_entity(client.account_id, "tasks", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


# ── template command ──────────────────────────────────────────────────────────

@app.command("template")
def task_template(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Print a minimal JSON skeleton for task creation.

    Pipe the output to a file, fill in the blanks, then pass to 'task create'.

    Example:
        caflou task template > new_task.json
        caflou task create --from-file new_task.json
    """
    client = get_client(account)

    # Pick first available ID from each cached type as a placeholder
    def first_id(cache_type: str) -> Optional[int]:
        cache = load_cache(client.account_id, cache_type)
        if cache:
            recs = cache.get("records", [])
            if recs:
                return recs[0]["id"]
        return None

    task_type_id = first_id("task_types")
    task_status_id = first_id("task_statuses")
    task_priority_id = first_id("task_priorities")

    notes = (
        "Remove this _comment key before submitting. "
        "project_id and company_id are optional but recommended. "
        "user_id is the primary assignee (use user_id column from 'caflou masterdata list account_users'). "
        "See 'caflou masterdata list task_types/task_statuses/task_priorities' for valid IDs. "
        "start_time and end_time are ISO 8601 (e.g. 2026-07-01T09:00:00+02:00)."
    )

    skeleton = {
        "_comment": notes,
        "name": "New task",
        "description": "",
        "project_id": None,
        "company_id": None,
        "user_id": None,
        "task_type_id": task_type_id,
        "task_status_id": task_status_id,
        "task_priority_id": task_priority_id,
        "start_time": None,
        "end_time": None,
        "planned_hours": 0.0,
        "currency": "CZK",
    }

    typer.echo(json.dumps(skeleton, ensure_ascii=False, indent=2))


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def task_create(
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with task data, or '-' to read from stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new task from a JSON body.

    Only 'name' is required. Use 'caflou task template' to generate a skeleton.

    Example:
        caflou task template > task.json
        caflou task create --from-file task.json
    """
    data = read_json_input(from_file)
    data.pop("_comment", None)

    client = get_client(account)
    result = client.post("tasks", data)

    if json_output:
        print_json(result)
    else:
        typer.echo(f"Created task {result.get('id')} — {result.get('name')}", err=True)
        print_record(result)


@app.command("update")
def task_update(
    id: int = typer.Argument(..., help="Task ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New task name."),
    status_id: Optional[int] = typer.Option(
        None, "--status-id", help="New task status ID (see 'caflou masterdata list task_statuses')."
    ),
    progress: Optional[float] = typer.Option(
        None, "--progress", help="Completion percentage (0–100)."
    ),
    finished: Optional[bool] = typer.Option(None, "--finished/--no-finished", help="Mark as finished or not."),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with fields to update, or '-' for stdin. Merged with any explicit flags.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update a task.

    Pass individual flags for common fields, or --from-file for arbitrary updates.

    Examples:
        caflou task update 12345 --status-id 1396769 --progress 100
        caflou task update 12345 --finished
        caflou task update 12345 --from-file changes.json
    """
    payload: dict = {}

    if from_file is not None:
        payload.update(read_json_input(from_file))
        payload.pop("_comment", None)

    if name is not None:
        payload["name"] = name
    if status_id is not None:
        payload["task_status_id"] = status_id
    if progress is not None:
        payload["progress"] = progress
    if finished is not None:
        payload["finished"] = finished

    if not payload:
        error("Nothing to update. Provide --name, --status-id, --progress, --finished/--no-finished, or --from-file.")

    client = get_client(account)
    result = client.patch(f"tasks/{id}", payload)

    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def task_delete(
    id: int = typer.Argument(..., help="Task ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a task. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    if not force:
        task = client.get(f"tasks/{id}")
        name = task.get("name") or f"id={id}"
        project = task.get("project_name") or "no project"
        confirmed = typer.confirm(f"Delete task '{name}' ({project})?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"tasks/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted task {id}.")
