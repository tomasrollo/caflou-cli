import json
from datetime import date
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, load_cache
from caflou_cli.output import (
    error, not_implemented, print_json, print_pagination, print_record, print_table,
)
from caflou_cli.commands._common import parse_filters, read_json_input, run_list

app = typer.Typer(help="Document commands (invoices, offers, delivery notes, etc.).")

_LIST_HEADERS = ["ID", "NUMBER", "COMPANY", "CURRENCY"]


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("number") or "-",
        r.get("company_name") or "-",
        r.get("currency") or "-",
    ]


# ── read commands ─────────────────────────────────────────────────────────────

@app.command("list")
def document_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List documents (invoices, offers, delivery notes, etc.)."""
    client = get_client(account)
    run_list(
        "invoices", _LIST_HEADERS, _list_row,
        client=client, json_output=json_output, page=page,
        per=per, all_pages=all_pages, filters=parse_filters(filter),
    )


@app.command("get")
def document_get(
    id: int = typer.Argument(..., help="Document ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a document."""
    client = get_client(account)
    data = client.get(f"invoices/{id}")
    enrich_from_entity(client.account_id, "invoices", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


# ── template command ──────────────────────────────────────────────────────────

@app.command("template")
def document_template(
    kind: str = typer.Argument(
        ...,
        help="Document kind. One of: issued, received, proforma, proforma_received, offer, "
             "offer_received, order_issued, order_received, delivery, contract, contract_received, "
             "storno, storno_received, tax_receipt, tax_receipt_received",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Print a minimal JSON skeleton for document creation.

    Pipe the output to a file, fill in the blanks, then pass to 'document create'.

    Example:
        caflou document template issued > new_invoice.json
        caflou document create --from-file new_invoice.json
    """
    client = get_client(account)

    # Find a matching numeric_row from cache
    cache = load_cache(client.account_id, "numeric_rows")
    numeric_row_id = None
    numeric_row_name = None
    if cache:
        rows = cache.get("records", [])
        matches = [r for r in rows if r.get("kind") == kind]
        if matches:
            numeric_row_id = matches[0]["id"]
            numeric_row_name = matches[0].get("name", "")

    if numeric_row_id is None:
        typer.echo(
            f"Warning: no cached numeric_row with kind '{kind}'. "
            "Run 'caflou masterdata sync numeric_rows' or set numeric_row_id manually.",
            err=True,
        )

    # Find a VAT rate from cache for the placeholder line item
    vat_cache = load_cache(client.account_id, "vat_rates")
    vat_rate_id = None
    if vat_cache:
        vat_records = vat_cache.get("records", [])
        if vat_records:
            vat_rate_id = vat_records[0]["id"]

    # Kinds where date_of_tax + date_of_payment are required (confirmed by API testing)
    _financial_kinds = {
        "issued", "received",
        "proforma", "proforma_received",
        "storno", "storno_received",
        "contract", "contract_received",
        "tax_receipt", "tax_receipt_received",
    }
    is_financial = kind in _financial_kinds

    # Received documents from an external party require from_company_id (the supplier)
    _needs_supplier = {"received", "proforma_received", "offer_received",
                       "order_issued", "storno_received", "contract_received",
                       "tax_receipt_received"}
    needs_supplier = kind in _needs_supplier

    # The POST body 'kind' field uses broader categories; storno/contract/tax_receipt
    # documents are distinguished by numeric_row_id, not by a unique kind string.
    _post_kind_map = {
        "storno":              "issued",
        "storno_received":     "received",
        "contract":            "issued",
        "contract_received":   "received",
        "tax_receipt":         "issued",
        "tax_receipt_received":"issued",
    }
    post_kind = _post_kind_map.get(kind, kind)

    extra_notes = []
    if is_financial:
        extra_notes.append("date_of_tax and date_of_payment are required by the API (undocumented)")
    if needs_supplier:
        extra_notes.append("from_company_id (supplier) is required for this document type")
    if post_kind != kind:
        extra_notes.append(
            f"kind is set to '{post_kind}' (the API's broader category); "
            f"the specific document type is determined by numeric_row_id"
        )

    skeleton = {
        "_comment": (
            "Remove this _comment key before submitting. "
            f"numeric_row: {numeric_row_name or kind}. "
            + ("; ".join(extra_notes) + ". " if extra_notes else "")
            + "See 'caflou masterdata list vat_rates' for VAT rate IDs, "
            "'caflou masterdata list numeric_rows' for series IDs."
        ),
        "name": f"New {kind} document",
        "kind": post_kind,
        "currency": "CZK",
        "date_of_issue": str(date.today()),
        **({"date_of_tax": str(date.today()), "date_of_payment": str(date.today())} if is_financial else {}),
        **({"from_company_id": None} if needs_supplier else {}),
        "numeric_row_id": numeric_row_id,
        "to_company_id": None,
        "note": "",
        "invoice_items_attributes": [
            {
                "name": "Item description",
                "amount": 1,
                "value": 0.0,
                "unit": "ks",
                "vat_rate_id": vat_rate_id,
            }
        ],
    }

    typer.echo(json.dumps(skeleton, ensure_ascii=False, indent=2))


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def document_create(
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with document data, or '-' to read from stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new document from a JSON body.

    Required JSON fields: name, kind, currency, date_of_issue.

    Example:
        caflou document template issued > doc.json
        caflou document create --from-file doc.json
    """
    data = read_json_input(from_file)
    data.pop("_comment", None)

    client = get_client(account)
    result = client.post("invoices", data)

    if json_output:
        print_json(result)
    else:
        typer.echo(
            f"Created document {result.get('id')} — {result.get('number') or '(no number yet)'}",
            err=True,
        )
        print_record(result)


@app.command("update")
def document_update(
    id: int = typer.Argument(..., help="Document ID."),
    paid: Optional[bool] = typer.Option(None, "--paid/--no-paid", help="Mark as paid or unpaid."),
    payment_date: Optional[str] = typer.Option(
        None, "--payment-date", help="Payment date (YYYY-MM-DD). Sets --paid implicitly."
    ),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with invoice_items_attributes to replace line items, or '-' for stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update a document.

    The API supports updating: paid status, payment date, and line items.

    Examples:
        caflou document update 12345 --paid --payment-date 2024-06-01
        caflou document update 12345 --no-paid
        caflou document update 12345 --from-file items.json
    """
    payload: dict = {}

    if paid is not None:
        payload["paid"] = paid
    if payment_date is not None:
        payload["payment_date"] = payment_date
        if paid is None:
            payload["paid"] = True
    if from_file is not None:
        items_data = read_json_input(from_file)
        if isinstance(items_data, list):
            payload["invoice_items_attributes"] = items_data
        elif isinstance(items_data, dict) and "invoice_items_attributes" in items_data:
            payload["invoice_items_attributes"] = items_data["invoice_items_attributes"]
        else:
            error("--from-file for update must contain a JSON array of line items, "
                  "or an object with an 'invoice_items_attributes' key.")

    if not payload:
        error("Nothing to update. Provide --paid/--no-paid, --payment-date, or --from-file.")

    client = get_client(account)
    result = client.patch(f"invoices/{id}", payload)

    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def document_delete(
    id: int = typer.Argument(..., help="Document ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a document. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    if not force:
        doc = client.get(f"invoices/{id}")
        number = doc.get("number") or f"id={id}"
        company = doc.get("company_name") or "unknown company"
        confirmed = typer.confirm(f"Delete document {number} ({company})?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"invoices/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted document {id}.")
