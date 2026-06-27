import json
import sys
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.cache import enrich_from_entity, load_cache
from caflou_cli.output import (
    error, print_json, print_pagination, print_record, print_table,
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
    filters = _parse_filters(filter)

    if all_pages:
        results = client.list_all("projects", filters=filters)
        enrich_from_entity(client.account_id, "projects", results)
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.list("projects", page=page, per=per, filters=filters)
        results = data.get("results", [])
        enrich_from_entity(client.account_id, "projects", results)
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
    enrich_from_entity(client.account_id, "projects", [data])
    if json_output:
        print_json(data)
    else:
        print_record(data)


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
    data = _read_json_input(from_file)
    data.pop("_comment", None)

    client = get_client(account)
    result = client.post("projects", data)

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
        payload.update(_read_json_input(from_file))
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
