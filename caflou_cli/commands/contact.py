import json
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, find_in_cache, load_cache
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
)
from caflou_cli.commands._common import parse_filters, read_json_input, run_list

app = typer.Typer(help="Contact management commands.")

_LIST_HEADERS = ["ID", "NAME", "COMPANY", "EMAIL"]


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("name") or "-",
        r.get("company_name") or "-",
        r.get("email") or "-",
    ]


# ── read commands ─────────────────────────────────────────────────────────────

@app.command("list")
def contact_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
    company_id: Optional[int] = typer.Option(
        None, "--company-id",
        help="List contacts for a specific company (uses the nested API endpoint).",
    ),
) -> None:
    """List contacts.

    Use --company-id to list contacts belonging to a specific company — this uses
    the dedicated nested API endpoint, which is the only reliable way to filter by company.
    """
    client = get_client(account)
    scope = ({"scope_type": "company", "scope_id": company_id}
             if company_id is not None else None)
    run_list(
        "contacts", _LIST_HEADERS, _list_row,
        client=client, json_output=json_output, page=page,
        per=per, all_pages=all_pages, filters=parse_filters(filter), scope=scope,
    )


@app.command("find")
def contact_find(
    name: str = typer.Argument(..., help="Name to search for (case-insensitive substring)."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cache and search API directly."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Find contacts by name or email. Searches local cache first, falls back to API.

    The cache stores names only, so email searches always fall back to the API —
    this is expected and correct. Partial email domains also work (e.g. "acme.com").

    Run 'caflou contact list --all' periodically to keep the name cache fresh.

    Examples:
        caflou contact find "Jan"
        caflou contact find "jan@acme.com"
        caflou contact find "acme.com"
        caflou contact find "Jan" --json | jq '.[0].id'
    """
    client = get_client(account)

    if not refresh:
        cached = find_in_cache(client.account_id, "contacts", name, search_fields=["name", "email"])
        if cached:
            if json_output:
                print_json(cached)
            else:
                for r in cached:
                    parts = [str(r["id"]), r.get("name") or ""]
                    if r.get("email"):
                        parts.append(r["email"])
                    typer.echo("\t".join(parts))
            return
        msg = "Cache empty, searching API..." if cached is None else "Not in cache, searching API..."
        typer.echo(msg, err=True)
    else:
        typer.echo("Searching API...", err=True)

    data = client.list("contacts", filters={"search": name})
    api_results = data.get("results", [])
    enrich_from_entity(client.account_id, "contacts", api_results)
    results = [
        {"id": r["id"], "name": r.get("name") or "", "email": r.get("email") or ""}
        for r in api_results
    ]

    if json_output:
        print_json(results)
    else:
        for r in results:
            parts = [str(r["id"]), r["name"]]
            if r.get("email"):
                parts.append(r["email"])
            typer.echo("\t".join(parts))


@app.command("get")
def contact_get(
    id: int = typer.Argument(..., help="Contact ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a contact."""
    client = get_client(account)
    data = client.get(f"contacts/{id}")
    enrich_from_entity(client.account_id, "contacts", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


@app.command("context")
def contact_context_cmd(
    id: int = typer.Argument(..., help="Contact ID."),
    all_: bool = typer.Option(False, "--all", help="Show all items, no per-section cap."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON (includes all items)."),
) -> None:
    """Show a context overview of a contact: company, projects."""
    from caflou_cli.commands._context import _DEFAULT_LIMIT, contact_context
    client = get_client(account)
    contact_context(id, client, limit=None if all_ else _DEFAULT_LIMIT, json_output=json_output)


# ── template command ──────────────────────────────────────────────────────────

@app.command("template")
def contact_template(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Print a minimal JSON skeleton for contact creation.

    Example:
        caflou contact template > new_contact.json
        caflou contact create --from-file new_contact.json
    """
    client = get_client(account)

    contact_type_id = None
    ct_cache = load_cache(client.account_id, "contact_types")
    if ct_cache:
        recs = ct_cache.get("records", [])
        if recs:
            contact_type_id = recs[0]["id"]

    skeleton = {
        "_comment": (
            "Remove this _comment key before submitting. "
            "Only 'name' is required. "
            "company_id links the contact to a company (use 'caflou company list' to find IDs). "
            "See 'caflou masterdata list contact_types' for valid contact_type_id values "
            "(populated by syncing contacts: 'caflou masterdata sync contact_types')."
        ),
        "name": "New contact",
        "company_id": None,
        "contact_type_id": contact_type_id,
        "email": "",
        "phone": "",
        "mobile": "",
        "website": "",
        "street": "",
        "city": "",
        "zip": "",
        "country": "",
        "facebook": "",
        "linkedin": "",
        "note": "",
    }

    typer.echo(json.dumps(skeleton, ensure_ascii=False, indent=2))


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def contact_create(
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with contact data, or '-' to read from stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new contact from a JSON body.

    'name' is required. 'company_id' is required to link the contact to a company —
    the API only supports creating contacts within a company context.

    Example:
        caflou contact template > contact.json
        caflou contact create --from-file contact.json
    """
    data = read_json_input(from_file)
    data.pop("_comment", None)

    company_id = data.get("company_id")
    if not company_id:
        error("'company_id' is required in the JSON body. Use 'caflou company list' to find the ID.")

    client = get_client(account)
    result = client.post(f"companies/{company_id}/contacts", data)
    enrich_from_entity(client.account_id, "contacts", [result])

    if json_output:
        print_json(result)
    else:
        typer.echo(f"Created contact {result.get('id')} — {result.get('name')}", err=True)
        print_record(result)


@app.command("update")
def contact_update(
    id: int = typer.Argument(..., help="Contact ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New contact name."),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with fields to update, or '-' for stdin. Merged with any explicit flags.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update a contact.

    Examples:
        caflou contact update 12345 --name "New name"
        caflou contact update 12345 --from-file changes.json
    """
    payload: dict = {}

    if from_file is not None:
        payload.update(read_json_input(from_file))
        payload.pop("_comment", None)

    if name is not None:
        payload["name"] = name

    if not payload:
        error("Nothing to update. Provide --name or --from-file.")

    client = get_client(account)
    # Fetch to resolve company_id — the API requires the company-nested PATCH path
    contact = client.get(f"contacts/{id}")
    company_id = contact.get("company_id")
    if not company_id:
        error(f"Contact {id} has no company_id — cannot update via API.")

    result = client.patch(f"companies/{company_id}/contacts/{id}", payload)
    enrich_from_entity(client.account_id, "contacts", [result])

    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def contact_delete(
    id: int = typer.Argument(..., help="Contact ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a contact. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    contact = client.get(f"contacts/{id}")
    company_id = contact.get("company_id")
    if not company_id:
        error(f"Contact {id} has no company_id — cannot delete via API.")

    if not force:
        name = contact.get("name") or f"id={id}"
        company = contact.get("company_name") or "no company"
        confirmed = typer.confirm(f"Delete contact '{name}' ({company})?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"companies/{company_id}/contacts/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted contact {id}.")
