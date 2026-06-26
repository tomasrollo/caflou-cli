from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity
from caflou_cli.output import (
    error, not_implemented, print_json, print_pagination, print_record, print_table,
)

app = typer.Typer(help="Transfer (cashflow) commands.")

_LIST_HEADERS = ["ID", "COMPANY", "CURRENCY", "INVOICE"]


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("company_name") or "-",
        r.get("currency") or "-",
        r.get("invoice_number") or "-",
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
def transfer_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List transfers (cashflow entries)."""
    client = get_client(account)
    filters = _parse_filters(filter)

    if all_pages:
        results = client.list_all("transfers", filters=filters)
        enrich_from_entity(client.account_id, "transfers", results)
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.list("transfers", page=page, per=per, filters=filters)
        results = data.get("results", [])
        enrich_from_entity(client.account_id, "transfers", results)
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])


@app.command("get")
def transfer_get(
    id: int = typer.Argument(..., help="Transfer ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a transfer."""
    client = get_client(account)
    data = client.get(f"transfers/{id}")
    enrich_from_entity(client.account_id, "transfers", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


@app.command("create")
def transfer_create() -> None:
    """Create a new transfer. [NOT IMPLEMENTED]"""
    not_implemented("transfer create")


@app.command("update")
def transfer_update(id: int = typer.Argument(..., help="Transfer ID.")) -> None:
    """Update a transfer. [NOT IMPLEMENTED]"""
    not_implemented("transfer update")


@app.command("delete")
def transfer_delete(id: int = typer.Argument(..., help="Transfer ID.")) -> None:
    """Delete a transfer. [NOT IMPLEMENTED]"""
    not_implemented("transfer delete")
