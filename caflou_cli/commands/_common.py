"""Shared helpers used by all command modules."""
import json
import sys
from collections.abc import Callable
from typing import Optional

from caflou_cli.cache import enrich_from_entity
from caflou_cli.output import error, print_json, print_pagination, print_table


def run_list(
    resource: str,
    headers: list[str],
    row_fn: Callable[[dict], list],
    *,
    client,
    json_output: bool,
    page: int,
    per: int,
    all_pages: bool,
    filters: dict,
) -> None:
    if all_pages:
        results = client.list_all(resource, filters=filters)
        enrich_from_entity(client.account_id, resource, results)
        if json_output:
            print_json(results)
        else:
            print_table(headers, [row_fn(r) for r in results])
    else:
        data = client.list(resource, page=page, per=per, filters=filters)
        results = data.get("results", [])
        enrich_from_entity(client.account_id, resource, results)
        if json_output:
            print_json(data)
        else:
            print_pagination(data)
            print_table(headers, [row_fn(r) for r in results])


def parse_filters(raw: list[str]) -> dict:
    filters: dict = {}
    for f in raw:
        if "=" not in f:
            error(f"Invalid filter '{f}'. Use key=value format.")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters


def read_json_input(from_file: Optional[str]) -> dict:
    """Read JSON from a file path, '-' for stdin, or error."""
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
