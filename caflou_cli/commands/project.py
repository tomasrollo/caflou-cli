from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.output import (
    error, not_implemented, print_json, print_pagination, print_record, print_table,
)

app = typer.Typer(help="Project management commands.")

_LIST_HEADERS = ["ID", "NAME", "START", "END"]


def _list_row(r: dict) -> list:
    return [r["id"], r.get("name", "-"), r.get("start_date", "-"), r.get("end_date", "-")]


def _parse_filters(raw: list[str]) -> dict:
    filters: dict = {}
    for f in raw:
        if "=" not in f:
            error(f"Invalid filter '{f}'. Use key=value format.")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters


@app.command("list")
def project_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(20, "--per", help="Items per page (max 1000)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List projects."""
    client = get_client(account)
    filters = _parse_filters(filter)

    if all_pages:
        results = client.list_all("projects", filters=filters)
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.list("projects", page=page, per=per, filters=filters)
        results = data.get("results", [])
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])


@app.command("get")
def project_get(
    id: int = typer.Argument(..., help="Project ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a project."""
    client = get_client(account)
    data = client.get(f"projects/{id}")
    if json_output:
        print_json(data)
    else:
        print_record(data)


@app.command("create")
def project_create() -> None:
    """Create a new project. [NOT IMPLEMENTED]"""
    not_implemented("project create")


@app.command("update")
def project_update(id: int = typer.Argument(..., help="Project ID.")) -> None:
    """Update a project. [NOT IMPLEMENTED]"""
    not_implemented("project update")


@app.command("delete")
def project_delete(id: int = typer.Argument(..., help="Project ID.")) -> None:
    """Delete a project. [NOT IMPLEMENTED]"""
    not_implemented("project delete")
