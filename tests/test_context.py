"""Tests for <entity> context commands."""
import json
from unittest.mock import patch

import pytest

from caflou_cli.main import app
from tests.fake_client import FakeClient

_ACCOUNT = "test-account"

# ── fixtures ──────────────────────────────────────────────────────────────────

_PROJECT = {
    "id": 1, "name": "Skříň Dejvice", "project_status_name": "In progress",
    "start_date": "2024-01-15", "end_date": "2024-06-30", "company_id": 10,
    "task_ids": [501, 502],
}
_COMPANY = {
    "id": 10, "name": "Acme s.r.o.", "company_type_name": "Customer",
    "company_status_name": "Active", "email": "info@acme.cz",
}
_CONTACTS = [
    {"id": 200, "name": "Jan Novák", "email": "jan.novak@acme.cz", "phone": "+420 777 111"},
    {"id": 201, "name": "Jana Dvořák", "email": "jana@acme.cz", "phone": ""},
]
_TASKS = [
    {
        "id": 501, "name": "Measure kitchen", "task_status_name": "To do",
        "target_user_name": "Jan N.", "due_date": "2024-02-10", "project_id": 1,
    },
    {
        "id": 502, "name": "Order materials", "task_status_name": "Doing",
        "target_user_name": "Jana D.", "due_date": "2024-02-20", "project_id": 1,
    },
]
_DOCUMENTS = [
    {
        "id": 100, "name": "Invoice 001", "number": "2024-001",
        "global_kind": "issued", "invoice_state_name": "Unpaid",
        "total_cache": 45000, "currency": "CZK", "paid": False,
        "project_id": 1, "to_company_id": 10,
    },
]
_CONTACT = {
    "id": 200, "name": "Jan Novák", "email": "jan.novak@acme.cz",
    "phone": "+420 777 111", "company_id": 10,
}
_DOCUMENT = {
    "id": 100, "name": "Invoice 001", "number": "2024-001",
    "global_kind": "issued", "invoice_state_name": "Unpaid",
    "total_cache": 45000, "currency": "CZK", "paid": False,
    "to_company_id": 10, "project_id": 1,
    "offer_ids": [], "order_ids": [], "proforma_ids": [],
    "invoice_ids": [], "delivery_ids": [], "storno_ids": [], "tax_receipt_ids": [],
}
_OFFER = {
    "id": 90, "name": "Offer 001", "number": "OFF-001",
    "global_kind": "offer", "invoice_state_name": "Sent",
    "total_cache": 45000, "currency": "CZK", "paid": False,
    "to_company_id": 10,
    "offer_ids": [], "order_ids": [], "proforma_ids": [],
    "invoice_ids": [], "delivery_ids": [], "storno_ids": [], "tax_receipt_ids": [],
}
_TRANSFERS = [
    {"id": 55, "name": "Payment", "category_name": "Income", "value": 20000,
     "currency": "CZK", "invoice_id": 100},
]
_TASK = {
    "id": 501, "name": "Measure kitchen", "task_status_name": "To do",
    "due_date": "2024-02-10", "project_id": 1, "company_id": None,
}
_SUBTASKS = [
    {"id": 510, "name": "Take photos", "task_status_name": "To do",
     "due_date": None, "parent_id": 501},
]


def _list_page(results):
    return {"results": results, "total_results": len(results), "total_pages": 1}


# ── project context ───────────────────────────────────────────────────────────

def _project_fake_with_tasks(task_list):
    """Build a FakeClient for project context with individual task GETs seeded."""
    project = {**_PROJECT, "task_ids": [t["id"] for t in task_list]}
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "projects/1", project)
        .seed("GET", "companies/10", _COMPANY)
        .seed("GET", "companies/10/contacts", _CONTACTS)
        .seed("LIST", "invoices", _list_page(_DOCUMENTS))
    )
    for t in task_list:
        fake.seed("GET", f"tasks/{t['id']}", t)
    return fake


def test_project_context_header(runner, tmp_path):
    fake = _project_fake_with_tasks(_TASKS)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "context", "1"])
    assert result.exit_code == 0
    assert "PROJECT" in result.stdout
    assert "Skříň Dejvice" in result.stdout
    assert "In progress" in result.stdout


def test_project_context_sections(runner, tmp_path):
    fake = _project_fake_with_tasks(_TASKS)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "context", "1"])
    assert "COMPANY" in result.stdout
    assert "Acme s.r.o." in result.stdout
    assert "CONTACTS (2)" in result.stdout
    assert "Jan Novák" in result.stdout
    assert "TASKS (2)" in result.stdout
    assert "Measure kitchen" in result.stdout
    assert "DOCUMENTS (1)" in result.stdout
    assert "2024-001" in result.stdout


def test_project_context_json(runner, tmp_path):
    fake = _project_fake_with_tasks(_TASKS)
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "context", "1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["project"]["id"] == 1
    assert data["company"]["id"] == 10
    assert len(data["contacts"]) == 2
    assert len(data["tasks"]) == 2
    assert len(data["documents"]) == 1


def test_project_context_cap(runner, tmp_path):
    many_tasks = [
        {"id": 500 + i, "name": f"Task {i}", "task_status_name": "To do", "due_date": None}
        for i in range(15)
    ]
    fake = _project_fake_with_tasks(many_tasks)
    # contacts and invoices not needed for cap test — override with empty
    fake.seed("GET", "companies/10/contacts", [])
    fake.seed("LIST", "invoices", _list_page([]))
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "context", "1"])
    assert "(+ 5 more" in result.stdout
    shown = [l for l in result.stdout.splitlines() if l.startswith("    ") and "Task" in l]
    assert len(shown) == 10


def test_project_context_all_flag_removes_cap(runner, tmp_path):
    many_tasks = [
        {"id": 500 + i, "name": f"Task {i}", "task_status_name": "To do", "due_date": None}
        for i in range(15)
    ]
    fake = _project_fake_with_tasks(many_tasks)
    fake.seed("GET", "companies/10/contacts", [])
    fake.seed("LIST", "invoices", _list_page([]))
    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "context", "1", "--all"])
    assert "(+ " not in result.stdout
    shown = [l for l in result.stdout.splitlines() if l.startswith("    ") and "Task" in l]
    assert len(shown) == 15


def test_project_context_failed_section(runner, tmp_path):
    """A failed sub-fetch shows '(failed to load)' and doesn't abort."""
    class ErroringClient(FakeClient):
        def list(self, resource, **kwargs):
            if resource == "invoices":
                raise RuntimeError("network error")
            return super().list(resource, **kwargs)

    fake = ErroringClient(_ACCOUNT)
    fake.seed("GET", "projects/1", _PROJECT)
    fake.seed("GET", "companies/10", _COMPANY)
    fake.seed("GET", "companies/10/contacts", [])
    for t in _TASKS:
        fake.seed("GET", f"tasks/{t['id']}", t)

    with patch("caflou_cli.commands.project.get_client", return_value=fake):
        result = runner.invoke(app, ["project", "context", "1"])
    assert result.exit_code == 0
    assert "DOCUMENTS" in result.stdout
    assert "failed to load" in result.stdout
    assert "TASKS (2)" in result.stdout  # tasks section still renders


# ── contact context ───────────────────────────────────────────────────────────

def test_contact_context_header(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "contacts/200", _CONTACT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("LIST", "projects", _list_page([_PROJECT]))
    )
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        result = runner.invoke(app, ["contact", "context", "200"])
    assert result.exit_code == 0
    assert "CONTACT" in result.stdout
    assert "Jan Novák" in result.stdout
    assert "jan.novak@acme.cz" in result.stdout
    assert "COMPANY" in result.stdout
    assert "Acme s.r.o." in result.stdout
    assert "PROJECTS (1)" in result.stdout
    assert "Skříň Dejvice" in result.stdout


def test_contact_context_json(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "contacts/200", _CONTACT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("LIST", "projects", _list_page([_PROJECT]))
    )
    with patch("caflou_cli.commands.contact.get_client", return_value=fake):
        result = runner.invoke(app, ["contact", "context", "200", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["contact"]["id"] == 200
    assert data["company"]["id"] == 10
    assert len(data["projects"]) == 1


# ── company context ───────────────────────────────────────────────────────────

def test_company_context_header(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("GET", "companies/10/contacts", _CONTACTS)
        .seed("LIST", "projects", _list_page([_PROJECT]))
        .seed("LIST", "invoices", _list_page(_DOCUMENTS))
    )
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        result = runner.invoke(app, ["company", "context", "10"])
    assert result.exit_code == 0
    assert "COMPANY" in result.stdout
    assert "Acme s.r.o." in result.stdout
    assert "CONTACTS (2)" in result.stdout
    assert "PROJECTS (1)" in result.stdout
    assert "DOCUMENTS (1)" in result.stdout


def test_company_context_json(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("GET", "companies/10/contacts", _CONTACTS)
        .seed("LIST", "projects", _list_page([_PROJECT]))
        .seed("LIST", "invoices", _list_page(_DOCUMENTS))
    )
    with patch("caflou_cli.commands.company.get_client", return_value=fake):
        result = runner.invoke(app, ["company", "context", "10", "--json"])
    data = json.loads(result.stdout)
    assert data["company"]["id"] == 10
    assert len(data["contacts"]) == 2
    assert len(data["projects"]) == 1
    assert len(data["documents"]) == 1


# ── document context ──────────────────────────────────────────────────────────

def test_document_context_header(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "invoices/100", _DOCUMENT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("GET", "projects/1", _PROJECT)
        .seed("LIST", "transfers", _list_page(_TRANSFERS))
    )
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "context", "100"])
    assert result.exit_code == 0
    assert "DOCUMENT" in result.stdout
    assert "2024-001" in result.stdout
    assert "BUYER" in result.stdout
    assert "Acme s.r.o." in result.stdout
    assert "PROJECT" in result.stdout
    assert "Skříň Dejvice" in result.stdout
    assert "PAYMENTS (1)" in result.stdout
    assert "Payment" in result.stdout


def test_document_context_no_project(runner, tmp_path):
    doc_no_project = {**_DOCUMENT, "project_id": None}
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "invoices/100", doc_no_project)
        .seed("GET", "companies/10", _COMPANY)
        .seed("LIST", "transfers", _list_page([]))
    )
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "context", "100"])
    assert result.exit_code == 0
    assert "PROJECT" not in result.stdout  # no project section shown


def test_document_context_json(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "invoices/100", _DOCUMENT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("GET", "projects/1", _PROJECT)
        .seed("LIST", "transfers", _list_page(_TRANSFERS))
    )
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "context", "100", "--json"])
    data = json.loads(result.stdout)
    assert data["document"]["id"] == 100
    assert data["company"]["id"] == 10
    assert data["project"]["id"] == 1
    assert len(data["payments"]) == 1
    assert "related_documents" in data
    assert data["related_documents"] == []


def test_document_context_chain(runner, tmp_path):
    """Documents linked via offer_ids use _fetch_by_ids — no list filter guessing."""
    doc_with_chain = {**_DOCUMENT, "offer_ids": [90]}
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "invoices/100", doc_with_chain)
        .seed("GET", "invoices/90", _OFFER)
        .seed("GET", "companies/10", _COMPANY)
        .seed("GET", "projects/1", _PROJECT)
        .seed("LIST", "transfers", _list_page([]))
    )
    with patch("caflou_cli.commands.document.get_client", return_value=fake):
        result = runner.invoke(app, ["document", "context", "100"])
    assert result.exit_code == 0
    assert "RELATED DOCUMENTS (1)" in result.stdout
    assert "OFF-001" in result.stdout
    assert "Offer" in result.stdout


# ── task context ──────────────────────────────────────────────────────────────

def test_task_context_header(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "tasks/501", _TASK)
        .seed("GET", "projects/1", _PROJECT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("LIST", "tasks", _list_page(_SUBTASKS))
    )
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "context", "501"])
    assert result.exit_code == 0
    assert "TASK" in result.stdout
    assert "Measure kitchen" in result.stdout
    assert "PROJECT" in result.stdout
    assert "Skříň Dejvice" in result.stdout
    assert "COMPANY" in result.stdout
    assert "Acme s.r.o." in result.stdout
    assert "SUBTASKS (1)" in result.stdout
    assert "Take photos" in result.stdout


def test_task_context_no_project(runner, tmp_path):
    task_no_project = {**_TASK, "project_id": None, "company_id": None}
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "tasks/501", task_no_project)
        .seed("LIST", "tasks", _list_page([]))
    )
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "context", "501"])
    assert result.exit_code == 0
    assert "TASK" in result.stdout
    assert "Measure kitchen" in result.stdout


def test_task_context_json(runner, tmp_path):
    fake = (FakeClient(_ACCOUNT)
        .seed("GET", "tasks/501", _TASK)
        .seed("GET", "projects/1", _PROJECT)
        .seed("GET", "companies/10", _COMPANY)
        .seed("LIST", "tasks", _list_page(_SUBTASKS))
    )
    with patch("caflou_cli.commands.task.get_client", return_value=fake):
        result = runner.invoke(app, ["task", "context", "501", "--json"])
    data = json.loads(result.stdout)
    assert data["task"]["id"] == 501
    assert data["project"]["id"] == 1
    assert data["company"]["id"] == 10
    assert len(data["subtasks"]) == 1
