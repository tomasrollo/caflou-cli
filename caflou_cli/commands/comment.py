import json
from typing import Optional

import typer

from caflou_cli.api import get_client
from caflou_cli.output import error, print_json, print_pagination, print_record, print_table
from caflou_cli.commands._common import parse_filters, read_json_input

app = typer.Typer(help="Comment commands.")

_LIST_HEADERS = ["ID", "USER", "TYPE", "ENTITY ID", "TEXT"]

# Likely commented_type values (Rails class names — not validated by the API spec).
_TYPE_HINT = "Task, Invoice, Project, Company, Contact, Transfer, Timesheet"


def _list_row(r: dict) -> list:
    text = (r.get("text") or "").replace("\n", " ")
    return [
        r.get("id"),
        r.get("user_name") or "-",
        r.get("commented_type") or "-",
        r.get("commented_id") or "-",
        text[:60] + ("…" if len(text) > 60 else ""),
    ]


# ── read commands ─────────────────────────────────────────────────────────────

@app.command("list")
def comment_list(
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    page: int = typer.Option(1, "--page", help="Page number."),
    per: int = typer.Option(100, "--per", help="Items per page (max 100)."),
    all_pages: bool = typer.Option(False, "--all", help="Fetch all pages (warns if >500)."),
    commented_type: Optional[str] = typer.Option(
        None, "--type", help=f"Filter by entity type. Likely values: {_TYPE_HINT}.",
    ),
    commented_id: Optional[int] = typer.Option(
        None, "--entity-id", help="Filter by entity ID (use together with --type).",
    ),
    filter: list[str] = typer.Option([], "--filter", help="Filter as key=value (repeatable)."),
) -> None:
    """List comments, optionally scoped to a specific entity.

    The comments API uses direct query params (not bracket-notation filters) for
    commented_type and commented_id, so --type/--entity-id are sent as top-level
    params. Any --filter key=value flags are sent as filter[key]=value alongside them.

    Examples:
        caflou comment list --type Task --entity-id 12345
        caflou comment list --type Invoice --entity-id 999
    """
    client = get_client(account)

    # commented_type and commented_id must be direct query params, not filter[...].
    def _build_params(page_num: int, per_page: int) -> dict:
        params: dict = {"page": page_num, "per": per_page}
        if commented_type:
            params["commented_type"] = commented_type
        if commented_id is not None:
            params["commented_id"] = commented_id
        for k, v in parse_filters(filter).items():
            params[f"filter[{k}]"] = v
        return params

    if all_pages:
        first = client.get("comments", params=_build_params(1, 100))
        total = first.get("total_results", 0)
        if total > 500:
            typer.echo(
                f"Warning: fetching all {total} results across multiple pages, this may be slow...",
                err=True,
            )
        results = list(first.get("results", []))
        for p in range(2, first.get("total_pages", 1) + 1):
            results.extend(client.get("comments", params=_build_params(p, 100)).get("results", []))
        if json_output:
            print_json(results)
        else:
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])
    else:
        data = client.get("comments", params=_build_params(page, per))
        results = data.get("results", [])
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(_LIST_HEADERS, [_list_row(r) for r in results])


@app.command("get")
def comment_get(
    id: int = typer.Argument(..., help="Comment ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Get full details of a comment."""
    client = get_client(account)
    data = client.get(f"comments/{id}")
    if json_output:
        print_json(data)
    else:
        print_record(data)


# ── write commands ────────────────────────────────────────────────────────────

@app.command("create")
def comment_create(
    text: Optional[str] = typer.Option(None, "--text", help="Comment text."),
    commented_type: Optional[str] = typer.Option(
        None, "--type", help=f"Entity type to comment on. Likely values: {_TYPE_HINT}.",
    ),
    commented_id: Optional[int] = typer.Option(
        None, "--entity-id", help="ID of the entity to comment on.",
    ),
    is_private: bool = typer.Option(False, "--private", help="Make the comment private."),
    notify: list[int] = typer.Option([], "--notify", help="User ID to notify (repeatable)."),
    reply_to: Optional[int] = typer.Option(
        None, "--reply-to", help="Parent comment ID to reply to.",
    ),
    from_file: Optional[str] = typer.Option(
        None, "--from-file", "-f",
        help="JSON file with full comment body, or '-' for stdin. Overrides all flags.",
    ),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Post a new comment on an entity.

    Examples:
        caflou comment create --type Task --entity-id 12345 --text "Looks good"
        caflou comment create --type Invoice --entity-id 999 --text "Please check" --notify 101
        caflou comment create --type Task --entity-id 12345 --text "Reply" --reply-to 88
        caflou comment create --from-file comment.json
    """
    if from_file is not None:
        data = read_json_input(from_file)
        data.pop("_comment", None)
    else:
        if not text:
            error("--text is required (or use --from-file).")
        if not commented_type:
            error(f"--type is required. Likely values: {_TYPE_HINT}.")
        if commented_id is None:
            error("--entity-id is required.")

        data: dict = {
            "text": text,
            "commented_type": commented_type,
            "commented_id": commented_id,
        }
        if is_private:
            data["is_private"] = True
        if notify:
            data["user_ids"] = list(notify)
        if reply_to is not None:
            data["comment_id"] = reply_to

    client = get_client(account)
    result = client.post("comments", data)

    if json_output:
        print_json(result)
    else:
        typer.echo(f"Created comment {result.get('id')}.", err=True)
        print_record(result)


@app.command("update")
def comment_update(
    id: int = typer.Argument(..., help="Comment ID."),
    text: str = typer.Option(..., "--text", help="New comment text."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Update the text of a comment.

    Example:
        caflou comment update 42 --text "Corrected wording"
    """
    client = get_client(account)
    result = client.patch(f"comments/{id}", {"text": text})
    if json_output:
        print_json(result)
    else:
        print_record(result)


@app.command("delete")
def comment_delete(
    id: int = typer.Argument(..., help="Comment ID."),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Delete a comment. Prompts for confirmation unless --force is given."""
    client = get_client(account)

    if not force:
        comment = client.get(f"comments/{id}")
        text = (comment.get("text") or "")[:50]
        confirmed = typer.confirm(f"Delete comment {id} ({text!r})?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    client.delete(f"comments/{id}")

    if json_output:
        print_json({"deleted": True, "id": id})
    else:
        typer.echo(f"Deleted comment {id}.")


@app.command("read")
def comment_read(
    id: int = typer.Argument(..., help="Comment ID."),
    read: bool = typer.Option(True, "--read/--no-read", help="Mark as read or unread."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Mark a comment as read or unread.

    Examples:
        caflou comment read 42
        caflou comment read 42 --no-read
    """
    client = get_client(account)
    result = client.patch(f"comments/{id}/change_read_status", {"read": read})
    if json_output:
        print_json(result or {"id": id, "read": read})
    else:
        status = "read" if read else "unread"
        typer.echo(f"Marked comment {id} as {status}.")


@app.command("like")
def comment_like(
    id: int = typer.Argument(..., help="Comment ID."),
    account: Optional[str] = typer.Option(None, "--account", help="Account ID or name override."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Toggle the like on a comment.

    Example:
        caflou comment like 42
    """
    client = get_client(account)
    result = client.patch(f"comments/{id}/like", {})
    if json_output:
        print_json(result or {"id": id})
    else:
        typer.echo(f"Toggled like on comment {id}.")
