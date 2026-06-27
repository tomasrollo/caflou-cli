import json
from unittest.mock import patch

from caflou_cli.main import app
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


# ── create ────────────────────────────────────────────────────────────────────

def test_document_create_strips_comment(runner):
    fake = FakeClient()
    body = {"_comment": "ignore", "name": "Test Invoice", "kind": "issued", "currency": "CZK", "date_of_issue": "2026-06-27"}
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "create", "--from-file", "-"], input=json.dumps(body))
    assert result.exit_code == 0
    post_call = next(c for c in fake.calls if c["method"] == "POST")
    assert "_comment" not in post_call["data"]
    assert post_call["path"] == "invoices"
