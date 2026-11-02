import asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
from uuid import uuid4

from fastapi import HTTPException
import pytest
from pydantic import ValidationError

from app.api.routes.admin import validate_cashbook_grant
from app.api.routes.cashbook import CashEntryCreate, ProjectResultCreate, cash_summary
from app.models import CompanyCashEntry, CompanyProjectResult, User
from app.security import cashbook_grants, require_cashbook


def entry(kind, amount, day=1, **values):
    values.setdefault("direction", "in" if kind in {"opening_in", "owner_capital", "project_received", "other_receipt"} else "out")
    values.setdefault("account", "Bank")
    values.setdefault("party", "Partner")
    values.setdefault("category", "Furniture")
    return CompanyCashEntry(kind=kind, amount=Decimal(amount), transaction_date=date(2026, 1, day), **values)


def test_cash_summary_reconciles_to_paise_and_excludes_voided_and_future():
    entries = [
        entry("opening_in", "100.25"),
        entry("owner_capital", "50.10", 2),
        entry("company_expense", "20.05", 3),
        entry("project_funding", "5.01", 4),
        entry("owner_withdrawal", "2.02", 5),
        entry("project_received", "3.03", 6),
        entry("other_receipt", "1000", 7, voided_at=date(2026, 1, 8)),
        entry("other_receipt", "9999", 20),
    ]
    summary = cash_summary(entries, date(2026, 1, 3), date(2026, 1, 10))
    assert summary["opening_balance"] == "150.35"
    assert summary["opening_entries"] == "0.00"
    assert summary["money_in"] == "3.03"
    assert summary["money_out"] == "27.08"
    assert summary["closing_balance"] == "126.30"
    assert summary["company_spending"] == "20.05"
    assert summary["expense_categories"] == [{"category": "Furniture", "amount": "20.05"}]
    assert summary["accounts"] == [{"account": "Bank", "balance": "126.30"}]
    lifetime = cash_summary(entries, None, date(2026, 1, 10))
    assert lifetime["opening_entries"] == "100.25"
    assert lifetime["opening_balance"] == "100.25", "Opening balance includes starting balances entered within the range"
    assert lifetime["money_in"] == "53.13"
    assert lifetime["closing_balance"] == summary["closing_balance"]
    assert lifetime["owners"] == [{"owner": "Partner", "capital": "50.10", "withdrawals": "2.02", "net": "48.08"}]


def test_negative_starting_balance_and_empty_register():
    summary = cash_summary([entry("opening_out", "20.50")], None, date(2026, 1, 1))
    assert summary["closing_balance"] == "-20.50"
    assert summary["money_out"] == "0.00"
    assert cash_summary([], None, date.today())["closing_balance"] == "0.00"


def cash_payload(**updates):
    return {
        "request_id": uuid4(), "transaction_date": date.today(), "kind": "company_expense",
        "category": "Furniture", "amount": "10.25", "party": "Supplier", "description": "Office desk",
        "account": "Bank", "payment_mode": "Bank transfer", **updates,
    }


@pytest.mark.parametrize("updates", [
    {"amount": "NaN"}, {"amount": "Infinity"}, {"amount": "0"}, {"amount": "-1"},
    {"amount": "1.001"}, {"amount": "10000000000000000"},
    {"party": "   "}, {"transaction_date": date.today() + timedelta(days=1)},
    {"kind": "project_funding", "category": "Project transfer"},
    {"project_id": uuid4()}, {"category": "   "},
    {"account": ""}, {"account": "   "}, {"account": "", "payment_mode": "UPI"}, {"account": "", "payment_mode": "Cheque"},
])
def test_entry_validation(updates):
    with pytest.raises(ValidationError):
        CashEntryCreate.model_validate(cash_payload(**updates))


@pytest.mark.parametrize(("updates", "allowed"), [
    ({}, True),
    ({"category": "Capital contribution"}, False),
    ({"category": "Office cleaning"}, True),
    ({"category": "Unknown"}, False),
    ({"category": "Annual premium"}, False),
    ({"custom_category": "Insurance", "category": "Annual premium"}, True),
    ({"custom_category": "Insurance", "category": "Company purchases"}, False),
    ({"custom_category": "Insurance", "category": "Office cleaning"}, False),
    ({"custom_category": "Unknown", "category": "Annual premium"}, False),
])
def test_entry_options_validate_registered_values(updates, allowed):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock
    from app.api.routes.cashbook import validate_entry_options
    options = [
        SimpleNamespace(option_type="type", parent="", name="Office cleaning", direction="in"),
        SimpleNamespace(option_type="category", parent="", name="Insurance"),
        SimpleNamespace(option_type="type", parent="Insurance", name="Annual premium", direction="out"),
    ]
    db = MagicMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=lambda: options))
    payload = CashEntryCreate.model_validate(cash_payload(**updates))
    if allowed:
        direction = asyncio.run(validate_entry_options(db, payload))
        assert direction == ("in" if payload.category == "Office cleaning" else "out")
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(validate_entry_options(db, payload))
        assert error.value.status_code == 422
    assert "company_cash_options.kind =" in str(db.scalars.call_args.args[0])


def test_only_administrators_can_add_options():
    from app.api.routes.cashbook import CashOptionCreate, create_option
    payload = CashOptionCreate(option_type="type", kind="company_expense", name="Insurance", direction="out")
    with pytest.raises(HTTPException) as error:
        asyncio.run(create_option(payload, User(global_access=False), None))
    assert error.value.status_code == 403


@pytest.mark.parametrize("payload", [
    {"option_type": "category", "kind": "owner_capital", "name": "Partner capital"},
    {"option_type": "category", "kind": "owner_capital", "name": "Partner capital", "first_type": "Loan", "parent": "X"},
    {"option_type": "type", "kind": "owner_capital", "name": "Loan", "first_type": "Other"},
])
def test_new_category_requires_first_type(payload):
    from app.api.routes.cashbook import CashOptionCreate
    with pytest.raises(ValidationError):
        CashOptionCreate.model_validate({**payload, "direction": "out"})


@pytest.mark.parametrize("direction", [None, "", "sideways"])
def test_transaction_type_requires_valid_direction(direction):
    from app.api.routes.cashbook import CashOptionCreate
    with pytest.raises(ValidationError):
        CashOptionCreate(option_type="type", kind="paid", name="Shop refund", direction=direction)


def test_paid_salary_and_mixed_directions_reconcile():
    rows = [
        entry("opening_in", "1000.00"),
        entry("paid", "100.25", 2, direction="out"),
        entry("salary", "200.10", 2, direction="out"),
        entry("paid", "20.05", 3, direction="in"),
        entry("salary", "10.10", 3, direction="in"),
        entry("salary", "999.00", 3, direction="out", voided_at=date(2026, 1, 4)),
    ]
    summary = cash_summary(rows, None, date(2026, 1, 4))
    assert summary["money_in"] == "30.15"
    assert summary["money_out"] == "300.35"
    assert summary["closing_balance"] == "729.80"
    assert summary["company_spending"] == "270.20"
    assert summary["kind_totals"]["paid"] == "80.20"
    assert summary["kind_totals"]["salary"] == "190.00"
    assert summary["accounts"] == [{"account": "Bank", "balance": "729.80"}]
    later = cash_summary(rows, date(2026, 1, 3), date(2026, 1, 4))
    assert later["opening_balance"] == "699.65"
    assert later["closing_balance"] == "729.80"


def test_borrowings_track_principal_and_interest_by_lender():
    rows = [
        entry("borrowings", "1000.00", 1, category="Loan received", party="Bank A", direction="in"),
        entry("borrowings", "250.00", 2, category="Loan repayment – principal", party="Bank A", direction="out"),
        entry("borrowings", "400.00", 2, category="Loan received", party="Lender B", direction="in"),
        entry("borrowings", "25.00", 3, category="Loan interest", party="Bank A", direction="out"),
        entry("borrowings", "50.00", 4, category="Loan repayment – principal", party="Bank A", direction="out", voided_at=date(2026, 1, 5)),
    ]
    summary = cash_summary(rows, None, date(2026, 1, 3))
    assert summary["money_in"] == "1400.00"
    assert summary["money_out"] == "275.00"
    assert summary["closing_balance"] == "1125.00"
    assert summary["company_spending"] == "25.00"
    assert summary["expense_categories"] == [{"category": "Loan interest", "amount": "25.00"}]
    assert summary["kind_totals"]["borrowings"] == "1150.00"
    assert summary["borrowings"] == [
        {"lender": "Bank A", "borrowed": "1000.00", "repaid": "250.00", "interest": "25.00", "outstanding": "750.00"},
        {"lender": "Lender B", "borrowed": "400.00", "repaid": "0.00", "interest": "0.00", "outstanding": "400.00"},
    ]
    assert (summary["borrowings_outstanding"], summary["borrowings_borrowed"], summary["borrowings_repaid"], summary["borrowings_interest"]) == ("1150.00", "1400.00", "250.00", "25.00")
    later = cash_summary(rows, date(2026, 1, 4), date(2026, 1, 5))
    assert later["borrowings_outstanding"] == "1150.00"


def test_borrowings_are_not_recorded_as_general_transactions():
    from unittest.mock import MagicMock
    from app.api.routes.cashbook import KINDS, validate_entry_options
    assert KINDS["borrowings"] == ["Loan received", "Loan repayment – principal", "Loan interest"]
    assert "Loan interest" not in KINDS["company_expense"]
    payload = CashEntryCreate.model_validate(cash_payload(kind="borrowings", category="Loan received"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(validate_entry_options(MagicMock(), payload))
    assert error.value.status_code == 422


def borrowing_payload(**updates):
    return {"request_id": uuid4(), "action": "repayment", "transaction_date": date.today(), "lender": "Bank A", "principal": "100.00",
            "interest": "5.25", "description": "EMI", "account": "Bank", "payment_mode": "Bank transfer", **updates}


@pytest.mark.parametrize("updates", [
    {"action": "loan", "principal": "0"}, {"action": "loan", "interest": "1.00"}, {"principal": "0", "interest": "0"},
    {"principal": "-1"}, {"interest": "1.001"}, {"lender": "  "}, {"description": " "},
    {"transaction_date": date.today() + timedelta(days=1)}, {"account": "", "payment_mode": "UPI"}, {"action": "transfer"},
])
def test_borrowing_validation(updates):
    from app.api.routes.cashbook import BorrowingCreate
    with pytest.raises(ValidationError):
        BorrowingCreate.model_validate(borrowing_payload(**updates))


def test_borrowing_repayment_can_be_interest_only():
    from app.api.routes.cashbook import BorrowingCreate
    payload = BorrowingCreate.model_validate(borrowing_payload(principal="0", account="", payment_mode="Cash"))
    assert payload.interest == Decimal("5.25")
    assert payload.account == "Cash"


@pytest.mark.parametrize(("kind", "transaction_types"), [
    ("paid", ["Paid to Pending", "Paid to Shop", "Paid to Electricity", "Paid to Wifi"]),
    ("salary", ["Salary to Contractors", "Salary to Manager", "Salary to Security", "Salary to Driver"]),
])
def test_requested_category_hierarchy(kind, transaction_types):
    from unittest.mock import AsyncMock, MagicMock
    from app.api.routes.cashbook import KINDS, validate_entry_options
    assert KINDS[kind] == transaction_types
    db = MagicMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=lambda: []))
    for name in transaction_types:
        payload = CashEntryCreate.model_validate(cash_payload(kind=kind, category=name))
        assert asyncio.run(validate_entry_options(db, payload)) == "out"
    payload = CashEntryCreate.model_validate(cash_payload(kind=kind, category="Furniture"))
    with pytest.raises(HTTPException):
        asyncio.run(validate_entry_options(db, payload))



@pytest.mark.parametrize(("mode", "typed", "saved"), [
    ("Cash", "", "Cash"), ("Cash", "  ", "Cash"), ("Other", "", "Others"),
    ("Cash", "Site petty cash", "Site petty cash"), ("Other", "Director card", "Director card"),
])
def test_cash_and_other_accounts_are_optional(mode, typed, saved):
    assert CashEntryCreate.model_validate(cash_payload(payment_mode=mode, account=typed)).account == saved

def test_result_accepts_loss_and_requires_basis():
    valid = dict(request_id=uuid4(), project_id=uuid4(), as_of=date.today(), amount="-100.01", basis="Confirmed against signed final accounts")
    assert ProjectResultCreate(**valid).amount == Decimal("-100.01")
    with pytest.raises(ValidationError):
        ProjectResultCreate(**{**valid, "basis": "  "})


def test_cashbook_permissions_are_independent_and_default_denied():
    user = User(global_access=False)
    assert cashbook_grants(user) == {"read": False, "write": False, "export_report": False}
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_cashbook()(user))
    assert error.value.status_code == 403
    user.cashbook_permissions = {"access": "allow", "write": {"mode": "partial", "actions": {"record": False}}, "read": {"export_report": True}}
    assert cashbook_grants(user) == {"read": True, "write": False, "export_report": True}
    assert asyncio.run(require_cashbook("export_report")(user)) is user
    with pytest.raises(HTTPException):
        asyncio.run(require_cashbook("write")(user))
    user.global_access = True
    assert all(cashbook_grants(user).values())


def test_cannot_delegate_cashbook_grants_actor_does_not_have():
    actor = User(global_access=False)
    profile = {"access": "allow", "read": {"export_report": True}, "write": {"mode": "all"}}
    with pytest.raises(HTTPException):
        validate_cashbook_grant(actor, profile)
    validate_cashbook_grant(actor, profile, profile)
    actor.global_access = True
    validate_cashbook_grant(actor, profile)


def test_company_audit_permission_is_independent_of_cashbook():
    from app.security import company_audit_grants, require_company_audit
    from app.api.routes.admin import validate_company_audit_grant
    user = User(global_access=False, cashbook_permissions={"access": "allow", "write": {"mode": "all"}, "read": {"export_report": True}})
    assert company_audit_grants(user) == {"read": False, "export_report": False}
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_company_audit()(user))
    assert error.value.status_code == 403
    profile = {"access": "allow", "read": {"export_report": False}, "write": {"mode": "partial", "actions": {}}}
    with pytest.raises(HTTPException):
        validate_company_audit_grant(user, profile)
    auditor = User(global_access=False, company_audit_permissions=profile)
    assert company_audit_grants(auditor) == {"read": True, "export_report": False}
    assert cashbook_grants(auditor)["read"] is False
    assert asyncio.run(require_company_audit()(auditor)) is auditor
    validate_company_audit_grant(auditor, profile)
    export_profile = {**profile, "read": {"export_report": True}}
    with pytest.raises(HTTPException):
        validate_company_audit_grant(auditor, export_profile)
    with pytest.raises(HTTPException):
        asyncio.run(require_company_audit("export_report")(auditor))
    auditor.company_audit_permissions = export_profile
    assert asyncio.run(require_company_audit("export_report")(auditor)) is auditor
    validate_company_audit_grant(auditor, export_profile)
    auditor.company_audit_permissions = {**export_profile, "access": "block"}
    assert company_audit_grants(auditor) == {"read": False, "export_report": False}
    assert company_audit_grants(User(global_access=True)) == {"read": True, "export_report": True}


def test_approval_requires_global_access():
    from app.api.routes.cashbook import approve_result, ResultApprovalCreate
    actor = User(global_access=False, cashbook_permissions={"access": "allow", "write": {"mode": "all"}})
    payload = ResultApprovalCreate(request_id=uuid4(), project_id=uuid4(), as_of=date.today(), fingerprint="a" * 64, note="Reviewed result")
    with pytest.raises(HTTPException) as error:
        asyncio.run(approve_result(payload, actor, None))
    assert error.value.status_code == 403


def test_user_history_does_not_bypass_company_financial_access():
    from unittest.mock import AsyncMock, MagicMock
    from app.api.routes.admin import user_history
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(all=lambda: []))
    db.scalar = AsyncMock(return_value=0)
    asyncio.run(user_history(uuid4(), 1, 5, "", User(global_access=False), db))
    query = db.execute.call_args.args[0]
    assert "CompanyCashbook" in query.compile().params.values()
    assert "audit_events.entity_type !=" in str(query)


@pytest.mark.skipif(os.environ.get("VRIDHI_TEST_POSTGRES") != "1", reason="Explicit opt-in required for transactional PostgreSQL integration test")
def test_postgres_cashbook_end_to_end():
    asyncio.run(postgres_scenario())


async def postgres_scenario():
    import httpx
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from app.core.config import settings
    from app.db import get_db
    from app.main import app
    from app.models import AuditEvent, Project
    from app.security import current_user, require_csrf

    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                # All tables, data and schema are rolled back; no live application records are used.
                schema = "cashbook_test_" + uuid4().hex
                await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
                await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
                def migrate(sync_connection):
                    from alembic.config import Config
                    from alembic.migration import MigrationContext
                    from alembic.operations import Operations
                    from alembic.script import ScriptDirectory
                    context = MigrationContext.configure(sync_connection)
                    revisions = ScriptDirectory.from_config(Config("alembic.ini"))
                    with Operations.context(context):
                        for revision in reversed(list(revisions.walk_revisions())):
                            revision.module.upgrade()
                await connection.run_sync(migrate)
                async with AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as db:
                    actor = User(id=uuid4(), username="test-finance", email=None, name="Test Finance", password_hash="unused", global_access=True, active=True)
                    project = Project(id=uuid4(), name="Test Project", location="Test", status="Active", baseline_budget=0, currency="INR", start_date=date.today(), created_by_id=actor.id)
                    db.add(actor)
                    await db.flush()
                    db.add(project)
                    await db.commit()
                    project_id = str(project.id)
                    async def database():
                        yield db
                    async def identity():
                        await db.refresh(actor)
                        return actor
                    app.dependency_overrides[get_db] = database
                    app.dependency_overrides[current_user] = identity
                    app.dependency_overrides[require_csrf] = lambda: None
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                        async def post(path, payload, expected=201):
                            response = await client.post("/api/v1/company-cashbook" + path, json=payload)
                            assert response.status_code == expected, response.text
                            return response.json()

                        payload = cash_payload(amount="1000.25")
                        payload = {key: str(value) if key in {"request_id", "transaction_date"} else value for key, value in payload.items()}
                        payload.update(kind="owner_capital", category="Capital contribution")
                        recorded = await post("/entries", payload)
                        exact_entry = await client.get(f"/api/v1/company-cashbook/records/{recorded['id']}")
                        assert exact_entry.status_code == 200, exact_entry.text
                        assert exact_entry.json()["type"] == "entry"
                        assert exact_entry.json()["record"]["id"] == recorded["id"]
                        assert exact_entry.json()["record"]["amount"] == "1000.25"
                        assert (await client.get(f"/api/v1/company-cashbook/records/{uuid4()}")).status_code == 404
                        assert (await client.get("/api/v1/company-cashbook/records/not-a-uuid")).status_code == 422
                        initial_activity = (await client.get("/api/v1/company-cashbook/audit-log")).json()["items"][0]
                        activity_export_url = f"/api/v1/company-cashbook/activities/{initial_activity['id']}/export"
                        assert (await client.post(activity_export_url, params={"source": "audit-log"})).status_code == 204
                        assert (await client.post(activity_export_url, params={"source": "history"})).status_code == 204
                        assert (await client.post(f"/api/v1/company-cashbook/activities/{uuid4()}/export", params={"source": "audit-log"})).status_code == 404
                        export_events = (await client.get("/api/v1/company-cashbook/history")).json()["items"]
                        activity_exports = [event for event in export_events if event["action"] == "cashbook_activity_export_requested"]
                        assert len(activity_exports) == 2
                        assert all(event["details"]["activity_id"] == initial_activity["id"] for event in activity_exports)
                        await post("/entries", payload, 409)
                        payload.update(request_id=str(uuid4()), amount="100.05", kind="company_expense", category="Furniture")
                        await post("/entries", payload)
                        for _ in range(103):
                            await post("/entries", {**payload, "request_id": str(uuid4()), "amount": "0.01"})
                        response = await client.get("/api/v1/company-cashbook")
                        assert response.status_code == 200, response.text
                        report = response.json()
                        assert report["summary"]["closing_balance"] == "899.17"
                        assert report["total"] == 105 and len(report["items"]) == 20
                        filtered = (await client.get("/api/v1/company-cashbook?category=Capital%20contribution")).json()
                        assert filtered["total"] == 1
                        assert filtered["summary"]["closing_balance"] == report["summary"]["closing_balance"]
                        assert filtered["filtered_in"] == "1000.25"
                        app.dependency_overrides.pop(require_csrf)
                        assert (await client.post("/api/v1/company-cashbook/entries", json=payload)).status_code == 403
                        app.dependency_overrides[require_csrf] = lambda: None
                        created_user = await client.post("/api/v1/users", json={
                            "name": "Cashbook Only", "username": "cashbook-only", "password": uuid4().hex,
                            "cashbook_permissions": {"access": "allow", "read": {"export_report": False}, "write": {"mode": "partial", "actions": {}}},
                        })
                        assert created_user.status_code == 201, created_user.text
                        assert created_user.json()["cashbook_permissions"]["access"] == "allow"
                        declaration = {"request_id": str(uuid4()), "project_id": project_id, "as_of": str(date.today() - timedelta(days=1)), "amount": "300", "basis": "Initial confirmed result"}
                        await post("/results", declaration, 409)
                        from app.models import BillingEntry, Contract, InventoryItem, InventoryTransaction, LaborWorker, LaborWorkEntry, LaborContract, LaborProgressClaim, PurchaseOrder, PurchaseOrderLine, Vendor
                        client_contract = Contract(project_id=project.id, number="TEST-CLIENT", original_value=Decimal("1000.25"), currency="INR")
                        vendor = Vendor(id=uuid4(), name="Test vendor")
                        material = InventoryItem(id=uuid4(), sku="TEST", name="Test material")
                        worker = LaborWorker(id=uuid4(), project_id=project.id, name="Test worker")
                        contract = LaborContract(id=uuid4(), project_id=project.id, contract_number="TEST-C1",
                                                 subcontractor_name="Test contractor", scope="Work", pricing_type="Fixed",
                                                 currency="INR", contract_value=500, created_by_id=actor.id)
                        db.add_all([client_contract, vendor, material, worker, contract])
                        await db.flush()
                        order = PurchaseOrder(id=uuid4(), number="TEST-PO", project_id=project.id, vendor_id=vendor.id,
                                              order_date=date.today(), currency="INR", approval_status="Approved", created_by_id=actor.id)
                        db.add(order)
                        await db.flush()
                        db.add(PurchaseOrderLine(purchase_order_id=order.id, item_id=material.id, description="Material", quantity=2, unit_price=Decimal("100.01")))
                        receipt = InventoryTransaction(project_id=project.id, item_id=material.id, transaction_type="receipt",
                                                       quantity=2, unit_cost=Decimal("100.01"), occurred_at=datetime.now(timezone.utc))
                        db.add_all([
                            receipt,
                            InventoryTransaction(project_id=project.id, item_id=material.id, transaction_type="issue", quantity=1, unit_cost=100),
                            LaborWorkEntry(project_id=project.id, worker_id=worker.id, work_date=date.today(), description="Site work", quantity=2, rate=Decimal("50.02"), recorded_by_id=actor.id),
                            LaborProgressClaim(project_id=project.id, contract_id=contract.id, claim_number="TEST-CLAIM", period_start=date.today(), period_end=date.today(), work_description="Certified work", amount=Decimal("50.05"), status="Certified", submitted_by_id=actor.id),
                            LaborProgressClaim(project_id=project.id, contract_id=contract.id, claim_number="TEST-PENDING", period_start=date.today(), period_end=date.today(), work_description="Pending work", amount=500, status="Pending certification", submitted_by_id=actor.id),
                            BillingEntry(project_id=project.id, application_number="TEST-FUTURE", description="Future work", submitted_date=date.today() + timedelta(days=1), amount=9999, status="Submitted"),
                        ])
                        await db.commit()
                        async def report_now():
                            response = await client.get("/api/v1/company-cashbook")
                            assert response.status_code == 200, response.text
                            return response.json()
                        report = await report_now()
                        auto = report["projects"][0]["calculated"]
                        assert auto["amount"] == "650.14"  # 1000.25 - 200.02 - 100.04 - 50.05
                        actor.global_permissions = {"overview": {"access": "allow", "write": {"mode": "all"}}}
                        await db.commit()
                        overview = await client.get(f"/api/v1/projects/{project_id}/dashboard")
                        assert overview.status_code == 200, overview.text
                        assert Decimal(overview.json()["approved_contract_value"]) - Decimal(overview.json()["actual_cost"]) == Decimal(auto["amount"])
                        receipt.unit_cost = 0
                        await db.commit()
                        assert (await report_now())["projects"][0]["calculated"]["amount"] == auto["amount"], "Reuse Overview; inventory valuation must not introduce another formula"
                        assert report["project_totals"]["reported"] == 0
                        approval = {"request_id": str(uuid4()), "project_id": project_id, "as_of": str(date.today()),
                                    "fingerprint": auto["fingerprint"], "note": "Reviewed source entries"}
                        await post("/result-approvals", {**approval, "as_of": str(date.today() - timedelta(days=1))}, 422)
                        app.dependency_overrides.pop(require_csrf)
                        await post("/result-approvals", approval, 403)
                        app.dependency_overrides[require_csrf] = lambda: None
                        result = await post("/result-approvals", approval)
                        exact_approval = await client.get(f"/api/v1/company-cashbook/records/{result['id']}")
                        assert exact_approval.status_code == 200, exact_approval.text
                        assert exact_approval.json()["type"] == "approval"
                        assert exact_approval.json()["record"]["snapshot"]["amount"] == "650.14"
                        assert exact_approval.json()["record"]["approved_by"] == actor.name
                        assert await post("/result-approvals", approval) == result  # Idempotent retry.
                        await post("/result-approvals", {**approval, "request_id": str(uuid4())}, 409)
                        report = await report_now()
                        assert report["project_totals"]["net"] == "650.14"
                        assert report["projects"][0]["pending_approval"] is False
                        client_contract.original_value = Decimal("200.00")
                        await db.commit()
                        report = await report_now()
                        assert report["projects"][0]["calculated"]["amount"] == "-150.11"
                        assert report["projects"][0]["pending_approval"] is True
                        assert report["project_totals"]["net"] == "650.14"  # Actual remains last approved.
                        await post("/result-approvals", {**approval, "request_id": str(uuid4())}, 409)  # Stale review.
                        report = await report_now()
                        await post("/result-approvals", {**approval, "request_id": str(uuid4()), "fingerprint": report["projects"][0]["calculated"]["fingerprint"]})
                        report = (await client.get("/api/v1/company-cashbook")).json()
                        assert report["project_totals"]["net"] == "-150.11"
                        assert report["project_totals"]["losses"] == "150.11"
                        assert len(report["approvals"]) == 2  # Same-day reapproval preserves both snapshots.
                        assert report["approvals"][1]["amount"] == "650.14"
                        assert report["summary"]["closing_balance"] == "899.17"  # Results never move cash.
                        historical = (await client.get(f"/api/v1/company-cashbook?end={date.today() - timedelta(days=1)}")).json()
                        assert historical["project_totals"]["reported"] == 0
                        await post(f"/entries/{recorded['id']}/void", {"reason": "Duplicate capital receipt"}, 200)
                        voided_entry = (await client.get(f"/api/v1/company-cashbook/records/{recorded['id']}")).json()["record"]
                        assert voided_entry["id"] == recorded["id"] and voided_entry["voided_at"]
                        assert voided_entry["void_reason"] == "Duplicate capital receipt"
                        await post(f"/entries/{recorded['id']}/void", {"reason": "Repeat void request"}, 409)
                        exported = await post("/export", {}, 200)
                        assert len(exported["items"]) == 104
                        assert exported["summary"]["closing_balance"] == "-101.08"
                        history = (await client.get("/api/v1/company-cashbook/history")).json()
                        assert history["total"] == 111
                        assert history["page_size"] == 10 and len(history["items"]) == 10
                        for tab, action in (
                            ("cash", "visit_cash_transactions"), ("borrowings", "visit_borrowings"),
                            ("results", "visit_project_profit_loss"), ("capital", "visit_owner_capital"),
                            ("history", "visit_cashbook_history"), ("audit-log", "visit_company_audit_log"),
                        ):
                            assert (await client.post("/api/v1/company-cashbook/activities", json={"page": tab})).status_code == 204
                            visits = (await client.get("/api/v1/company-cashbook/history", params={"search": action})).json()
                            assert visits["total"] == 1
                            assert visits["items"][0]["actor"] == actor.username
                            assert visits["items"][0]["details"]["activity"] == "visit"
                        for source in ("history", "audit-log"):
                            url = f"/api/v1/company-cashbook/{source}"
                            for size in (10, 20, 50, 100):
                                first = (await client.get(url, params={"page_size": size})).json()
                                second = (await client.get(url, params={"page_size": size, "page": 2})).json()
                                assert first["page_size"] == size and len(first["items"]) == size
                                assert not {item["id"] for item in first["items"]} & {item["id"] for item in second["items"]}
                            assert (await client.get(url, params={"page_size": 5})).status_code == 422
                            assert (await client.get(url, params={"page_size": 101})).status_code == 422
                            assert (await client.get(url, params={"start_time": "2026-01-01T00:00:00"})).status_code == 422
                            assert (await client.get(url, params={"start_time": "2026-02-01T00:00:00Z", "end_time": "2026-01-01T00:00:00Z"})).status_code == 422
                            assert (await client.get(url, params={"search": "Visited Borrowings"})).json()["items"][0]["action"] == "visit_borrowings"
                            assert (await client.get(url, params={"search": actor.name})).json()["total"] > 100
                            assert (await client.get(url, params={"search": "unmatched-unique-search"})).json()["total"] == 0
                            assert (await client.get(url, params={"start_time": "2099-01-01T00:00:00Z"})).json()["total"] == 0
                            event_time = first["items"][0]["occurred_at"]
                            bounded = (await client.get(url, params={"start_time": event_time, "end_time": event_time})).json()
                            assert first["items"][0]["id"] in {item["id"] for item in bounded["items"]}
                            scoped_export = await client.post(url + "/export", params={"search": "visit_owner_capital"})
                            assert scoped_export.status_code == 200, scoped_export.text
                            assert any(item["action"] == "visit_owner_capital" for item in scoped_export.json()["items"])
                            exported_history = await client.post(url + "/export")
                            assert exported_history.status_code == 200, exported_history.text
                            assert len(exported_history.json()["items"]) == exported_history.json()["total"] > 100
                        app.dependency_overrides.pop(require_csrf)
                        assert (await client.post("/api/v1/company-cashbook/activities", json={"page": "cash"})).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/audit-log/export")).status_code == 403
                        assert (await client.post(activity_export_url, params={"source": "audit-log"})).status_code == 403
                        assert (await client.post(activity_export_url, params={"source": "history"})).status_code == 403
                        app.dependency_overrides[require_csrf] = lambda: None
                        assert (await client.post("/api/v1/company-cashbook/activities", json={"page": "invalid"})).status_code == 422
                        custom_category = {"option_type": "category", "kind": "company_expense", "name": "Insurance", "first_type": "Annual premium", "direction": "out"}
                        created = (await post("/options", custom_category))["items"]
                        for option in created:
                            exact_option = await client.get(f"/api/v1/company-cashbook/records/{option['id']}")
                            assert exact_option.status_code == 200, exact_option.text
                            assert exact_option.json() == {"type": "option", "record": option}
                        assert [(item["option_type"], item["parent"], item["name"]) for item in created] == [("category", "", "Insurance"), ("type", "Insurance", "Annual premium")]
                        custom_type = {"option_type": "type", "kind": "company_expense", "parent": "Insurance", "name": "Vehicle insurance", "direction": "out"}
                        await post("/options", custom_type)
                        await post("/options", {"option_type": "type", "kind": "company_expense", "name": "Office cleaning", "direction": "out"})
                        await post("/options", {**custom_type, "name": " VEHICLE INSURANCE "}, 409)
                        await post("/options", {**custom_category, "name": "company spending"}, 409)
                        await post("/options", {**custom_category, "name": " INSURANCE "}, 409)
                        await post("/options", {"option_type": "type", "kind": "company_expense", "name": "Furniture", "direction": "out"}, 409)
                        await post("/options", {**custom_type, "kind": "owner_capital"}, 422)
                        custom_payload = {**payload, "request_id": str(uuid4()), "amount": "12.34",
                                          "custom_category": "Insurance", "category": "Vehicle insurance"}
                        await post("/entries", {**custom_payload, "kind": "other_receipt"}, 422)
                        await post("/entries", {**custom_payload, "category": "Furniture"}, 422)
                        await post("/entries", {**custom_payload, "custom_category": None}, 422)
                        await post("/entries", custom_payload)
                        custom_report = (await client.get("/api/v1/company-cashbook?search=Vehicle%20insurance")).json()
                        assert len(custom_report["options"]) == 4
                        assert custom_report["total"] == 1
                        assert custom_report["items"][0]["custom_category"] == "Insurance"
                        assert custom_report["items"][0]["category"] == "Vehicle insurance"
                        assert (await client.get("/api/v1/company-cashbook?custom_category=Insurance")).json()["total"] == 1
                        assert (await client.get("/api/v1/company-cashbook?kind=company_expense&search=Vehicle%20insurance")).json()["total"] == 0
                        assert custom_report["items"][0]["direction"] == "out"
                        assert custom_report["summary"]["closing_balance"] == "-113.42"
                        assert custom_report["project_totals"]["net"] == "-150.11"
                        for kind, name in [("paid", "Paid to Shop"), ("salary", "Salary to Driver")]:
                            await post("/entries", {**payload, "request_id": str(uuid4()), "kind": kind, "category": name, "amount": "10.00"})
                        await post("/options", {"option_type": "type", "kind": "paid", "name": "Shop refund", "direction": "in"})
                        refund_payload = {**payload, "request_id": str(uuid4()), "kind": "paid", "category": "Shop refund", "amount": "3.25"}
                        await post("/entries", {**refund_payload, "direction": "out"}, 422)
                        refund = await post("/entries", refund_payload)
                        incoming_report = (await client.get("/api/v1/company-cashbook?kind=paid&direction=in")).json()
                        assert incoming_report["total"] == 1
                        assert incoming_report["items"][0]["direction"] == "in"
                        assert incoming_report["filtered_in"] == "3.25"
                        assert incoming_report["filtered_out"] == "0.00"
                        assert incoming_report["summary"]["closing_balance"] == "-130.17"
                        assert incoming_report["summary"]["kind_totals"]["paid"] == "6.75"
                        assert incoming_report["summary"]["kind_totals"]["salary"] == "10.00"
                        outgoing_report = (await client.get("/api/v1/company-cashbook?kind=paid&direction=out")).json()
                        assert outgoing_report["total"] == 1
                        assert outgoing_report["filtered_out"] == "10.00"
                        exported_refund = (await client.post("/api/v1/company-cashbook/export?kind=paid&direction=in")).json()
                        assert exported_refund["items"] == incoming_report["items"]
                        await post(f"/entries/{refund['id']}/void", {"reason": "Refund entered twice"}, 200)
                        after_void = (await client.get("/api/v1/company-cashbook?kind=paid&direction=in")).json()
                        assert after_void["total"] == 0
                        assert after_void["summary"]["closing_balance"] == "-133.42"
                        history = (await client.get("/api/v1/company-cashbook/history")).json()
                        history_items = list(history["items"])
                        for page in range(2, (history["total"] + 9) // 10 + 1):
                            history_items.extend((await client.get(f"/api/v1/company-cashbook/history?page={page}")).json()["items"])
                        recorded_refund = next(item for item in history_items if item["record_id"] == refund["id"] and item["details"].get("after"))
                        assert recorded_refund["details"]["after"]["direction"] == "in"
                        loan = {"request_id": str(uuid4()), "action": "loan", "transaction_date": date.today().isoformat(), "lender": "City Bank",
                                "principal": "500.00", "description": "Working capital loan", "account": "Company bank", "payment_mode": "Bank transfer"}
                        await post("/entries", {**payload, "request_id": str(uuid4()), "kind": "borrowings", "category": "Loan received"}, 422)
                        await post("/borrowings", {**loan, "action": "repayment", "request_id": str(uuid4())}, 422)
                        assert len((await post("/borrowings", loan))["ids"]) == 1
                        await post("/borrowings", loan, 409)
                        repayment = {**loan, "request_id": str(uuid4()), "action": "repayment", "lender": "city bank", "principal": "200.00", "interest": "12.50", "description": "EMI 1"}
                        await post("/borrowings", {**repayment, "request_id": str(uuid4()), "principal": "500.01"}, 422)
                        repaid = await post("/borrowings", repayment)
                        assert len(repaid["ids"]) == 2
                        await post("/borrowings", repayment, 409)
                        loan_report = (await client.get("/api/v1/company-cashbook?kind=borrowings")).json()
                        assert loan_report["total"] == 3
                        assert {item["party"] for item in loan_report["items"]} == {"City Bank"}
                        assert loan_report["lifetime"]["borrowings"] == [{"lender": "City Bank", "borrowed": "500.00", "repaid": "200.00", "interest": "12.50", "outstanding": "300.00"}]
                        assert loan_report["summary"]["closing_balance"] == "154.08"
                        assert {"category": "Loan interest", "amount": "12.50"} in loan_report["summary"]["expense_categories"]
                        interest_id = next(item["id"] for item in loan_report["items"] if item["category"] == "Loan interest")
                        await post(f"/entries/{interest_id}/void", {"reason": "Interest entered incorrectly"}, 200)
                        after_interest_void = (await client.get("/api/v1/company-cashbook")).json()
                        assert after_interest_void["lifetime"]["borrowings_interest"] == "0.00"
                        assert after_interest_void["lifetime"]["borrowings_outstanding"] == "300.00"
                        lender_history = (await client.get("/api/v1/company-cashbook", params={
                            "kind": "borrowings", "lender": "City Bank", "status": "all", "page_size": 2,
                        })).json()
                        assert lender_history["total"] == 3
                        assert len(lender_history["items"]) == 2
                        lender_page_two = (await client.get("/api/v1/company-cashbook", params={
                            "kind": "borrowings", "lender": "City Bank", "status": "all", "page_size": 2, "page": 2,
                        })).json()
                        lender_entries = lender_history["items"] + lender_page_two["items"]
                        assert {item["id"] for item in lender_entries} == {item["id"] for item in loan_report["items"]}
                        assert next(item for item in lender_entries if item["id"] == interest_id)["voided_at"]
                        for not_a_lender in ["City", "Working capital loan", "Company bank"]:
                            other_history = (await client.get("/api/v1/company-cashbook", params={"lender": not_a_lender})).json()
                            assert other_history["total"] == 0
                        posted_history = (await client.get("/api/v1/company-cashbook", params={"lender": "City Bank"})).json()
                        assert posted_history["total"] == 2
                        loan_page = (await client.get("/api/v1/company-cashbook/history")).json()
                        loan_history = list(loan_page["items"])
                        for page in range(2, (loan_page["total"] + 9) // 10 + 1):
                            loan_history.extend((await client.get(f"/api/v1/company-cashbook/history?page={page}")).json()["items"])
                        assert sum(item["action"] == "cashbook_borrowing_recorded" for item in loan_history) == 3
                        await post("/borrowings", {**repayment, "request_id": str(uuid4()), "principal": "300.00", "interest": "0"})
                        for principal, interest in [("1.00", "0"), ("0", "1.00")]:
                            settled = await post("/borrowings", {**repayment, "request_id": str(uuid4()), "principal": principal, "interest": interest}, 422)
                            assert "settled" in settled["detail"]
                        await post("/borrowings", {**loan, "request_id": str(uuid4()), "principal": "10.00"})
                        await post("/borrowings", {**repayment, "request_id": str(uuid4()), "principal": "1.00", "interest": "0"})
                        actor.global_access = False
                        actor.cashbook_permissions = {"access": "allow", "write": {"mode": "all"}}
                        await db.commit()
                        await post("/options", {**custom_category, "name": "Unauthorized"}, 403)
                        await post("/entries", {**custom_payload, "request_id": str(uuid4())})
                        actor.cashbook_permissions = {"access": "allow", "read": {"export_report": False}, "write": {"mode": "partial", "actions": {}}}
                        await db.commit()
                        assert (await client.get(f"/api/v1/company-cashbook/records/{recorded['id']}")).status_code == 200
                        assert (await client.get("/api/v1/company-cashbook")).status_code == 200
                        assert (await client.post("/api/v1/company-cashbook/export")).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/entries", json=payload)).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/borrowings", json={**loan, "request_id": str(uuid4())})).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/result-approvals", json=approval)).status_code == 403
                        assert (await client.get("/api/v1/company-cashbook/audit-log")).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/history/export")).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/audit-log/export")).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/activities", json={"page": "cash"})).status_code == 204
                        assert (await client.post("/api/v1/company-cashbook/activities", json={"page": "audit-log"})).status_code == 403
                        legacy_result = CompanyProjectResult(
                            request_id=uuid4(), project_id=project.id, as_of=date.today(),
                            amount=Decimal("125.50"), basis="Legacy confirmed result", recorded_by_id=actor.id,
                        )
                        db.add(legacy_result)
                        await db.commit()
                        exact_result = await client.get(f"/api/v1/company-cashbook/records/{legacy_result.id}")
                        assert exact_result.status_code == 200, exact_result.text
                        assert exact_result.json()["type"] == "result"
                        assert exact_result.json()["record"]["basis"] == "Legacy confirmed result"
                        assert exact_result.json()["record"]["project_name"] == project.name
                        actor.cashbook_permissions = None
                        actor.company_audit_permissions = {"access": "allow", "read": {"export_report": False}, "write": {"mode": "partial", "actions": {}}}
                        await db.commit()
                        assert (await client.get("/api/v1/company-cashbook")).status_code == 403
                        assert (await client.get("/api/v1/company-cashbook/history")).status_code == 403
                        audit_log = await client.get("/api/v1/company-cashbook/audit-log")
                        assert audit_log.status_code == 200 and audit_log.json()["total"] > 0
                        assert (await client.post("/api/v1/company-cashbook/activities", json={"page": "cash"})).status_code == 403
                        assert (await client.post("/api/v1/company-cashbook/activities", json={"page": "audit-log"})).status_code == 204
                        assert (await client.post("/api/v1/company-cashbook/audit-log/export")).status_code == 403
                        actor.company_audit_permissions = {**actor.company_audit_permissions, "read": {"export_report": True}}
                        await db.commit()
                        assert (await client.post("/api/v1/company-cashbook/audit-log/export")).status_code == 200
                        assert (await client.post("/api/v1/company-cashbook/history/export")).status_code == 403
                        for record_id in (recorded["id"], result["id"], str(legacy_result.id), created[0]["id"], str(uuid4())):
                            denied = await client.get(f"/api/v1/company-cashbook/records/{record_id}")
                            assert denied.status_code == 403
                            assert "Company Cashbook read permission" in denied.json()["detail"]
                        assert (await client.post(activity_export_url, params={"source": "audit-log"})).status_code == 403
                        visit_event = await db.scalar(select(AuditEvent).where(AuditEvent.action == "visit_company_audit_log", AuditEvent.actor_id == actor.id))
                        assert (await client.post(f"/api/v1/company-cashbook/activities/{visit_event.id}/export", params={"source": "audit-log"})).status_code == 204
            finally:
                app.dependency_overrides.clear()
                await transaction.rollback()
    finally:
        await engine.dispose()
