"""Shared helpers used by all command modules."""
import json
import sys
from typing import Optional

from caflou_cli.output import error


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
