import json
from unittest.mock import patch

from caflou_cli.main import app
from tests.fake_client import FakeClient

_COMMENT = {
    "id": 10, "user_name": "Alice", "commented_type": "Task",
    "commented_id": 42, "text": "Looks good", "is_private": False,
}
_PAGE = {"results": [_COMMENT], "total_results": 1, "total_pages": 1, "page": 1}


# ── list ──────────────────────────────────────────────────────────────────────

def test_comment_list_shows_text(runner):
    fake = FakeClient().seed("GET", "comments", _PAGE)
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "list"])
    assert result.exit_code == 0
    assert "Looks good" in result.output


def test_comment_list_type_and_entity_id_as_direct_params(runner):
    fake = FakeClient().seed("GET", "comments", _PAGE)
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        runner.invoke(app, ["comment", "list", "--type", "Task", "--entity-id", "42"])
    get_call = next(c for c in fake.calls if c["method"] == "GET" and c["path"] == "comments")
    # Must be direct params, not bracket-notation
    assert get_call["params"]["commented_type"] == "Task"
    assert get_call["params"]["commented_id"] == 42
    assert "filter[commented_type]" not in get_call["params"]


def test_comment_list_extra_filter_uses_bracket_notation(runner):
    fake = FakeClient().seed("GET", "comments", _PAGE)
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        runner.invoke(app, ["comment", "list", "--type", "Task", "--filter", "is_private=false"])
    get_call = next(c for c in fake.calls if c["method"] == "GET" and c["path"] == "comments")
    assert get_call["params"]["commented_type"] == "Task"
    assert get_call["params"]["filter[is_private]"] == "false"


def test_comment_list_json(runner):
    fake = FakeClient().seed("GET", "comments", _PAGE)
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["results"][0]["id"] == 10


# ── get ───────────────────────────────────────────────────────────────────────

def test_comment_get(runner):
    fake = FakeClient().seed("GET", "comments/10", _COMMENT)
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "get", "10"])
    assert result.exit_code == 0
    assert "Looks good" in result.output


# ── create ────────────────────────────────────────────────────────────────────

def test_comment_create_flag_based(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, [
            "comment", "create",
            "--type", "Task", "--entity-id", "42", "--text", "LGTM",
        ])
    assert result.exit_code == 0
    post = next(c for c in fake.calls if c["method"] == "POST")
    assert post["path"] == "comments"
    assert post["data"] == {"text": "LGTM", "commented_type": "Task", "commented_id": 42}


def test_comment_create_private_and_notify(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        runner.invoke(app, [
            "comment", "create",
            "--type", "Task", "--entity-id", "42", "--text", "FYI",
            "--private", "--notify", "101", "--notify", "102",
        ])
    post = next(c for c in fake.calls if c["method"] == "POST")
    assert post["data"]["is_private"] is True
    assert post["data"]["user_ids"] == [101, 102]


def test_comment_create_reply_to(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        runner.invoke(app, [
            "comment", "create",
            "--type", "Task", "--entity-id", "42", "--text", "Agreed", "--reply-to", "88",
        ])
    post = next(c for c in fake.calls if c["method"] == "POST")
    assert post["data"]["comment_id"] == 88


def test_comment_create_from_file(runner):
    fake = FakeClient()
    body = {"text": "From file", "commented_type": "Project", "commented_id": 7}
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(
            app, ["comment", "create", "--from-file", "-"], input=json.dumps(body)
        )
    assert result.exit_code == 0
    post = next(c for c in fake.calls if c["method"] == "POST")
    assert post["data"]["commented_type"] == "Project"


def test_comment_create_missing_text_errors(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, [
            "comment", "create", "--type", "Task", "--entity-id", "42",
        ])
    assert result.exit_code != 0


def test_comment_create_missing_type_errors(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, [
            "comment", "create", "--entity-id", "42", "--text", "Hi",
        ])
    assert result.exit_code != 0


def test_comment_create_missing_entity_id_errors(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, [
            "comment", "create", "--type", "Task", "--text", "Hi",
        ])
    assert result.exit_code != 0


# ── update ────────────────────────────────────────────────────────────────────

def test_comment_update_patches_text(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "update", "10", "--text", "Revised"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["path"] == "comments/10"
    assert patch_call["data"] == {"text": "Revised"}


# ── delete ────────────────────────────────────────────────────────────────────

def test_comment_delete_force(runner):
    fake = FakeClient().seed("GET", "comments/10", _COMMENT)
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "delete", "10", "--force"])
    assert result.exit_code == 0
    assert any(c["method"] == "DELETE" and c["path"] == "comments/10" for c in fake.calls)


def test_comment_delete_aborted(runner):
    fake = FakeClient().seed("GET", "comments/10", _COMMENT)
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "delete", "10"], input="n\n")
    assert result.exit_code == 0
    assert not any(c["method"] == "DELETE" for c in fake.calls)


# ── read ──────────────────────────────────────────────────────────────────────

def test_comment_read_sends_patch(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "read", "10"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["path"] == "comments/10/change_read_status"
    assert patch_call["data"]["read"] is True


def test_comment_read_no_read(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "read", "10", "--no-read"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["data"]["read"] is False


# ── like ──────────────────────────────────────────────────────────────────────

def test_comment_like_sends_patch(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.comment.get_client", return_value=fake):
        result = runner.invoke(app, ["comment", "like", "10"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["path"] == "comments/10/like"
