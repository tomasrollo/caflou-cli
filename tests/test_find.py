"""Tests for <object> find commands across project, company, document."""
import json
from unittest.mock import patch

import pytest

from caflou_cli.main import app
from tests.fake_client import FakeClient

_ACCOUNT = "test-account"

_PROJECTS = [
    {"id": 1, "name": "Skříň Dejvice"},
    {"id": 2, "name": "Skříň Holešovice"},
    {"id": 3, "name": "Kuchyně Praha"},
]
_COMPANIES = [
    {"id": 10, "name": "Acme s.r.o."},
    {"id": 11, "name": "Acme International"},
]
_DOCUMENTS = [
    {"id": 100, "name": "Invoice 2024-001"},
    {"id": 101, "name": "Invoice 2024-002"},
]


def _write_cache(tmp_path, cache_name, records):
    cache_dir = tmp_path / "cache" / _ACCOUNT
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{cache_name}.json").write_text(
        json.dumps({"synced_at": "2026-01-01T00:00:00", "records": records})
    )


# ── project find ──────────────────────────────────────────────────────────────

def test_project_find_cache_hit(runner, tmp_path):
    _write_cache(tmp_path, "projects", _PROJECTS)
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "find", "skříň"])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert lines[0] == "1\tSkříň Dejvice"
    assert lines[1] == "2\tSkříň Holešovice"
    assert not any(c["method"] == "LIST" for c in fake.calls)


def test_project_find_cache_hit_json(runner, tmp_path):
    _write_cache(tmp_path, "projects", _PROJECTS)
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "find", "skříň", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 2
    assert data[0] == {"id": 1, "name": "Skříň Dejvice"}


def test_project_find_no_cache_falls_back_to_api(runner, tmp_path):
    fake = FakeClient(_ACCOUNT).seed(
        "LIST", "projects", {"results": _PROJECTS[:1], "total_results": 1, "total_pages": 1}
    )
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "find", "Skříň"])
    assert result.exit_code == 0
    assert "Cache empty" in result.output
    assert "1\tSkříň Dejvice" in result.stdout
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"] == {"search": "Skříň"}


def test_project_find_cache_miss_falls_back_to_api(runner, tmp_path):
    _write_cache(tmp_path, "projects", _PROJECTS)
    fake = FakeClient(_ACCOUNT).seed(
        "LIST", "projects", {"results": [], "total_results": 0, "total_pages": 1}
    )
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "find", "nonexistent"])
    assert result.exit_code == 0
    assert "Not in cache" in result.output
    assert any(c["method"] == "LIST" for c in fake.calls)


def test_project_find_refresh_skips_cache(runner, tmp_path):
    _write_cache(tmp_path, "projects", _PROJECTS)
    fake = FakeClient(_ACCOUNT).seed(
        "LIST", "projects", {"results": _PROJECTS[2:], "total_results": 1, "total_pages": 1}
    )
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "find", "Kuchyně", "--refresh"])
    assert result.exit_code == 0
    assert any(c["method"] == "LIST" for c in fake.calls)
    assert "3\tKuchyně Praha" in result.stdout


def test_project_find_api_fallback_populates_cache(runner, tmp_path):
    fake = FakeClient(_ACCOUNT).seed(
        "LIST", "projects", {"results": _PROJECTS[:1], "total_results": 1, "total_pages": 1}
    )
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(app, ["project", "find", "Skříň"])
    cache_file = tmp_path / "cache" / _ACCOUNT / "projects.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    ids = {r["id"] for r in data["records"]}
    assert 1 in ids


# ── company find ──────────────────────────────────────────────────────────────

def test_company_find_cache_hit(runner, tmp_path):
    _write_cache(tmp_path, "companies", _COMPANIES)
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        result = runner.invoke(app, ["company", "find", "acme"])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert lines[0] == "10\tAcme s.r.o."


def test_company_find_no_cache_falls_back_to_api(runner, tmp_path):
    fake = FakeClient(_ACCOUNT).seed(
        "LIST", "companies", {"results": _COMPANIES[:1], "total_results": 1, "total_pages": 1}
    )
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        result = runner.invoke(app, ["company", "find", "Acme"])
    assert result.exit_code == 0
    assert "Cache empty" in result.output
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["filters"] == {"search": "Acme"}


def test_company_find_json(runner, tmp_path):
    _write_cache(tmp_path, "companies", _COMPANIES)
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        result = runner.invoke(app, ["company", "find", "acme", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data[0]["id"] == 10


# ── document find ─────────────────────────────────────────────────────────────

def test_document_find_cache_hit(runner, tmp_path):
    _write_cache(tmp_path, "documents", _DOCUMENTS)
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "find", "invoice 2024"])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    assert lines[0] == "100\tInvoice 2024-001"


def test_document_find_no_cache_falls_back_to_api(runner, tmp_path):
    fake = FakeClient(_ACCOUNT).seed(
        "LIST", "invoices", {"results": _DOCUMENTS[:1], "total_results": 1, "total_pages": 1}
    )
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "find", "Invoice"])
    assert result.exit_code == 0
    assert "Cache empty" in result.output
    list_call = next(c for c in fake.calls if c["method"] == "LIST")
    assert list_call["resource"] == "invoices"
    assert list_call["filters"] == {"search": "Invoice"}


def test_document_find_json(runner, tmp_path):
    _write_cache(tmp_path, "documents", _DOCUMENTS)
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "find", "invoice", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data[0]["id"] == 100


# ── cache enrichment from other commands ──────────────────────────────────────

def test_project_create_enriches_cache(runner, tmp_path):
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        runner.invoke(
            app,
            ["project", "create", "--from-file", "-"],
            input=json.dumps({"name": "New Project"}),
        )
    cache_file = tmp_path / "cache" / _ACCOUNT / "projects.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    names = [r["name"] for r in data["records"]]
    assert "New Project" in names


def test_company_create_enriches_cache(runner, tmp_path):
    fake = FakeClient(_ACCOUNT)
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        runner.invoke(
            app,
            ["company", "create", "--from-file", "-"],
            input=json.dumps({"name": "New Company"}),
        )
    cache_file = tmp_path / "cache" / _ACCOUNT / "companies.json"
    assert cache_file.exists()
