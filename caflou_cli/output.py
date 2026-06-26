import json
import sys
from typing import Any

import typer


def print_json(data: Any) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


def print_table(headers: list[str], rows: list[list[Any]]) -> None:
    if not rows:
        typer.echo("No results.")
        return

    str_rows = [
        [str(cell) if cell is not None else "-" for cell in row] for row in rows
    ]
    all_rows = [headers] + str_rows
    widths = [max(len(row[i]) for row in all_rows) for i in range(len(headers))]

    typer.echo("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    for row in str_rows:
        typer.echo("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))


def print_record(data: dict) -> None:
    _SKIP = {
        "privacy", "default_privacy", "wbs_can_write", "delete_warning",
        "template", "inherited_template", "repeat_weekdays", "repeat_monthdays",
        "timesheets_stats", "user_budget_allocations", "user_ids",
        "budget_progress", "hours_progress", "incomes_progress", "expenses_progress",
        "get_progress", "get_progress_old", "planned_tracked_time",
        "tracked_time_progress", "unread_object_ids",
    }

    items = []
    for k, v in data.items():
        if k in _SKIP:
            continue
        if isinstance(v, dict) and _is_keyed_by_user_ids(v):
            continue
        items.append((k, _fmt(v)))

    if not items:
        return

    width = max(len(k) for k, _ in items)
    for k, v in items:
        typer.echo(f"{k}:{' ' * (width - len(k) + 2)}{v}")


def print_pagination(data: dict) -> None:
    total = data.get("total_results", "?")
    page = data.get("page", "?")
    pages = data.get("total_pages", "?")
    typer.echo(f"Page {page}/{pages} — {total} total", err=True)


def error(message: str, exit_code: int = 1) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(exit_code)


def not_implemented(operation: str) -> None:
    typer.echo(f"Not implemented: {operation} is a write operation and has not been implemented yet.", err=True)
    raise typer.Exit(0)


# ── helpers ──────────────────────────────────────────────────────────────────

def _is_keyed_by_user_ids(d: dict) -> bool:
    """Return True if dict looks like a user-ID-keyed map (e.g. privacy blobs)."""
    keys = list(d.keys())
    return bool(keys) and all(str(k).isdigit() for k in keys[:5])


def _fmt(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list):
        if not v:
            return "-"
        if all(isinstance(x, (str, int, float)) for x in v):
            return ", ".join(str(x) for x in v)
        return f"[{len(v)} items]"
    if isinstance(v, dict):
        name = v.get("name") or v.get("id")
        if name:
            return str(name)
        return json.dumps(v, ensure_ascii=False)
    return str(v)
