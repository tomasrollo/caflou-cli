from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity
from caflou_cli.output import (
    error, not_implemented, print_json, print_pagination, print_record, print_table,
)

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


def _parse_filters(raw: list[str]) -> dict:
    filters: dict = {}
    for f in raw:
        if "=" not in f:
            error(f"Invalid filter '{f}'. Use key=value format.")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters


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
    filters = _parse_filters(filter)

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


@app.command("create")
def task_create() -> None:
    """Create a new task. [NOT IMPLEMENTED]"""
    not_implemented("task create")


@app.command("update")
def task_update(id: int = typer.Argument(..., help="Task ID.")) -> None:
    """Update a task. [NOT IMPLEMENTED]"""
    not_implemented("task update")


@app.command("delete")
def task_delete(id: int = typer.Argument(..., help="Task ID.")) -> None:
    """Delete a task. [NOT IMPLEMENTED]"""
    not_implemented("task delete")
