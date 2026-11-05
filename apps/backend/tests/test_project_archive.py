import asyncio
from datetime import date
import os
from uuid import uuid4

import pytest

from app.api.routes.projects import ProjectArchiveChange
from app.security import project_write_action


def test_archive_action_is_separate_from_status_permission():
    assert project_write_action("overview", "PATCH", "/api/v1/projects/id/archive") == "archive_project"
    assert project_write_action("overview", "PATCH", "/api/v1/projects/id/status") == "update_status"


def test_archive_requires_reason_and_version():
    from pydantic import ValidationError
    for reason in ["", "  ", "x" * 501]:
        with pytest.raises(ValidationError):
            ProjectArchiveChange(archived=True, reason=reason, expected_version=1)


@pytest.mark.parametrize(("problem", "expected"), [
    ("vendor", "Outstanding vendor payments"),
    ("client", "Outstanding client billing"),
    ("worker", "Outstanding worker payments"),
    ("claim", "Unpaid certified claim"),
    ("certification", "awaiting certification"),
    ("addendum", "awaiting approval"),
    ("stock", "Remaining inventory"),
    ("unreceived", "Unreceived ordered inventory"),
    ("approval", "Approve the projected"),
    ("stale", "out of date"),
    ("active", "Only Completed or Cancelled"),
    ("planning", "Only Completed or Cancelled"),
    ("hold", "Only Completed or Cancelled"),
    ("currency", "INR projects only"),
])
def test_readiness_reports_specific_outstanding_items(monkeypatch, problem, expected):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.api.routes import cashbook, labor, operations, procurement, projects
    project = SimpleNamespace(id=uuid4(), status={"active": "Active", "planning": "Planning", "hold": "On Hold"}.get(problem, "Cancelled"), archived_at=None, currency="USD" if problem == "currency" else "INR")
    monkeypatch.setattr(projects, "dashboard", AsyncMock(return_value={"open_commitments": "5" if problem == "vendor" else "0"}))
    monkeypatch.setattr(operations, "billing_summary", AsyncMock(return_value={"outstanding_invoices": "5" if problem == "client" else "0"}))
    monkeypatch.setattr(labor, "labor_ledger", AsyncMock(return_value={"workers": [{"payable": "5" if problem == "worker" else "0"}]}))
    claim = {"status": "Pending certification" if problem == "certification" else "Certified", "claim_number": "CL-1", "payable": "5" if problem == "claim" else "0"}
    monkeypatch.setattr(labor, "list_labor_contracts", AsyncMock(return_value={"contracts": [{"contract_number": "LC-1", "claims": [claim], "addenda": [{"status": "Pending approval" if problem == "addendum" else "Approved"}]}]}))
    stock = {"item": {"name": "Bricks", "unit_of_measure": "unit"}, "available_quantity": "5" if problem == "stock" else "0", "open_order_quantity": "5" if problem == "unreceived" else "0"}
    monkeypatch.setattr(procurement, "project_inventory", AsyncMock(return_value={"items": [stock]}))
    monkeypatch.setattr(cashbook, "overview_projection", AsyncMock(return_value={"fingerprint": "new"}))
    approval = None if problem == "approval" else SimpleNamespace(snapshot={"fingerprint": "old" if problem == "stale" else "new"})
    db = SimpleNamespace(scalar=AsyncMock(return_value=approval))
    result = asyncio.run(projects.archive_readiness(project, SimpleNamespace(), db))
    assert not result["can_archive"]
    assert any(expected in message for message in result["blockers"]), result


@pytest.mark.skipif(os.environ.get("VRIDHI_TEST_POSTGRES") != "1", reason="Transactional PostgreSQL test requires opt-in")
def test_archive_end_to_end():
    asyncio.run(archive_scenario())


async def archive_scenario():
    import httpx
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from app.core.config import settings
    from app.db import get_db
    from app.main import app
    from app.models import AuditEvent, BillingEntry, CashReceipt, LaborWagePayment, LaborWorkEntry, LaborWorker, Project, ProjectMembership
    from app.security import current_user, require_csrf

    engine = create_async_engine(settings.database_url)
    overrides = dict(app.dependency_overrides)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                schema = "archive_test_" + uuid4().hex
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))

                def migrate(sync_connection):
                    from alembic.config import Config
                    from alembic.migration import MigrationContext
                    from alembic.operations import Operations
                    from alembic.script import ScriptDirectory
                    with Operations.context(MigrationContext.configure(sync_connection)):
                        for revision in reversed(list(ScriptDirectory.from_config(Config("alembic.ini")).walk_revisions())):
                            revision.module.upgrade()
                await connection.run_sync(migrate)
                async with AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as db:
                    from app.models import User
                    profile = {"access": "allow", "read": {"export_report": True}, "write": {"mode": "all", "actions": {}}}
                    actor = User(id=uuid4(), username="archive-test", name="Archive Test", password_hash="unused", global_access=True, active=True, global_permissions={module: profile for module in ["overview", "procurement", "cashflow", "inventory", "labor"]})
                    db.add(actor)
                    await db.flush()
                    projects = [Project(id=uuid4(), name=f"Archive sample {i:03}", location="Test", status="Completed", baseline_budget=0, currency="INR", start_date=date.today(), created_by_id=actor.id) for i in range(131)]
                    db.add_all(projects)
                    await db.commit()
                    project = projects[0]

                    async def database():
                        yield db

                    async def identity():
                        return actor

                    app.dependency_overrides[get_db] = database
                    app.dependency_overrides[current_user] = identity
                    app.dependency_overrides[require_csrf] = lambda: None
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                        base = f"/api/v1/projects/{project.id}"

                        async def archive(archived=True, version=None, expected=200):
                            response = await client.patch(base + "/archive", json={"archived": archived, "reason": "Reviewed for storage", "expected_version": version or project.version})
                            assert response.status_code == expected, response.text
                            return response

                        async def approve():
                            data = (await client.get("/api/v1/company-cashbook")).json()
                            row = next(p for p in data["projects"] if p["id"] == str(project.id))
                            result = await client.post("/api/v1/company-cashbook/result-approvals", json={"request_id": str(uuid4()), "project_id": str(project.id), "as_of": date.today().isoformat(), "fingerprint": row["calculated"]["fingerprint"], "note": "Reviewed projection"})
                            assert result.status_code == 201, result.text

                        # Server pagination and totals work beyond the old first-100 boundary.
                        first = (await client.get("/api/v1/me/projects", params={"scope": "current", "page_size": 100})).json()
                        second = (await client.get("/api/v1/me/projects", params={"scope": "current", "page_size": 100, "page": 2})).json()
                        assert first["total"] == 131 and len(first["items"]) == 100
                        assert len(second["items"]) == 31 and first["status_counts"]["Completed"] == 131
                        response = await archive(expected=409)
                        assert "Approve the projected" in response.text
                        await approve()

                        # Outstanding billing must block, even with unallocated receipts elsewhere.
                        bill = BillingEntry(project_id=project.id, application_number="TEST", description="Bill", submitted_date=date.today(), amount=50, status="Submitted")
                        db.add(bill)
                        await db.commit()
                        assert "Outstanding client billing" in (await archive(expected=409)).text
                        db.add(CashReceipt(project_id=project.id, billing_entry_id=bill.id, received_date=date.today(), amount=50, payment_method="Cash", recorded_by_id=actor.id))
                        await db.commit()

                        worker = LaborWorker(project_id=project.id, name="Worker", trade="Test", active=True)
                        db.add(worker)
                        await db.flush()
                        db.add(LaborWorkEntry(project_id=project.id, worker_id=worker.id, work_date=date.today(), description="Work", quantity=1, unit="day", rate=10, recorded_by_id=actor.id))
                        await db.commit()
                        assert "Outstanding worker payments" in (await archive(expected=409)).text
                        db.add(LaborWagePayment(project_id=project.id, worker_id=worker.id, payment_date=date.today(), amount=10, payment_mode="Cash", recorded_by_id=actor.id))
                        await db.commit()
                        assert "out of date" in (await archive(expected=409)).text
                        await approve()

                        for status in ["Planning", "Active", "On Hold"]:
                            project.status = status
                            await db.commit()
                            assert "Only Completed or Cancelled" in (await archive(expected=409)).text
                        project.status = "Completed"
                        await db.commit()
                        before = (await client.get("/api/v1/company-cashbook")).json()["project_totals"]
                        version = project.version
                        archived_response = (await archive()).json()
                        assert archived_response["archived_by_username"] == "archive-test"
                        assert project.archived_at is not None and project.status == "Completed"
                        assert (await client.get("/api/v1/company-cashbook")).json()["project_totals"] == before
                        assert (await client.get("/api/v1/me/projects")).json()["total"] == 130
                        archived = (await client.get("/api/v1/me/projects?scope=archived")).json()
                        assert archived["total"] == 1 and archived["items"][0]["id"] == str(project.id)
                        assert archived["items"][0]["archived_by_username"] == "archive-test"
                        assert (await client.get(base)).json()["archived_by_username"] == "archive-test"
                        assert (await client.get(base + "/dashboard")).status_code == 200

                        # Business writes blocked in every project module, but visits/report requests still work.
                        for path in ["/documents", "/cash-receipts", "/progress-billings", "/purchase-orders", "/inventory/transactions", "/labor/workers", "/labor/contracts", "/timecards"]:
                            response = await client.post(base + path, json={})
                            assert response.status_code == 409, (path, response.text)
                            assert "archived" in response.text
                        assert (await client.post(base + "/activities", json={"module": "overview", "activity": "export"})).status_code == 204
                        transfer = await client.post("/api/v1/company-cashbook/entries", json={"request_id": str(uuid4()), "transaction_date": date.today().isoformat(), "kind": "project_funding", "category": "Project transfer", "amount": "1", "party": "Test", "description": "Transfer", "account": "Bank", "payment_mode": "Cash", "project_id": str(project.id)})
                        assert transfer.status_code == 409, transfer.text
                        await archive(False, version=version, expected=409)
                        await archive(False)
                        assert project.archived_at is None and project.status == "Completed"

                        # One combined action, including Global profile and project override.
                        blocked = {"access": "allow", "read": {"export_report": True}, "write": {"mode": "partial", "actions": {"update_status": True}}}
                        actor.global_permissions = {"overview": blocked}
                        await db.commit()
                        await archive(expected=403)
                        grant = {**blocked, "write": {"mode": "partial", "actions": {"archive_project": True}}}
                        actor.global_permissions = {"overview": grant}
                        await db.commit()
                        await archive()
                        link = ProjectMembership(project_id=project.id, user_id=actor.id, permissions={"overview": blocked})
                        db.add(link)
                        await db.commit()
                        await archive(False, expected=403)
                        link.permissions = {"overview": grant}
                        actor.global_access = False
                        await db.commit()
                        await archive(False)
                        events = list((await db.scalars(select(AuditEvent).where(AuditEvent.project_id == project.id, AuditEvent.action.in_(["project_archived", "project_unarchived"])))).all())
                        assert len(events) == 4 and all(event.details["reason"] and "after" in event.details for event in events)
                        blocked_events = list((await db.scalars(select(AuditEvent).where(AuditEvent.project_id == project.id, AuditEvent.action == "project_archive_blocked"))).all())
                        assert blocked_events and all(event.details["reason"] and event.details["blockers"] for event in blocked_events)
                        actor.global_access = True
                        await db.commit()
                        log = (await client.get(base + "/audit-log?search=Archive%20request%20blocked")).json()
                        assert log["total"] == len(blocked_events) and log["items"][0]["activity"] == "Archive request blocked"
                        log = (await client.get(base + "/audit-log?search=UnArchived%20project")).json()
                        assert log["total"] == 2 and log["items"][0]["activity"] == "UnArchived project"
            finally:
                app.dependency_overrides.clear()
                app.dependency_overrides.update(overrides)
                await transaction.rollback()
    finally:
        await engine.dispose()
