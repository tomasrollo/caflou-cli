from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.output import (
    error, not_implemented, print_json, print_pagination, print_record, print_table,
)

app = typer.Typer(help="Invoice management commands.")

_LIST_HEADERS = ["ID", "NUMBER", "COMPANY", "CURRENCY"]


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("number") or "-",
        r.get("company_name") or "-",
        r.get("currency") or "-",
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
def invoice_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(20, "--per", help="Items per page (max 1000)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List invoices."""
    client = get_client(account)
    filters = _parse_filters(filter)

    if all_pages:
        results = client.list_all("invoices", filters=filters)
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.list("invoices", page=page, per=per, filters=filters)
        results = data.get("results", [])
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])


@app.command("get")
def invoice_get(
    id: int = typer.Argument(..., help="Invoice ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of an invoice."""
    client = get_client(account)
    data = client.get(f"invoices/{id}")
    if json_output:
        print_json(data)
    else:
        print_record(data)


@app.command("create")
def invoice_create() -> None:
    """Create a new invoice. [NOT IMPLEMENTED]"""
    not_implemented("invoice create")


@app.command("update")
def invoice_update(id: int = typer.Argument(..., help="Invoice ID.")) -> None:
    """Update an invoice. [NOT IMPLEMENTED]"""
    not_implemented("invoice update")


@app.command("delete")
def invoice_delete(id: int = typer.Argument(..., help="Invoice ID.")) -> None:
    """Delete an invoice. [NOT IMPLEMENTED]"""
    not_implemented("invoice delete")
