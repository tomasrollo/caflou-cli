from unittest.mock import patch

from caflou_cli.main import app
from tests.fake_client import FakeClient

_PAGE = {"results": [], "total_results": 0, "total_pages": 1, "page": 1}


def test_project_list_company_id_sets_scope(runner):
    fake = FakeClient().seed("LIST", "projects", _PAGE)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "list", "--company-id", "42"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "company", "scope_id": 42}


def test_project_list_no_company_id_sends_no_scope(runner):
    fake = FakeClient().seed("LIST", "projects", _PAGE)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "list"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] is None


def test_project_list_active_sets_filter(runner):
    fake = FakeClient().seed("LIST", "projects", _PAGE)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "list", "--active"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("active") == "true"


def test_project_list_closed_sets_filter(runner):
    fake = FakeClient().seed("LIST", "projects", _PAGE)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "list", "--closed"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("closed") == "true"


def test_project_list_project_status_id_sets_filter(runner):
    fake = FakeClient().seed("LIST", "projects", _PAGE)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "list", "--project-status-id", "1", "--project-status-id", "2"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("project_status_ids") == "1,2"


def test_project_list_project_type_id_sets_filter(runner):
    fake = FakeClient().seed("LIST", "projects", _PAGE)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "list", "--project-type-id", "5"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("project_type_ids") == "5"


def test_project_list_user_id_sets_filter(runner):
    fake = FakeClient().seed("LIST", "projects", _PAGE)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "list", "--user-id", "7", "--user-id", "8"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("user_ids") == "7,8"
