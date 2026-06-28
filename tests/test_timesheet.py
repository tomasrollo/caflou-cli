from unittest.mock import patch

from caflou_cli.main import app
from tests.fake_client import FakeClient

_PAGE = {"results": [], "total_results": 0, "total_pages": 1, "page": 1}


def test_timesheet_list_company_id_sets_scope(runner):
    fake = FakeClient().seed("LIST", "timesheets", _PAGE)
    with patch("caflou_cli.commands.timesheet.get_client", return_value=fake):
        runner.invoke(app, ["timesheet", "list", "--company-id", "7"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "company", "scope_id": 7}


def test_timesheet_list_no_company_id_sends_no_scope(runner):
    fake = FakeClient().seed("LIST", "timesheets", _PAGE)
    with patch("caflou_cli.commands.timesheet.get_client", return_value=fake):
        runner.invoke(app, ["timesheet", "list"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] is None
