import json
from unittest.mock import patch

from caflou_cli.main import app
from tests.fake_client import FakeClient

_TASK = {"id": 42, "name": "My Task", "project_name": "Proj", "task_status_name": "Open", "task_type_name": None}
_PAGE = {"results": [_TASK], "total_results": 1, "total_pages": 1, "page": 1}


# ── list ──────────────────────────────────────────────────────────────────────

def test_task_list_shows_name(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "list"])
    assert result.exit_code == 0
    assert "My Task" in result.output


def test_task_list_json(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["results"][0]["name"] == "My Task"


def test_task_list_empty(runner):
    fake = FakeClient().seed("LIST", "tasks", {"results": [], "total_results": 0, "total_pages": 1, "page": 1})
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "list"])
    assert result.exit_code == 0
    assert "No results." in result.output


def test_task_list_passes_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--filter", "project_id=99"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"] == {"project_id": "99"}


def test_task_list_project_id_sets_scope(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--project-id", "7"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "project", "scope_id": 7}


def test_task_list_company_id_sets_scope(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--company-id", "3"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "company", "scope_id": 3}


def test_task_list_project_id_takes_precedence_over_company_id(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--project-id", "7", "--company-id", "3"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "project", "scope_id": 7}


def test_task_list_closed_sets_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--closed"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("closed") == "true"


def test_task_list_active_sets_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--active"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("active") == "true"


def test_task_list_task_status_id_sets_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--task-status-id", "1", "--task-status-id", "2"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("task_status_ids") == "1,2"


def test_task_list_task_type_id_sets_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--task-type-id", "10"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("task_type_ids") == "10"


def test_task_list_user_id_sets_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--user-id", "5", "--user-id", "6"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("target_user_ids") == "5,6"


def test_task_list_im_involved_sets_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--im-involved"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("im_involved") == "true"


def test_task_list_assigned_sets_filter(runner):
    fake = FakeClient().seed("LIST", "tasks", _PAGE)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "list", "--assigned"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("assigned") == "true"


# ── get ───────────────────────────────────────────────────────────────────────

def test_task_get_shows_record(runner):
    fake = FakeClient().seed("GET", "tasks/42", _TASK)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "get", "42"])
    assert result.exit_code == 0
    assert "My Task" in result.output


def test_task_get_json(runner):
    fake = FakeClient().seed("GET", "tasks/42", _TASK)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "get", "42", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["id"] == 42


# ── create ────────────────────────────────────────────────────────────────────

def test_task_create_strips_comment(runner):
    fake = FakeClient()
    body = {"_comment": "ignore me", "name": "New Task"}
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code == 0
    post_call = next(c for c in fake.calls if c["method"] == "POST")
    assert "_comment" not in post_call["data"]
    assert post_call["data"]["name"] == "New Task"


def test_task_create_posts_to_correct_path(runner):
    fake = FakeClient()
    body = {"name": "New Task"}
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        runner.invoke(app, ["task", "create", "--from-file", "-"], input=json.dumps(body))
    post_call = next(c for c in fake.calls if c["method"] == "POST")
    assert post_call["path"] == "tasks"


# ── update ────────────────────────────────────────────────────────────────────

def test_task_update_name(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "update", "1", "--name", "Renamed"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["data"] == {"name": "Renamed"}


def test_task_update_status_id_uses_task_status_id_field(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "update", "1", "--status-id", "99"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["data"] == {"task_status_id": 99}


def test_task_update_no_flags_errors(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "update", "1"])
    assert result.exit_code != 0


# ── delete ────────────────────────────────────────────────────────────────────

def test_task_delete_force_skips_prompt(runner):
    fake = FakeClient().seed("GET", "tasks/42", _TASK)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "delete", "42", "--force"])
    assert result.exit_code == 0
    assert any(c["method"] == "DELETE" and c["path"] == "tasks/42" for c in fake.calls)


def test_task_delete_aborted_on_no(runner):
    fake = FakeClient().seed("GET", "tasks/42", _TASK)
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "delete", "42"], input="n\n")
    assert result.exit_code == 0
    assert not any(c["method"] == "DELETE" for c in fake.calls)
