from unittest.mock import patch

from caflou_cli.main import app
from tests.fake_client import FakeClient

_PAGE = {"results": [], "total_results": 0, "total_pages": 1, "page": 1}


def test_company_list_active_sets_filter(runner):
    fake = FakeClient().seed("LIST", "companies", _PAGE)
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        runner.invoke(app, ["company", "list", "--active"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("active") == "true"


def test_company_list_company_type_id_sets_filter(runner):
    fake = FakeClient().seed("LIST", "companies", _PAGE)
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        runner.invoke(app, ["company", "list", "--company-type-id", "3", "--company-type-id", "4"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("company_type_ids") == "3,4"


def test_company_list_no_flags_sends_empty_filters(runner):
    fake = FakeClient().seed("LIST", "companies", _PAGE)
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        runner.invoke(app, ["company", "list"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"] == {}
    assert list_call["scope"] is None
