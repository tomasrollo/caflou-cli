import json
import pytest
import typer
from unittest.mock import patch

from caflou_cli.main import app
from caflou_cli.commands.document import _validate_document_body
from tests.fake_client import FakeClient


# ── template kind mapping ─────────────────────────────────────────────────────

def _template_output(runner, kind: str) -> dict:
    fake = FakeClient()
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "template", kind])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def test_template_issued_passthrough(runner):
    assert _template_output(runner, "issued")["kind"] == "issued"


def test_template_received_passthrough(runner):
    assert _template_output(runner, "received")["kind"] == "received"


def test_template_proforma_passthrough(runner):
    assert _template_output(runner, "proforma")["kind"] == "proforma"


def test_template_storno_maps_to_issued(runner):
    assert _template_output(runner, "storno")["kind"] == "issued"


def test_template_storno_received_maps_to_received(runner):
    assert _template_output(runner, "storno_received")["kind"] == "received"


def test_template_contract_maps_to_issued(runner):
    assert _template_output(runner, "contract")["kind"] == "issued"


def test_template_contract_received_maps_to_received(runner):
    assert _template_output(runner, "contract_received")["kind"] == "received"


def test_template_tax_receipt_maps_to_issued(runner):
    assert _template_output(runner, "tax_receipt")["kind"] == "issued"


def test_template_tax_receipt_received_maps_to_issued(runner):
    # tax_receipt_received is still "issued" per the API (not "received")
    assert _template_output(runner, "tax_receipt_received")["kind"] == "issued"


def test_template_financial_kind_includes_date_fields(runner):
    skeleton = _template_output(runner, "issued")
    assert "date_of_tax" in skeleton
    assert "date_of_payment" in skeleton


def test_template_non_financial_kind_omits_date_fields(runner):
    skeleton = _template_output(runner, "offer")
    assert "date_of_tax" not in skeleton
    assert "date_of_payment" not in skeleton


def test_template_received_includes_from_company_id(runner):
    skeleton = _template_output(runner, "received")
    assert "from_company_id" in skeleton


def test_template_issued_omits_from_company_id(runner):
    skeleton = _template_output(runner, "issued")
    assert "from_company_id" not in skeleton


def test_template_has_no_comment_key_in_parsed_output(runner):
    skeleton = _template_output(runner, "issued")
    # _comment is present in the template (it's there for humans to read before submitting)
    assert "_comment" in skeleton


# ── _validate_document_body unit tests ───────────────────────────────────────

_ISSUED = {
    "name": "Test", "kind": "issued", "currency": "CZK",
    "date_of_issue": "2026-06-27", "date_of_tax": "2026-06-27", "date_of_payment": "2026-06-27",
}

def test_validate_passthrough_kind_unchanged():
    data = _validate_document_body({**_ISSUED})
    assert data["kind"] == "issued"


def test_validate_storno_translates_to_issued():
    data = _validate_document_body({**_ISSUED, "kind": "storno"})
    assert data["kind"] == "issued"


def test_validate_contract_received_translates_to_received():
    body = {
        "name": "C", "kind": "contract_received", "currency": "CZK",
        "date_of_issue": "2026-06-27", "date_of_tax": "2026-06-27", "date_of_payment": "2026-06-27",
        "from_company_id": 42,
    }
    data = _validate_document_body(body)
    assert data["kind"] == "received"


def test_validate_missing_kind_errors():
    with pytest.raises(typer.Exit):
        _validate_document_body({"name": "X", "currency": "CZK", "date_of_issue": "2026-06-27"})


def test_validate_unknown_kind_errors():
    with pytest.raises(typer.Exit):
        _validate_document_body({**_ISSUED, "kind": "nonsense"})


def test_validate_missing_name_errors():
    with pytest.raises(typer.Exit):
        _validate_document_body({**_ISSUED, "name": ""})


def test_validate_missing_currency_errors():
    with pytest.raises(typer.Exit):
        _validate_document_body({**_ISSUED, "currency": None})


def test_validate_missing_date_of_issue_errors():
    with pytest.raises(typer.Exit):
        _validate_document_body({**_ISSUED, "date_of_issue": ""})


def test_validate_financial_kind_missing_date_of_tax_errors():
    body = {**_ISSUED}
    del body["date_of_tax"]
    with pytest.raises(typer.Exit):
        _validate_document_body(body)


def test_validate_financial_kind_missing_date_of_payment_errors():
    body = {**_ISSUED}
    del body["date_of_payment"]
    with pytest.raises(typer.Exit):
        _validate_document_body(body)


def test_validate_non_financial_kind_does_not_require_date_fields():
    body = {"name": "O", "kind": "offer", "currency": "CZK", "date_of_issue": "2026-06-27"}
    data = _validate_document_body(body)  # must not raise
    assert data["kind"] == "offer"


def test_validate_needs_supplier_kind_missing_from_company_id_errors():
    body = {
        "name": "R", "kind": "received", "currency": "CZK",
        "date_of_issue": "2026-06-27", "date_of_tax": "2026-06-27", "date_of_payment": "2026-06-27",
    }
    with pytest.raises(typer.Exit):
        _validate_document_body(body)


def test_validate_needs_supplier_kind_with_from_company_id_ok():
    body = {
        "name": "R", "kind": "received", "currency": "CZK",
        "date_of_issue": "2026-06-27", "date_of_tax": "2026-06-27", "date_of_payment": "2026-06-27",
        "from_company_id": 99,
    }
    data = _validate_document_body(body)
    assert data["kind"] == "received"


# ── create ────────────────────────────────────────────────────────────────────

def test_document_create_strips_comment(runner):
    fake = FakeClient()
    body = {
        "_comment": "ignore", "name": "Test Invoice", "kind": "issued", "currency": "CZK",
        "date_of_issue": "2026-06-27", "date_of_tax": "2026-06-27", "date_of_payment": "2026-06-27",
    }
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code == 0
    post_call = next(c for c in fake.calls if c["method"] == "POST")
    assert "_comment" not in post_call["data"]
    assert post_call["path"] == "invoices"


def test_document_create_translates_storno_kind(runner):
    fake = FakeClient()
    body = {
        "name": "Credit note", "kind": "storno", "currency": "CZK",
        "date_of_issue": "2026-06-27", "date_of_tax": "2026-06-27", "date_of_payment": "2026-06-27",
    }
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code == 0
    post_call = next(c for c in fake.calls if c["method"] == "POST")
    assert post_call["data"]["kind"] == "issued"


def test_document_create_unknown_kind_errors(runner):
    fake = FakeClient()
    body = {"name": "X", "kind": "bogus", "currency": "CZK", "date_of_issue": "2026-06-27"}
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code != 0
    assert not any(c["method"] == "POST" for c in fake.calls)


def test_document_create_financial_kind_missing_date_errors(runner):
    fake = FakeClient()
    body = {"name": "X", "kind": "issued", "currency": "CZK", "date_of_issue": "2026-06-27"}
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code != 0
    assert not any(c["method"] == "POST" for c in fake.calls)


# ── list filters and scopes ───────────────────────────────────────────────────

_LIST_PAGE = {"results": [], "total_results": 0, "total_pages": 1, "page": 1}


def test_document_list_kind_sets_scope(runner):
    fake = FakeClient().seed("LIST", "invoices", _LIST_PAGE)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        runner.invoke(app, ["document", "list", "--kind", "offer"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"kind": "offer"}


def test_document_list_invalid_kind_errors(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "list", "--kind", "bogus"])
    assert result.exit_code != 0
    assert not any(c["method"] == "LIST" for c in fake.calls)


def test_document_list_company_id_sets_scope(runner):
    fake = FakeClient().seed("LIST", "invoices", _LIST_PAGE)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        runner.invoke(app, ["document", "list", "--company-id", "10"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "company", "scope_id": 10}


def test_document_list_project_id_sets_scope(runner):
    fake = FakeClient().seed("LIST", "invoices", _LIST_PAGE)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        runner.invoke(app, ["document", "list", "--project-id", "5"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "project", "scope_id": 5}


def test_document_list_kind_and_company_id_combined(runner):
    fake = FakeClient().seed("LIST", "invoices", _LIST_PAGE)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        runner.invoke(app, ["document", "list", "--kind", "invoice", "--company-id", "10"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["scope"] == {"scope_type": "company", "scope_id": 10, "kind": "invoice"}


def test_document_list_unpaid_sets_filter(runner):
    fake = FakeClient().seed("LIST", "invoices", _LIST_PAGE)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        runner.invoke(app, ["document", "list", "--unpaid"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("unpaids") == "true"


def test_document_list_issued_sets_filter(runner):
    fake = FakeClient().seed("LIST", "invoices", _LIST_PAGE)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        runner.invoke(app, ["document", "list", "--issued"])
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"].get("issueds") == "true"
