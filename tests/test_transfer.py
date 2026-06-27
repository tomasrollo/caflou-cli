from unittest.mock import patch

from caflou_cli.main import app
from tests.fake_client import FakeClient


def test_transfer_update_paid_uses_done_field(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.transfer.get_client", return_value=fake):
        result = runner.invoke(app, ["transfer", "update", "1", "--paid"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["data"] == {"done": True}
    assert "paid" not in patch_call["data"]


def test_transfer_update_no_paid_uses_done_false(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.transfer.get_client", return_value=fake):
        result = runner.invoke(app, ["transfer", "update", "1", "--no-paid"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["data"] == {"done": False}


def test_transfer_update_payment_date_sets_done_true(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.transfer.get_client", return_value=fake):
        result = runner.invoke(app, ["transfer", "update", "1", "--payment-date", "2026-01-01"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["data"]["payment_date"] == "2026-01-01"
    assert patch_call["data"]["done"] is True


def test_transfer_update_payment_date_does_not_override_explicit_paid(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.transfer.get_client", return_value=fake):
        result = runner.invoke(app, ["transfer", "update", "1", "--payment-date", "2026-01-01", "--no-paid"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    # --no-paid takes precedence; done is False, not implicitly True
    assert patch_call["data"]["done"] is False


def test_transfer_update_real_value(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.transfer.get_client", return_value=fake):
        result = runner.invoke(app, ["transfer", "update", "1", "--real-value", "9500.0"])
    assert result.exit_code == 0
    patch_call = next(c for c in fake.calls if c["method"] == "PATCH")
    assert patch_call["data"] == {"real_value": 9500.0}


def test_transfer_update_no_flags_errors(runner):
    fake = FakeClient()
    with patch("caflou_cli.commands.transfer.get_client", return_value=fake):
        result = runner.invoke(app, ["transfer", "update", "1"])
    assert result.exit_code != 0
