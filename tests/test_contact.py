import json
from unittest.mock import patch

from caflou_cli.main import app
from tests.fake_client import FakeClient

_CONTACT = {"id": 5, "name": "Alice", "company_id": 100, "company_name": "ACME", "email": "alice@acme.com"}


# ── create routes through company-nested path ─────────────────────────────────

def test_contact_create_posts_to_nested_path(runner):
    fake = FakeClient()
    body = {"name": "Alice", "company_id": 777}
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        result = runner.invoke(app, ["contact", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code == 0
    post_call = next(c for c in fake.calls if c["method"] == "POST")
    assert post_call["path"] == "companies/777/contacts"


def test_contact_create_strips_comment(runner):
    fake = FakeClient()
    body = {"_comment": "remove me", "name": "Alice", "company_id": 777}
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        runner.invoke(app, ["contact", "create", "--from-file", "-"], input=json.dumps(body))
    post_call = next(c for c in fake.calls if c["method"] == "POST")
    assert "_comment" not in post_call["data"]


def test_contact_create_requires_company_id(runner):
    fake = FakeClient()
    body = {"name": "Alice"}  # missing company_id
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        result = runner.invoke(app, ["contact", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code != 0
    assert not any(c["method"] == "POST" for c in fake.calls)


# ── update fetches company_id then uses nested PATCH path ─────────────────────

def test_contact_update_patches_nested_path(runner):
    fake = FakeClient().seed("GET", "contacts/5", _CONTACT)
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        result = runner.invoke(app, ["contact", "update", "5", "--name", "Bob"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["path"] == "companies/100/contacts/5"
    assert patch_call["data"]["name"] == "Bob"


def test_contact_update_fetches_contact_first(runner):
    fake = FakeClient().seed("GET", "contacts/5", _CONTACT)
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        runner.invoke(app, ["contact", "update", "5", "--name", "Bob"])
    get_call = next(c for c in fake.calls if c["method"] == "GET")
    assert get_call["path"] == "contacts/5"


def test_contact_update_no_flags_errors(runner):
    fake = FakeClient().seed("GET", "contacts/5", _CONTACT)
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        result = runner.invoke(app, ["contact", "update", "5"])
    assert result.exit_code != 0


# ── delete fetches company_id then uses nested DELETE path ────────────────────

def test_contact_delete_force_uses_nested_path(runner):
    fake = FakeClient().seed("GET", "contacts/5", _CONTACT)
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        result = runner.invoke(app, ["contact", "delete", "5", "--force"])
    assert result.exit_code == 0
    delete_call = next(c for c in fake.calls if c["method"] == "DELETE")
    assert delete_call["path"] == "companies/100/contacts/5"


# ── list scope ────────────────────────────────────────────────────────────────

_LIST_PAGE = {"results": [], "total_results": 0, "total_pages": 1, "page": 1}


def test_contact_list_company_id_sets_scope(runner):
    fake = FakeClient().seed("LIST", "contacts", _LIST_PAGE)
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        runner.invoke(app, ["contact", "list", "--company-id", "100"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "company", "scope_id": 100}


def test_contact_list_no_company_id_sends_no_scope(runner):
    fake = FakeClient().seed("LIST", "contacts", _LIST_PAGE)
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        runner.invoke(app, ["contact", "list"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] is None
