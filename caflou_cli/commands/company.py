import json
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, find_in_cache, load_cache
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
)
from caflou_cli.commands._common import parse_filters, read_json_input, run_list

app = typer.Typer(help="Company management commands.")

_LIST_HEADERS = ["ID", "NAME"]


def _list_row(r: dict) -> list:
    return [r["id"], r.get("name") or "-"]


# ── read commands ─────────────────────────────────────────────────────────────

@app.command("list")
def company_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
    active: bool = typer.Option(False, "--active", help="Only active companies."),
    company_type_id: list[int] = typer.Option([], "--company-type-id", help="Filter by company type ID (repeatable)."),
) -> None:
    """List companies.

    Use --active and --company-type-id for confirmed server-side API filters.
    """
    client = get_client(account)
    filters = parse_filters(filter)
    if active:
        filters["active"] = "true"
    if company_type_id:
        filters["company_type_ids"] = ",".join(str(i) for i in company_type_id)
    run_list(
        "companies", _LIST_HEADERS, _list_row,
        client=client, json_output=json_output, page=page,
        per=per, all_pages=all_pages, filters=filters,
    )


@app.command("get")
def company_get(
    id: int = typer.Argument(..., help="Company ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a company."""
    client = get_client(account)
    data = client.get(f"companies/{id}")
    enrich_from_entity(client.account_id, "companies", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


@app.command("context")
def company_context_cmd(
    id: int = typer.Argument(..., help="Company ID."),
    all_: bool = typer.Option(False, "--all", help="Show all items, no per-section cap."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON (includes all items)."),
) -> None:
    """Show a context overview of a company: contacts, projects, documents."""
    from caflou_cli.commands._context import _DEFAULT_LIMIT, company_context
    client = get_client(account)
    company_context(id, client, limit=None if all_ else _DEFAULT_LIMIT, json_output=json_output)


@app.command("find")
def company_find(
    name: str = typer.Argument(..., help="Name to search for (case-insensitive substring)."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cache and search API directly."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Find companies by name. Searches local cache first, falls back to API.

    Run 'caflou company list --all' periodically to keep the cache fresh.

    Examples:
        caflou company find "Acme"
        caflou company find "Acme" --json | jq '.[0].id'
    """
    client = get_client(account)

    if not refresh:
        cached = find_in_cache(client.account_id, "companies", name)
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

    data = client.list("companies", filters={"search": name})
    api_results = data.get("results", [])
    enrich_from_entity(client.account_id, "companies", api_results)
    results = [{"id": r["id"], "name": r.get("name") or ""} for r in api_results]

    if json_output:
        print_json(results)
    else:
        for r in results:
            typer.echo(f"{r['id']}\t{r['name']}")


# ── template command ──────────────────────────────────────────────────────────

@app.command("template")
def company_template(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Print a minimal JSON skeleton for company creation.

    Example:
        caflou company template > new_company.json
        caflou company create --from-file new_company.json
    """
    client = get_client(account)

    def first_id(cache_type: str) -> Optional[int]:
        cache = load_cache(client.account_id, cache_type)
        if cache:
            recs = cache.get("records", [])
            if recs:
                return recs[0]["id"]
        return None

    skeleton = {
        "_comment": (
            "Remove this _comment key before submitting. "
            "Only 'name' is required. "
            "kind: 'legal_entity' (registered company) or 'individual' (sole trader / natural person). "
            "target_user_id is the account manager (use user_id column from 'caflou masterdata list account_users'). "
            "See 'caflou masterdata list company_types/company_statuses/company_phases' for valid IDs."
        ),
        "name": "New company",
        "kind": "legal_entity",
        "company_type_id": first_id("company_types"),
        "company_status_id": first_id("company_statuses"),
        "company_phase_id": first_id("company_phases"),
        "target_user_id": None,
        "email": "",
        "phone": "",
        "website": "",
        "street": "",
        "city": "",
        "zip": "",
        "country": "CZ",
        "id_num": "",
        "tax_num": "",
        "vat_payer": False,
        "description": "",
    }

    typer.echo(json.dumps(skeleton, ensure_ascii=False, indent=2))


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def company_create(
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with company data, or '-' to read from stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new company from a JSON body.

    Only 'name' is required. Use 'caflou company template' to generate a skeleton.

    Example:
        caflou company template > company.json
        caflou company create --from-file company.json
    """
    data = read_json_input(from_file)
    data.pop("_comment", None)

    client = get_client(account)
    result = client.post("companies", data)
    enrich_from_entity(client.account_id, "companies", [result])

    if json_output:
        print_json(result)
    else:
        typer.echo(f"Created company {result.get('id')} — {result.get('name')}", err=True)
        print_record(result)


@app.command("update")
def company_update(
    id: int = typer.Argument(..., help="Company ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New company name."),
    status_id: Optional[int] = typer.Option(
        None, "--status-id", help="New company status ID (see 'caflou masterdata list company_statuses')."
    ),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with fields to update, or '-' for stdin. Merged with any explicit flags.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update a company.

    Pass individual flags for common fields, or --from-file for arbitrary updates.

    Examples:
        caflou company update 12345 --name "New name"
        caflou company update 12345 --status-id 1411946
        caflou company update 12345 --from-file changes.json
    """
    payload: dict = {}

    if from_file is not None:
        payload.update(read_json_input(from_file))
        payload.pop("_comment", None)

    if name is not None:
        payload["name"] = name
    if status_id is not None:
        payload["company_status_id"] = status_id

    if not payload:
        error("Nothing to update. Provide --name, --status-id, or --from-file.")

    client = get_client(account)
    result = client.patch(f"companies/{id}", payload)
    enrich_from_entity(client.account_id, "companies", [result])

    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def company_delete(
    id: int = typer.Argument(..., help="Company ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a company. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    if not force:
        company = client.get(f"companies/{id}")
        name = company.get("name") or f"id={id}"
        confirmed = typer.confirm(f"Delete company '{name}'?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"companies/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted company {id}.")
