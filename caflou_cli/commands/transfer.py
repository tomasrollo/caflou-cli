import json
import sys
from datetime import date
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, load_cache
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
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


# ── template command ──────────────────────────────────────────────────────────

@app.command("template")
def transfer_template(
    kind: str = typer.Argument("income", help="Transfer kind: 'income' or 'expense'."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Print a minimal JSON skeleton for transfer creation.

    Example:
        caflou transfer template income > new_transfer.json
        caflou transfer create --from-file new_transfer.json
    """
    if kind not in ("income", "expense"):
        error(f"Invalid kind '{kind}'. Must be 'income' or 'expense'.")

    client = get_client(account)

    category_id = None
    cat_cache = load_cache(client.account_id, "transfer_categories")
    if cat_cache:
        recs = cat_cache.get("records", [])
        if recs:
            category_id = recs[0]["id"]

    skeleton = {
        "_comment": (
            "Remove this _comment key before submitting. "
            "Required fields: name, kind, currency, date, value. "
            "kind must be 'income' or 'expense'. "
            "date is the accounting/entry date (YYYY-MM-DD); payment_date is when money actually moved. "
            "invoice_id links this transfer to a document. "
            "See 'caflou masterdata list transfer_categories' for category IDs."
        ),
        "name": f"New {kind} transfer",
        "kind": kind,
        "currency": "CZK",
        "date": str(date.today()),
        "value": 0.0,
        "category_id": category_id,
        "company_id": None,
        "project_id": None,
        "invoice_id": None,
        "payment_date": None,
        "done": False,
        "description": "",
        "reference_number": "",
    }

    typer.echo(json.dumps(skeleton, ensure_ascii=False, indent=2))


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def transfer_create(
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with transfer data, or '-' to read from stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new transfer from a JSON body.

    Required fields: name, kind ('income'/'expense'), currency, date, value.

    Example:
        caflou transfer template expense > transfer.json
        caflou transfer create --from-file transfer.json
    """
    data = _read_json_input(from_file)
    data.pop("_comment", None)

    client = get_client(account)
    result = client.post("transfers", data)

    if json_output:
        print_json(result)
    else:
        typer.echo(f"Created transfer {result.get('id')} — {result.get('name')}", err=True)
        print_record(result)


@app.command("update")
def transfer_update(
    id: int = typer.Argument(..., help="Transfer ID."),
    paid: Optional[bool] = typer.Option(None, "--paid/--no-paid", help="Mark as paid or unpaid."),
    payment_date: Optional[str] = typer.Option(
        None, "--payment-date", help="Payment date (YYYY-MM-DD). Sets --paid implicitly."
    ),
    real_value: Optional[float] = typer.Option(
        None, "--real-value", help="Actual payment amount (if different from invoiced value)."
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update a transfer.

    The API supports updating: paid status, payment date, and real value.

    Examples:
        caflou transfer update 12345 --paid --payment-date 2026-06-01
        caflou transfer update 12345 --real-value 9500.00
        caflou transfer update 12345 --no-paid
    """
    payload: dict = {}

    if paid is not None:
        payload["done"] = paid
    if payment_date is not None:
        payload["payment_date"] = payment_date
        if paid is None:
            payload["done"] = True
    if real_value is not None:
        payload["real_value"] = real_value

    if not payload:
        error("Nothing to update. Provide --paid/--no-paid, --payment-date, or --real-value.")

    client = get_client(account)
    result = client.patch(f"transfers/{id}", payload)

    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def transfer_delete(
    id: int = typer.Argument(..., help="Transfer ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a transfer. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    if not force:
        transfer = client.get(f"transfers/{id}")
        name = transfer.get("name") or f"id={id}"
        value = transfer.get("value")
        currency = transfer.get("currency") or ""
        confirmed = typer.confirm(
            f"Delete transfer '{name}' ({value} {currency})?", default=False
        )
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"transfers/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted transfer {id}.")
