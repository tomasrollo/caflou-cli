import json
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, find_in_cache, load_cache
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
)
from caflou_cli.commands._common import parse_filters, read_json_input, run_list

app = typer.Typer(help="Project management commands.")

_LIST_HEADERS = ["ID", "NAME", "START", "END"]


def _list_row(r: dict) -> list:
    return [r["id"], r.get("name", "-"), r.get("start_date", "-"), r.get("end_date", "-")]


# ── read commands ─────────────────────────────────────────────────────────────

@app.command("list")
def project_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List projects."""
    client = get_client(account)
    run_list(
        "projects", _LIST_HEADERS, _list_row,
        client=client, json_output=json_output, page=page,
        per=per, all_pages=all_pages, filters=parse_filters(filter),
    )


@app.command("get")
def project_get(
    id: int = typer.Argument(..., help="Project ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a project."""
    client = get_client(account)
    data = client.get(f"projects/{id}")
    enrich_from_entity(client.account_id, "projects", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


@app.command("find")
def project_find(
    name: str = typer.Argument(..., help="Name to search for (case-insensitive substring)."),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cache and search API directly."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Find projects by name. Searches local cache first, falls back to API.

    Run 'caflou project list --all' periodically to keep the cache fresh.

    Examples:
        caflou project find "Skříň"
        caflou project find "Skříň" --json | jq '.[0].id'
    """
    client = get_client(account)

    if not refresh:
        cached = find_in_cache(client.account_id, "projects", name)
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

    data = client.list("projects", filters={"search": name})
    api_results = data.get("results", [])
    enrich_from_entity(client.account_id, "projects", api_results)
    results = [{"id": r["id"], "name": r.get("name") or ""} for r in api_results]

    if json_output:
        print_json(results)
    else:
        for r in results:
            typer.echo(f"{r['id']}\t{r['name']}")


# ── template command ──────────────────────────────────────────────────────────

@app.command("template")
def project_template(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
) -> None:
    """Print a minimal JSON skeleton for project creation.

    Example:
        caflou project template > new_project.json
        caflou project create --from-file new_project.json
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
            "user_id is the project owner (use user_id column from 'caflou masterdata list account_users'). "
            "user_ids is a list of additional team member user IDs. "
            "See 'caflou masterdata list project_types/project_statuses/project_priorities' for valid IDs."
        ),
        "name": "New project",
        "description": "",
        "company_id": None,
        "user_id": None,
        "user_ids": [],
        "project_type_id": first_id("project_types"),
        "project_status_id": first_id("project_statuses"),
        "project_priority_id": first_id("project_priorities"),
        "start_date": None,
        "end_date": None,
        "currency": "CZK",
        "planned_hours": 0.0,
    }

    typer.echo(json.dumps(skeleton, ensure_ascii=False, indent=2))


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def project_create(
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with project data, or '-' to read from stdin.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new project from a JSON body.

    Only 'name' is required. Use 'caflou project template' to generate a skeleton.

    Example:
        caflou project template > project.json
        caflou project create --from-file project.json
    """
    data = read_json_input(from_file)
    data.pop("_comment", None)

    client = get_client(account)
    result = client.post("projects", data)
    enrich_from_entity(client.account_id, "projects", [result])

    if json_output:
        print_json(result)
    else:
        typer.echo(f"Created project {result.get('id')} — {result.get('name')}", err=True)
        print_record(result)


@app.command("update")
def project_update(
    id: int = typer.Argument(..., help="Project ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New project name."),
    status_id: Optional[int] = typer.Option(
        None, "--status-id", help="New project status ID (see 'caflou masterdata list project_statuses')."
    ),
    progress: Optional[float] = typer.Option(
        None, "--progress", help="Completion percentage (0–100)."
    ),
    finished: Optional[bool] = typer.Option(None, "--finished/--no-finished", help="Mark as finished or not."),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with fields to update, or '-' for stdin. Merged with any explicit flags.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update a project.

    Pass individual flags for common fields, or --from-file for arbitrary updates.

    Examples:
        caflou project update 12345 --name "New name"
        caflou project update 12345 --status-id 1291868 --finished
        caflou project update 12345 --from-file changes.json
    """
    payload: dict = {}

    if from_file is not None:
        payload.update(read_json_input(from_file))
        payload.pop("_comment", None)

    if name is not None:
        payload["name"] = name
    if status_id is not None:
        payload["project_status_id"] = status_id
    if progress is not None:
        payload["progress"] = progress
    if finished is not None:
        payload["finished"] = finished

    if not payload:
        error("Nothing to update. Provide --name, --status-id, --progress, --finished/--no-finished, or --from-file.")

    client = get_client(account)
    result = client.patch(f"projects/{id}", payload)
    enrich_from_entity(client.account_id, "projects", [result])

    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def project_delete(
    id: int = typer.Argument(..., help="Project ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a project. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    if not force:
        project = client.get(f"projects/{id}")
        name = project.get("name") or f"id={id}"
        company = project.get("company_name") or "no company"
        confirmed = typer.confirm(f"Delete project '{name}' ({company})?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"projects/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted project {id}.")
