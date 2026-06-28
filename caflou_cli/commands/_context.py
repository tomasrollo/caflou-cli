"""Shared helpers for <entity> context commands."""
from __future__ import annotations

from typing import Optional

import typer

from caflou_cli.api import ClientProtocol
from caflou_cli.cache import enrich_from_entity
from caflou_cli.output import print_json

_DEFAULT_LIMIT = 20


# ── rendering ─────────────────────────────────────────────────────────────────

def _print_rows(rows: list[list], indent: str = "    ", headers: Optional[list[str]] = None) -> None:
    if not rows:
        return
    str_rows = [[str(c) if c is not None else "-" for c in row] for row in rows]
    all_rows = ([headers] if headers else []) + str_rows
    widths = [max(len(r[i]) for r in all_rows) for i in range(len(all_rows[0]))]
    if headers:
        typer.echo(indent + "  ".join(c.ljust(w) for c, w in zip(headers, widths)))
    for row in str_rows:
        typer.echo(indent + "  ".join(c.ljust(w) for c, w in zip(row, widths)))


def _section_header(label: str, count: Optional[int] = None) -> None:
    suffix = f" ({count})" if count is not None else ""
    typer.echo(f"  {label}{suffix}")


def _overflow_hint(n: int, cmd: str) -> None:
    typer.echo(f"    (+ {n} more — {cmd})")


def _failed(label: str) -> None:
    typer.echo(f"  {label}   (failed to load)")


def _safe(fn):
    """Call fn(), return None on any exception."""
    try:
        return fn()
    except Exception:
        return None


def _daterange(start: Optional[str], end: Optional[str]) -> str:
    if start and end:
        return f"{start}–{end}"
    return start or end or ""


def _money(value, currency: Optional[str]) -> str:
    if value is None:
        return "-"
    try:
        formatted = f"{float(value):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        formatted = str(value)
    return f"{formatted} {currency}" if currency else formatted


# ── field formatters ──────────────────────────────────────────────────────────

_PROJECT_HEADERS  = ["ID", "NAME", "STATUS", "DATES"]
_COMPANY_HEADERS  = ["ID", "NAME", "TYPE", "EMAIL"]
_CONTACT_HEADERS  = ["ID", "NAME", "EMAIL", "PHONE"]
_TASK_HEADERS     = ["ID", "NAME", "STATUS", "ASSIGNEE", "DUE"]
_DOCUMENT_HEADERS = ["ID", "NUMBER", "KIND", "STATE", "TOTAL", "PAID"]
_TRANSFER_HEADERS = ["ID", "NAME", "CATEGORY", "TOTAL"]


def _project_cells(r: dict) -> list:
    return [
        str(r["id"]),
        r.get("name") or "-",
        r.get("project_status_name") or "-",
        _daterange(r.get("start_date"), r.get("end_date")),
    ]


def _company_cells(r: dict) -> list:
    return [
        str(r["id"]),
        r.get("name") or "-",
        r.get("company_type_name") or "-",
        r.get("email") or "-",
    ]


def _contact_cells(r: dict) -> list:
    return [
        str(r["id"]),
        r.get("name") or "-",
        r.get("email") or "-",
        r.get("phone") or r.get("mobile") or "-",
    ]


def _task_cells(r: dict) -> list:
    return [
        str(r["id"]),
        r.get("name") or "-",
        r.get("task_status_name") or "-",
        r.get("target_user_name") or r.get("user_name") or "-",
        r.get("due_date") or "-",
    ]


def _document_cells(r: dict) -> list:
    paid = "paid" if r.get("paid") else "unpaid"
    return [
        str(r["id"]),
        r.get("number") or r.get("name") or "-",
        r.get("global_kind") or "-",
        r.get("invoice_state_name") or "-",
        _money(r.get("total_cache"), r.get("currency")),
        paid,
    ]


def _transfer_cells(r: dict) -> list:
    return [
        str(r["id"]),
        r.get("name") or "-",
        r.get("category_name") or "-",
        _money(r.get("value") or r.get("amount"), r.get("currency")),
    ]


# ── section printer ───────────────────────────────────────────────────────────

def _print_section(
    label: str,
    records,  # list[dict] | None — None means fetch failed
    cell_fn,
    limit: Optional[int],
    overflow_cmd: str,
    headers: Optional[list[str]] = None,
) -> None:
    if records is None:
        _failed(label)
        return
    _section_header(label, len(records))
    rows = [cell_fn(r) for r in records]
    to_show = rows if limit is None else rows[:limit]
    overflow = len(rows) - len(to_show)
    _print_rows(to_show, headers=headers)
    if overflow:
        _overflow_hint(overflow, overflow_cmd)


# ── fetch helpers ─────────────────────────────────────────────────────────────

def _list_results(
    client: ClientProtocol,
    resource: str,
    filters: dict,
    post_filter=None,
) -> Optional[list]:
    """Fetch up to 100 results, then apply post_filter as a client-side safety net.

    The Caflou API silently ignores unknown filter keys instead of erroring, so
    server-side filters are best-effort.  post_filter=(lambda r: r["x"] == v)
    guarantees correctness regardless of whether the server honours the filter.
    """
    result = _safe(lambda: client.list(resource, per=100, filters=filters))
    if result is None:
        return None
    records = result.get("results", [])
    if post_filter is not None:
        records = [r for r in records if post_filter(r)]
    return records


def _contacts_for_company(
    client: ClientProtocol, company_id: int
) -> Optional[list]:
    result = _safe(
        lambda: client.get(f"companies/{company_id}/contacts", params={"per": 100})
    )
    if result is None:
        return None
    if isinstance(result, list):
        return result
    return result.get("results", [])


def _fetch_by_ids(
    client: ClientProtocol, resource: str, ids: list, limit: Optional[int]
) -> tuple[list, int]:
    """Fetch entities by ID list, bounded by limit.

    Returns (fetched_records, total_count) where total_count is len(ids) so the
    caller can compute overflow without fetching the tail.
    """
    total = len(ids)
    to_fetch = ids if limit is None else ids[:limit]
    records = []
    for eid in to_fetch:
        item = _safe(lambda eid=eid: client.get(f"{resource}/{eid}"))
        if item:
            records.append(item)
    return records, total


# ── context builders ──────────────────────────────────────────────────────────

def project_context(
    id: int,
    client: ClientProtocol,
    limit: Optional[int] = _DEFAULT_LIMIT,
    json_output: bool = False,
) -> None:
    """Context view for a project: linked companies by type, tasks, documents."""
    project = client.get(f"projects/{id}")
    enrich_from_entity(client.account_id, "projects", [project])

    # Companies: merge primary company_id (customer) with company_ids (linked companies),
    # deduplicating in case of overlap. Primary company goes first so it's always fetched.
    primary_id = project.get("company_id")
    linked_ids = project.get("company_ids") or []
    seen: set = set()
    company_id_list: list = []
    for cid in ([primary_id] if primary_id else []) + linked_ids:
        if cid not in seen:
            seen.add(cid)
            company_id_list.append(cid)
    companies, total_companies = _fetch_by_ids(client, "companies", company_id_list, limit)
    if companies:
        enrich_from_entity(client.account_id, "companies", companies)

    # Tasks: use task_ids from the project response — authoritative, no filter guessing.
    task_ids = project.get("task_ids") or []
    tasks, total_tasks = _fetch_by_ids(client, "tasks", task_ids, limit)
    if tasks:
        enrich_from_entity(client.account_id, "tasks", tasks)

    docs = _list_results(client, "invoices", {"project_id": id},
                         post_filter=lambda r: r.get("project_id") == id)

    if json_output:
        # For JSON, fetch all items beyond the display limit
        if limit is not None and total_companies > len(companies):
            extra, _ = _fetch_by_ids(client, "companies", company_id_list[len(companies):], limit=None)
            companies = companies + extra
        if limit is not None and total_tasks > len(tasks):
            extra, _ = _fetch_by_ids(client, "tasks", task_ids[len(tasks):], limit=None)
            tasks = tasks + extra
        print_json({
            "project": project,
            "companies": companies,
            "tasks": tasks,
            "documents": docs or [],
        })
        return

    dates = _daterange(project.get("start_date"), project.get("end_date"))
    typer.echo("  ".join(x for x in [
        "PROJECT", str(project["id"]), project.get("name") or "",
        project.get("project_status_name") or "", dates,
    ] if x))

    # Companies grouped by type — type is the group header so omit it from each row.
    # The primary company's type group sorts first; all others are alphabetical.
    if company_id_list:
        _section_header("COMPANIES", total_companies)
        grouped: dict[str, list] = {}
        for c in companies:
            t = c.get("company_type_name") or "Other"
            grouped.setdefault(t, []).append(c)
        primary_type = companies[0].get("company_type_name") if companies else None
        for type_name, type_cos in sorted(
            grouped.items(), key=lambda kv: (0 if kv[0] == primary_type else 1, kv[0])
        ):
            typer.echo(f"    {type_name} ({len(type_cos)})")
            _print_rows(
                [[str(c["id"]), c.get("name") or "-", c.get("email") or "-"] for c in type_cos],
                indent="      ",
                headers=["ID", "NAME", "EMAIL"],
            )
        overflow = total_companies - len(companies)
        if overflow:
            _overflow_hint(overflow, f"caflou project get {id} --json | jq '.company_ids'")

    # Tasks: total_tasks comes from task_ids length, not the fetched slice.
    _section_header("TASKS", total_tasks)
    _print_rows([_task_cells(t) for t in tasks], headers=_TASK_HEADERS)
    overflow = total_tasks - len(tasks)
    if overflow:
        _overflow_hint(overflow, f"caflou task list --filter project_id={id}")

    _print_section(
        "DOCUMENTS", docs, _document_cells, limit,
        f"caflou document list --filter project_id={id}",
        headers=_DOCUMENT_HEADERS,
    )


def contact_context(
    id: int,
    client: ClientProtocol,
    limit: Optional[int] = _DEFAULT_LIMIT,
    json_output: bool = False,
) -> None:
    """Context view for a contact: company, projects."""
    contact = client.get(f"contacts/{id}")
    enrich_from_entity(client.account_id, "contacts", [contact])
    company_id = contact.get("company_id")

    company = _safe(lambda: client.get(f"companies/{company_id}")) if company_id else None
    if company:
        enrich_from_entity(client.account_id, "companies", [company])

    projects = (
        _list_results(client, "projects", {"company_id": company_id},
                      post_filter=lambda r: r.get("company_id") == company_id)
        if company_id else []
    )

    if json_output:
        print_json({
            "contact": contact,
            "company": company,
            "projects": projects or [],
        })
        return

    typer.echo("  ".join(x for x in [
        "CONTACT", str(contact["id"]), contact.get("name") or "",
        contact.get("email") or "",
        contact.get("phone") or contact.get("mobile") or "",
    ] if x))

    if company_id and company is None:
        _failed("COMPANY")
    elif company:
        _section_header("COMPANY")
        _print_rows([_company_cells(company)], headers=_COMPANY_HEADERS)

    _print_section(
        "PROJECTS", projects, _project_cells, limit,
        f"caflou project list --filter company_id={company_id}",
        headers=_PROJECT_HEADERS,
    )


def company_context(
    id: int,
    client: ClientProtocol,
    limit: Optional[int] = _DEFAULT_LIMIT,
    json_output: bool = False,
) -> None:
    """Context view for a company: contacts, projects, documents."""
    company = client.get(f"companies/{id}")
    enrich_from_entity(client.account_id, "companies", [company])

    contacts = _contacts_for_company(client, id)
    projects = _list_results(client, "projects", {"company_id": id},
                             post_filter=lambda r: r.get("company_id") == id)
    docs = _list_results(client, "invoices", {"to_company_id": id},
                         post_filter=lambda r: r.get("to_company_id") == id)

    if json_output:
        print_json({
            "company": company,
            "contacts": contacts or [],
            "projects": projects or [],
            "documents": docs or [],
        })
        return

    typer.echo("  ".join(x for x in [
        "COMPANY", str(company["id"]), company.get("name") or "",
        company.get("company_type_name") or "",
        company.get("company_status_name") or "",
        company.get("email") or "",
    ] if x))

    _print_section(
        "CONTACTS", contacts, _contact_cells, limit,
        f"caflou contact list --filter company_id={id}",
        headers=_CONTACT_HEADERS,
    )
    _print_section(
        "PROJECTS", projects, _project_cells, limit,
        f"caflou project list --filter company_id={id}",
        headers=_PROJECT_HEADERS,
    )
    _print_section(
        "DOCUMENTS", docs, _document_cells, limit,
        f"caflou document list --filter to_company_id={id}",
        headers=_DOCUMENT_HEADERS,
    )


# Document chain field names on an Invoice response → label for display
_DOC_CHAIN_FIELDS = [
    ("offer_ids",       "Offer"),
    ("order_ids",       "Order"),
    ("proforma_ids",    "Proforma"),
    ("invoice_ids",     "Invoice"),
    ("delivery_ids",    "Delivery"),
    ("storno_ids",      "Storno"),
    ("tax_receipt_ids", "Tax receipt"),
]


def _collect_chain_ids(doc: dict) -> list[tuple[int, str]]:
    """Return (id, kind_label) pairs from all non-empty chain ID arrays on an invoice."""
    pairs = []
    for field, label in _DOC_CHAIN_FIELDS:
        for eid in doc.get(field) or []:
            pairs.append((eid, label))
    return pairs


def document_context(
    id: int,
    client: ClientProtocol,
    limit: Optional[int] = _DEFAULT_LIMIT,
    json_output: bool = False,
) -> None:
    """Context view for a document: buyer company, project, payments, related documents."""
    doc = client.get(f"invoices/{id}")
    enrich_from_entity(client.account_id, "invoices", [doc])
    company_id = doc.get("to_company_id")
    project_id = doc.get("project_id")

    company = _safe(lambda: client.get(f"companies/{company_id}")) if company_id else None
    if company:
        enrich_from_entity(client.account_id, "companies", [company])

    project = _safe(lambda: client.get(f"projects/{project_id}")) if project_id else None
    if project:
        enrich_from_entity(client.account_id, "projects", [project])

    transfers = _list_results(client, "transfers", {"invoice_id": id},
                             post_filter=lambda r: r.get("invoice_id") == id)

    # Related documents come from the invoice's own ID arrays — authoritative, no filter guessing.
    chain_pairs = _collect_chain_ids(doc)
    chain_ids = [eid for eid, _ in chain_pairs]
    chain_labels = {eid: label for eid, label in chain_pairs}
    related_docs, total_related = _fetch_by_ids(client, "invoices", chain_ids, limit)

    if json_output:
        print_json({
            "document": doc,
            "company": company,
            "project": project,
            "payments": transfers or [],
            "related_documents": related_docs,
        })
        return

    paid = "paid" if doc.get("paid") else "unpaid"
    typer.echo("  ".join(x for x in [
        "DOCUMENT", str(doc["id"]),
        doc.get("number") or doc.get("name") or "",
        doc.get("global_kind") or "",
        doc.get("invoice_state_name") or "",
        _money(doc.get("total_cache"), doc.get("currency")),
        paid,
    ] if x))

    if company_id and company is None:
        _failed("BUYER")
    elif company:
        _section_header("BUYER")
        _print_rows([_company_cells(company)], headers=_COMPANY_HEADERS)

    if project_id and project is None:
        _failed("PROJECT")
    elif project:
        _section_header("PROJECT")
        _print_rows([_project_cells(project)], headers=_PROJECT_HEADERS)

    _print_section(
        "PAYMENTS", transfers, _transfer_cells, limit,
        f"caflou transfer list --filter invoice_id={id}",
        headers=_TRANSFER_HEADERS,
    )

    if total_related:
        _section_header("RELATED DOCUMENTS", total_related)
        _print_rows([
            [chain_labels.get(r.get("id"), "?"), str(r.get("id", "-")),
             r.get("number") or r.get("name") or "-",
             r.get("invoice_state_name") or "-",
             _money(r.get("total_cache"), r.get("currency"))]
            for r in related_docs
        ], headers=["KIND", "ID", "NUMBER", "STATE", "TOTAL"])
        overflow = total_related - len(related_docs)
        if overflow:
            _overflow_hint(overflow, f"caflou document get {id} --json | jq '.related_documents'")


def task_context(
    id: int,
    client: ClientProtocol,
    limit: Optional[int] = _DEFAULT_LIMIT,
    json_output: bool = False,
) -> None:
    """Context view for a task: project, company, subtasks."""
    task = client.get(f"tasks/{id}")
    enrich_from_entity(client.account_id, "tasks", [task])
    project_id = task.get("project_id")

    project = _safe(lambda: client.get(f"projects/{project_id}")) if project_id else None
    if project:
        enrich_from_entity(client.account_id, "projects", [project])

    company_id = (project.get("company_id") if project else None) or task.get("company_id")
    company = _safe(lambda: client.get(f"companies/{company_id}")) if company_id else None
    if company:
        enrich_from_entity(client.account_id, "companies", [company])

    subtasks = _list_results(client, "tasks", {"parent_id": id},
                            post_filter=lambda r: r.get("parent_id") == id)

    if json_output:
        print_json({
            "task": task,
            "project": project,
            "company": company,
            "subtasks": subtasks or [],
        })
        return

    due = f"due {task['due_date']}" if task.get("due_date") else ""
    typer.echo("  ".join(x for x in [
        "TASK", str(task["id"]), task.get("name") or "",
        task.get("task_status_name") or "", due,
    ] if x))

    if project_id and project is None:
        _failed("PROJECT")
    elif project:
        _section_header("PROJECT")
        _print_rows([_project_cells(project)], headers=_PROJECT_HEADERS)

    if company_id and company is None:
        _failed("COMPANY")
    elif company:
        _section_header("COMPANY")
        _print_rows([_company_cells(company)], headers=_COMPANY_HEADERS)

    _print_section(
        "SUBTASKS", subtasks, _task_cells, limit,
        f"caflou task list --filter parent_id={id}",
        headers=_TASK_HEADERS,
    )
