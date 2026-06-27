import pytest
import typer

from caflou_cli.commands._common import parse_filters


def test_parse_filters_empty():
    assert parse_filters([]) == {}


def test_parse_filters_single():
    assert parse_filters(["key=value"]) == {"key": "value"}


def test_parse_filters_multiple():
    assert parse_filters(["a=1", "b=2"]) == {"a": "1", "b": "2"}


def test_parse_filters_value_contains_equals():
    # Only splits on first '='
    assert parse_filters(["key=v=1"]) == {"key": "v=1"}


def test_parse_filters_invalid_raises():
    with pytest.raises(typer.Exit):
        parse_filters(["no-equals-sign"])
