import json
import sys
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
)

app = typer.Typer(help="Contact management commands.")

_LIST_HEADERS = ["ID", "NAME", "COMPANY", "EMAIL"]


def _list_row(r: dict) -> list:
    return [
        r["id"],
        r.get("name") or "-",
        r.get("company_name") or "-",
        r.get("email") or "-",
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
def contact_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List contacts."""
    client = get_client(account)
    filters = _parse_filters(filter)

    if all_pages:
        results = client.list_all("contacts", filters=filters)
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.list("contacts", page=page, per=per, filters=filters)
        results = data.get("results", [])
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])


@app.command("get")
def contact_get(
    id: int = typer.Argument(..., help="Contact ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a contact."""
    client = get_client(account)
    data = client.get(f"contacts/{id}")
    if json_output:
        print_json(data)
    else:
        print_record(data)


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
    skeleton = {
        "_comment": (
            "Remove this _comment key before submitting. "
            "Only 'name' is required. "
            "company_id links the contact to a company (use 'caflou company list' to find IDs). "
            "contact_type_id is optional — Caflou does not expose contact types via the API."
        ),
        "name": "New contact",
        "company_id": None,
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
    data = _read_json_input(from_file)
    data.pop("_comment", None)

    company_id = data.get("company_id")
    if not company_id:
        error("'company_id' is required in the JSON body. Use 'caflou company list' to find the ID.")

    client = get_client(account)
    result = client.post(f"companies/{company_id}/contacts", data)

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
        payload.update(_read_json_input(from_file))
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
