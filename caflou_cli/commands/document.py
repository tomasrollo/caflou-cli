import json
from datetime import date
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, find_in_cache, load_cache
from caflou_cli.output import (
    error, not_implemented, print_json, print_pagination, print_record, print_table,
)
from caflou_cli.commands._common import parse_filters, read_json_input, run_list

app = typer.Typer(help="Document commands (invoices, offers, delivery notes, etc.).")

_LIST_HEADERS = ["ID", "NUMBER", "COMPANY", "CURRENCY"]

# ── document kind rules ───────────────────────────────────────────────────────
# All kinds a user may specify (logical names, not necessarily API POST values).
_VALID_KINDS = {
    "issued", "received",
    "proforma", "proforma_received",
    "offer", "offer_received",
    "order_issued", "order_received",
    "delivery",
    "storno", "storno_received",
    "contract", "contract_received",
    "tax_receipt", "tax_receipt_received",
}

# Kinds requiring date_of_tax and date_of_payment (confirmed by API testing).
_FINANCIAL_KINDS = {
    "issued", "received",
    "proforma", "proforma_received",
    "storno", "storno_received",
    "contract", "contract_received",
    "tax_receipt", "tax_receipt_received",
}

# Kinds where the document is received from an external party — supplier required.
_NEEDS_SUPPLIER = {
    "received", "proforma_received", "offer_received",
    "order_issued", "storno_received", "contract_received",
    "tax_receipt_received",
}

# The POST body 'kind' field uses broader categories; storno/contract/tax_receipt
# are distinguished from plain issued/received only by numeric_row_id.
_POST_KIND_MAP = {
    "storno":               "issued",
    "storno_received":      "received",
    "contract":             "issued",
    "contract_received":    "received",
    "tax_receipt":          "issued",
    "tax_receipt_received": "issued",
}


def _validate_document_body(data: dict) -> dict:
    """Validate and normalise a document body before POSTing.

    - Rejects unknown kind values with a clear error.
    - Checks required fields for the given kind.
    - Translates logical kinds (storno, contract, tax_receipt) to their API kind.

    Modifies and returns the data dict.
    """
    kind = data.get("kind")
    if not kind:
        error(
            "'kind' is required. "
            f"Valid values: {', '.join(sorted(_VALID_KINDS))}."
        )

    if kind not in _VALID_KINDS:
        error(
            f"Unknown document kind '{kind}'. "
            f"Valid values: {', '.join(sorted(_VALID_KINDS))}."
        )

    for field in ("name", "currency", "date_of_issue"):
        if not data.get(field):
            error(f"'{field}' is required for all document kinds.")

    if kind in _FINANCIAL_KINDS:
        for field in ("date_of_tax", "date_of_payment"):
            if not data.get(field):
                error(
                    f"'{field}' is required for '{kind}' documents "
                    "(undocumented API requirement for financial document types)."
                )

    if kind in _NEEDS_SUPPLIER:
        if not data.get("from_company_id"):
            error(
                f"'from_company_id' (supplier) is required for '{kind}' documents. "
                "Use 'caflou company list' to find the supplier's ID."
            )

    data["kind"] = _POST_KIND_MAP.get(kind, kind)
    return data


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("number") or "-",
        r.get("company_name") or "-",
        r.get("currency") or "-",
    ]


# ── read commands ─────────────────────────────────────────────────────────────

_LIST_KINDS = ("offer", "order", "proforma", "invoice", "delivery")


@app.command("list")
def document_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
    kind: Optional[str] = typer.Option(None, "--kind",
        help=f"Filter by document kind: {', '.join(_LIST_KINDS)}."),
    unpaid: bool = typer.Option(False, "--unpaid", help="Only unpaid documents."),
    issued: bool = typer.Option(False, "--issued", help="Only issued documents."),
    company_id: Optional[int] = typer.Option(None, "--company-id", help="Filter to documents for a company."),
    project_id: Optional[int] = typer.Option(None, "--project-id", help="Filter to documents for a project."),
) -> None:
    """List documents (invoices, offers, delivery notes, etc.).

    Use --company-id or --project-id for server-side scoping (scope_type/scope_id).
    Use --kind to filter by document type (confirmed server-side API param).
    Use --unpaid / --issued for confirmed server-side state filters.
    """
    if kind is not None and kind not in _LIST_KINDS:
        from caflou_cli.output import error
        error(f"Unknown kind '{kind}'. Valid values: {', '.join(_LIST_KINDS)}.")
    client = get_client(account)
    filters = parse_filters(filter)
    if unpaid:
        filters["unpaids"] = "true"
    if issued:
        filters["issueds"] = "true"
    # kind, scope_type, scope_id are all raw params (not filter[]-wrapped)
    scope: dict = {}
    if company_id is not None:
        scope.update({"scope_type": "company", "scope_id": company_id})
    elif project_id is not None:
        scope.update({"scope_type": "project", "scope_id": project_id})
    if kind is not None:
        scope["kind"] = kind
    run_list(
        "invoices", _LIST_HEADERS, _list_row,
        client=client, json_output=json_output, page=page,
        per=per, all_pages=all_pages, filters=filters, scope=scope or None,
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


@app.command("find")
def document_find(
    name: str = typer.Argument(..., help="Name to search for (case-insensitive substring)."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cache and search API directly."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Find documents by name. Searches local cache first, falls back to API.

    Run 'caflou document list --all' periodically to keep the cache fresh.

    Examples:
        caflou document find "Invoice"
        caflou document find "Invoice" --json | jq '.[0].id'
    """
    client = get_client(account)

    if not refresh:
        cached = find_in_cache(client.account_id, "documents", name)
        if cached:
            if json_output:
                print_json(cached)
            else:
                for r in cached:
                    typer.echo(f"{r['id']}\t{r['name']}")
            return
        msg = "Cache empty, searching API..." if cached is None else "Not in cache, searching API..."
        typer.echo(msg, err=True)
    else:
        typer.echo("Searching API...", err=True)

    data = client.list("invoices", filters={"search": name})
    api_results = data.get("results", [])
    enrich_from_entity(client.account_id, "invoices", api_results)
    results = [{"id": r["id"], "name": r.get("name") or ""} for r in api_results]

    if json_output:
        print_json(results)
    else:
        for r in results:
            typer.echo(f"{r['id']}\t{r['name']}")


@app.command("context")
def document_context_cmd(
    id: int = typer.Argument(..., help="Document ID."),
    all_: bool = typer.Option(False, "--all", help="Show all items, no per-section cap."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON (includes all items)."),
) -> None:
    """Show a context overview of a document: buyer company, project, payments."""
    from caflou_cli.commands._context import _DEFAULT_LIMIT, document_context
    client = get_client(account)
    document_context(id, client, limit=None if all_ else _DEFAULT_LIMIT, json_output=json_output)


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
    if kind not in _VALID_KINDS:
        error(
            f"Unknown document kind '{kind}'. "
            f"Valid values: {', '.join(sorted(_VALID_KINDS))}."
        )

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

    is_financial = kind in _FINANCIAL_KINDS
    needs_supplier = kind in _NEEDS_SUPPLIER
    post_kind = _POST_KIND_MAP.get(kind, kind)

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
    data = _validate_document_body(data)

    client = get_client(account)
    result = client.post("invoices", data)
    enrich_from_entity(client.account_id, "invoices", [result])

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
    enrich_from_entity(client.account_id, "invoices", [result])

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
