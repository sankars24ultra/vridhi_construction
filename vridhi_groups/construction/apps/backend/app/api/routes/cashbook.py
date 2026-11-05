"""Company cash and approvals of existing Project Overview projections."""
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AuditEvent, CompanyCashEntry, CompanyCashOption, CompanyProjectResult, Project, ProjectResultApproval, User
from app.security import current_user, require_cashbook, require_company_audit, require_csrf, require_writable_project
from app.services.common import add_audit, money
from app.api.routes.projects import dashboard

router = APIRouter(prefix="/api/v1/company-cashbook", tags=["Company Cashbook"])
INCOMING = {"owner_capital", "project_received", "other_receipt", "opening_in", "borrowings"}
OPENING = {"opening_in", "opening_out"}
SPENDING = {"company_expense", "paid", "salary"}
LOAN_RECEIVED = "Loan received"
LOAN_PRINCIPAL_REPAYMENT = "Loan repayment – principal"
LOAN_INTEREST = "Loan interest"
KINDS = {
    "owner_capital": ["Capital contribution"],
    "owner_withdrawal": ["Owner withdrawal"],
    "company_expense": ["Company purchases", "Company labor", "Furniture", "Plumbing", "Building maintenance", "Rent", "Utilities", "Transport", "Miscellaneous"],
    "project_received": ["Project transfer"],
    "project_funding": ["Project transfer"],
    "other_receipt": ["Other company receipt"],
    "opening_in": ["Opening balance"],
    "opening_out": ["Opening balance"],
    "paid": ["Paid to Pending", "Paid to Shop", "Paid to Electricity", "Paid to Wifi"],
    "salary": ["Salary to Contractors", "Salary to Manager", "Salary to Security", "Salary to Driver"],
    "borrowings": [LOAN_RECEIVED, LOAN_PRINCIPAL_REPAYMENT, LOAN_INTEREST],
}
DEFAULT_ACCOUNTS = {"Cash": "Cash", "Other": "Others"}
Kind = Literal["owner_capital", "owner_withdrawal", "company_expense", "project_received", "project_funding", "other_receipt", "opening_in", "opening_out", "paid", "salary", "borrowings"]


class CashEntryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    request_id: UUID
    transaction_date: date
    kind: Kind
    # Custom top-level category; None means the built-in category named by kind.
    custom_category: str | None = Field(default=None, min_length=1, max_length=80)
    # Second-level transaction type (stored in the historical category column).
    category: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    party: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=500)
    account: str = Field(default="", max_length=100)
    payment_mode: Literal["Bank transfer", "Cash", "UPI", "Cheque", "Other"]
    reference: str | None = Field(default=None, max_length=100)
    project_id: UUID | None = None

    @model_validator(mode="after")
    def valid_entry(self):
        if self.transaction_date > date.today():
            raise ValueError("Future cash transactions are not allowed")
        if (self.kind in {"project_received", "project_funding"}) != bool(self.project_id):
            raise ValueError("A linked project is required only for project cash transfers")
        if not self.account:
            if self.payment_mode not in DEFAULT_ACCOUNTS:
                raise ValueError("Company account is required for bank transfer, UPI and cheque payments")
            self.account = DEFAULT_ACCOUNTS[self.payment_mode]
        return self


BUILTIN_CATEGORIES = {
    "owner_capital": "Owner capital", "owner_withdrawal": "Owner withdrawal", "company_expense": "Company spending",
    "project_received": "Project cash received", "project_funding": "Project funding", "other_receipt": "Other receipt",
    "opening_in": "Starting balance (+)", "opening_out": "Starting balance (−)",
    "paid": "Paid", "salary": "Salary",
    "borrowings": "Borrowings",
}


class CashOptionCreate(BaseModel):
    """A category groups transaction types; each type defines its cash direction."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    option_type: Literal["category", "type"]
    kind: Kind
    parent: str = Field(default="", max_length=80)
    name: str = Field(min_length=1, max_length=80)
    first_type: str | None = Field(default=None, min_length=1, max_length=80)
    direction: Literal["in", "out"]

    @model_validator(mode="after")
    def valid_option(self):
        if self.option_type == "category":
            if self.parent or not self.first_type:
                raise ValueError("A new category needs its first transaction type")
        elif self.first_type is not None:
            raise ValueError("Only a new category can include a first transaction type")
        return self


def option_dto(option: CompanyCashOption) -> dict:
    return {"id": str(option.id), "option_type": option.option_type, "kind": option.kind, "parent": option.parent, "name": option.name, "direction": option.direction}


@router.post("/options", status_code=201, dependencies=[Depends(require_csrf)])
async def create_option(payload: CashOptionCreate, user: User = Depends(require_cashbook("write")), db: AsyncSession = Depends(get_db)):
    if not user.global_access:
        raise HTTPException(status_code=403, detail="Only cashbook administrators can add categories and transaction types")
    if payload.kind == "borrowings":
        raise HTTPException(status_code=422, detail="Borrowing categories and transaction types are fixed so lender balances remain accurate")
    existing = list((await db.scalars(select(CompanyCashOption))).all())
    categories = [option for option in existing if option.option_type == "category"]
    if payload.option_type == "category":
        if payload.name.casefold() in {name.casefold() for name in [*BUILTIN_CATEGORIES.values(), *(option.name for option in categories)]}:
            raise HTTPException(status_code=409, detail="This category already exists")
        types = [(payload.name, payload.first_type)]
    else:
        if payload.parent and not any(option.name == payload.parent and option.kind == payload.kind for option in categories):
            raise HTTPException(status_code=422, detail="Select an existing category")
        built_in = [] if payload.parent else KINDS[payload.kind]
        siblings = [option.name for option in existing if option.option_type == "type" and option.kind == payload.kind and option.parent == payload.parent]
        if payload.name.casefold() in {name.casefold() for name in [*built_in, *siblings]}:
            raise HTTPException(status_code=409, detail="This transaction type already exists in the selected category")
        types = [(payload.parent, payload.name)]
    created = []
    if payload.option_type == "category":
        created.append(CompanyCashOption(id=uuid4(), option_type="category", kind=payload.kind, parent="", name=payload.name, normalized_name=payload.name.casefold(), created_by_id=user.id))
    created += [CompanyCashOption(id=uuid4(), option_type="type", kind=payload.kind, parent=parent, name=name, normalized_name=name.casefold(), direction=payload.direction, created_by_id=user.id) for parent, name in types]
    db.add_all(created)
    await add_audit(db, user, "cashbook_option_created", "CompanyCashbook", created[0].id, {"after": payload.model_dump()})
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This option already exists. Refresh and select it.") from error
    return {"items": [option_dto(option) for option in created]}


async def validate_entry_options(db: AsyncSession, payload: CashEntryCreate):
    if payload.kind == "borrowings":
        raise HTTPException(status_code=422, detail="Record loans, repayments and interest from the Borrowings tab")
    options = list((await db.scalars(select(CompanyCashOption).where(CompanyCashOption.kind == payload.kind))).all())
    parent = payload.custom_category or ""
    if parent and not any(option.option_type == "category" and option.name == parent for option in options):
        raise HTTPException(status_code=422, detail="Select an existing category")
    built_in = [] if parent else KINDS[payload.kind]
    if payload.category not in built_in and not any(option.option_type == "type" and option.parent == parent and option.name == payload.category for option in options):
        raise HTTPException(status_code=422, detail="Select a transaction type belonging to this category")
    if payload.category in built_in:
        return "in" if payload.kind in INCOMING else "out"
    return next(option.direction for option in options if option.option_type == "type" and option.parent == parent and option.name == payload.category)


class ProjectResultCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    request_id: UUID
    project_id: UUID
    as_of: date
    amount: Decimal = Field(max_digits=18, decimal_places=2)
    basis: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def valid_date(self):
        if self.as_of > date.today():
            raise ValueError("A project result cannot be dated in the future")
        return self


class VoidCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    reason: str = Field(min_length=5, max_length=500)


class ResultApprovalCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    request_id: UUID
    project_id: UUID
    as_of: date
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    note: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def valid_date(self):
        if self.as_of != date.today():
            raise ValueError("Approve the current Overview projection using today's date")
        return self


def signed(entry: CompanyCashEntry) -> Decimal:
    return entry.amount if entry.direction == "in" else -entry.amount


def category_amount(entry: CompanyCashEntry) -> Decimal:
    # Opposite-direction types offset their category's normal movement.
    return signed(entry) if entry.kind in INCOMING else -signed(entry)


def is_interest(entry: CompanyCashEntry) -> bool:
    return entry.kind == "borrowings" and entry.category == LOAN_INTEREST


def cash_summary(entries: list[CompanyCashEntry], start: date | None, end: date) -> dict:
    active = [entry for entry in entries if entry.voided_at is None and entry.transaction_date <= end]
    period = [entry for entry in active if start is None or entry.transaction_date >= start]
    movement = [entry for entry in period if entry.kind not in OPENING]
    prior = sum((signed(entry) for entry in active if start and entry.transaction_date < start), Decimal(0))
    introduced = sum((signed(entry) for entry in period if entry.kind in OPENING), Decimal(0))
    inbound = sum((entry.amount for entry in movement if entry.direction == "in"), Decimal(0))
    outbound = sum((entry.amount for entry in movement if entry.direction == "out"), Decimal(0))
    expenses: dict[str, Decimal] = {}
    accounts: dict[str, Decimal] = {}
    owners: dict[str, dict[str, Decimal]] = {}
    borrowings: dict[str, dict[str, Decimal]] = {}
    for entry in active:
        accounts[entry.account] = accounts.get(entry.account, Decimal(0)) + signed(entry)
    for entry in period:
        if entry.kind in SPENDING or is_interest(entry):
            expenses[entry.category] = expenses.get(entry.category, Decimal(0)) + (-signed(entry) if is_interest(entry) else category_amount(entry))
        if entry.kind in {"owner_capital", "owner_withdrawal"}:
            owner = owners.setdefault(entry.party, {"capital": Decimal(0), "withdrawals": Decimal(0)})
            owner["capital" if entry.kind == "owner_capital" else "withdrawals"] += category_amount(entry)
    for entry in active:
        if entry.kind == "borrowings":
            lender = borrowings.setdefault(entry.party, {"borrowed": Decimal(0), "repaid": Decimal(0), "interest": Decimal(0)})
            lender["borrowed" if entry.category == LOAN_RECEIVED else "interest" if entry.category == LOAN_INTEREST else "repaid"] += entry.amount
    # Interest is spending, so the Borrowings category total is net principal movement only.
    kind_totals = {kind: money(sum((category_amount(entry) for entry in movement if entry.kind == kind and not is_interest(entry)), Decimal(0))) for kind in KINDS if kind not in OPENING}
    borrowing_rows = [
        {"lender": lender, "borrowed": money(values["borrowed"]), "repaid": money(values["repaid"]), "interest": money(values["interest"]), "outstanding": money(values["borrowed"] - values["repaid"])}
        for lender, values in sorted(borrowings.items(), key=lambda item: item[0].casefold())
    ]
    return {
        "opening_balance": money(prior + introduced), "opening_entries": money(introduced),
        "money_in": money(inbound), "money_out": money(outbound),
        "closing_balance": money(prior + introduced + inbound - outbound),
        "net_movement": money(inbound - outbound),
        "company_spending": money(sum(expenses.values(), Decimal(0))),
        "kind_totals": kind_totals,
        "borrowings": borrowing_rows,
        "borrowings_outstanding": money(sum((values["borrowed"] - values["repaid"] for values in borrowings.values()), Decimal(0))),
        "borrowings_borrowed": money(sum((values["borrowed"] for values in borrowings.values()), Decimal(0))),
        "borrowings_repaid": money(sum((values["repaid"] for values in borrowings.values()), Decimal(0))),
        "borrowings_interest": money(sum((values["interest"] for values in borrowings.values()), Decimal(0))),
        "expense_categories": [{"category": key, "amount": money(value)} for key, value in sorted(expenses.items(), key=lambda item: -item[1])],
        "accounts": [{"account": key, "balance": money(value)} for key, value in sorted(accounts.items())],
        "owners": [{"owner": key, "capital": money(value["capital"]), "withdrawals": money(value["withdrawals"]), "net": money(value["capital"] - value["withdrawals"])} for key, value in sorted(owners.items())],
        "count": len(period),
    }


def entry_dto(entry: CompanyCashEntry, names: dict, users: dict) -> dict:
    return {
        "id": str(entry.id), "reference_number": f"CC-{str(entry.id)[:8].upper()}",
        "transaction_date": entry.transaction_date.isoformat(), "kind": entry.kind,
        "category": entry.category, "custom_category": entry.custom_category, "amount": money(entry.amount),
        "direction": entry.direction, "party": entry.party,
        "description": entry.description, "account": entry.account,
        "payment_mode": entry.payment_mode, "reference": entry.reference,
        "project_id": str(entry.project_id) if entry.project_id else None,
        "project_name": names.get(entry.project_id),
        "recorded_by": users.get(entry.recorded_by_id, "Unknown"),
        "recorded_at": entry.recorded_at.isoformat(),
        "voided_at": entry.voided_at.isoformat() if entry.voided_at else None,
        "voided_by": users.get(entry.voided_by_id), "void_reason": entry.void_reason,
    }


def result_dto(result: CompanyProjectResult, names: dict, users: dict) -> dict:
    return {
        "id": str(result.id), "project_id": str(result.project_id),
        "project_name": names.get(result.project_id), "as_of": result.as_of.isoformat(),
        "amount": money(result.amount), "basis": result.basis,
        "recorded_by": users.get(result.recorded_by_id, "Unknown"),
        "recorded_at": result.recorded_at.isoformat(),
        "voided_at": result.voided_at.isoformat() if result.voided_at else None,
        "void_reason": result.void_reason,
    }


def approval_dto(record: ProjectResultApproval, names: dict, users: dict) -> dict:
    return {
        "id": str(record.id), "project_id": str(record.project_id),
        "project_name": names.get(record.project_id), "as_of": record.as_of.isoformat(),
        "amount": money(record.amount), "snapshot": record.snapshot, "note": record.note,
        "approved_by": users.get(record.approved_by_id, "Unknown"),
        "approved_at": record.approved_at.isoformat(),
    }


async def overview_projection(db: AsyncSession, project: Project, user: User) -> dict:
    # Reuse the existing Overview report; do not introduce a second cost formula.
    report = await dashboard(project=project, _=user, db=db)
    snapshot = {
        "contract_value": report["approved_contract_value"], "recorded_cost": report["actual_cost"],
        "materials": next(item["amount"] for item in report["cost_breakdown"] if item["category"] == "Materials"),
        "wages": report["labor_cost_breakdown"]["direct_workers"],
        "contractors": report["labor_cost_breakdown"]["contract_claims"],
        "formula_version": "overview-projected-profit-v1",
    }
    snapshot["amount"] = money(Decimal(snapshot["contract_value"]) - Decimal(snapshot["recorded_cost"]))
    snapshot["fingerprint"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return snapshot


@router.get("")
async def cashbook(start: date | None = None, end: date | None = None, search: str = Query("", max_length=200), kind: Kind | None = None, direction: Literal["in", "out"] | None = None, status: Literal["posted", "voided", "all"] = "posted", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(require_cashbook()), db: AsyncSession = Depends(get_db), category: str = Query("", max_length=80), custom_category: str = Query("", max_length=80), lender: str = Query("", max_length=160)) -> dict:
    end = end or date.today()
    if start and start > end or end > date.today():
        raise HTTPException(status_code=422, detail="Choose a valid date range ending no later than today")
    projects = (await db.scalars(select(Project).where(Project.currency == "INR").order_by(Project.name))).all()
    names = {project.id: project.name for project in projects}
    users = dict((await db.execute(select(User.id, User.name))).all())
    entries = list((await db.scalars(select(CompanyCashEntry).where(CompanyCashEntry.transaction_date <= end).order_by(CompanyCashEntry.transaction_date.desc(), CompanyCashEntry.recorded_at.desc(), CompanyCashEntry.id.desc()))).all())
    summary = cash_summary(entries, start, end)
    lifetime = cash_summary(entries, None, end)
    items = []
    term = search.casefold().strip()
    for entry in entries:
        if start and entry.transaction_date < start:
            continue
        if category and entry.category != category:
            continue
        if lender and (entry.kind != "borrowings" or entry.party != lender):
            continue
        if custom_category and entry.custom_category != custom_category or not custom_category and kind and (entry.kind != kind or entry.custom_category):
            continue
        if status != "all" and (entry.voided_at is not None) != (status == "voided"):
            continue
        if direction and entry.direction != direction:
            continue
        searchable = " ".join([str(entry.id), f"CC-{str(entry.id)[:8]}", entry.party, entry.description, entry.category, entry.custom_category or "", entry.reference or "", entry.account, names.get(entry.project_id, "")])
        if term not in searchable.casefold():
            continue
        items.append(entry)
    all_results = list((await db.scalars(select(CompanyProjectResult).where(CompanyProjectResult.as_of <= end).order_by(CompanyProjectResult.as_of.desc(), CompanyProjectResult.recorded_at.desc()))).all())
    approvals = list((await db.scalars(select(ProjectResultApproval).where(
        ProjectResultApproval.as_of <= end, ProjectResultApproval.project_id.in_(names)
    ).order_by(ProjectResultApproval.as_of.desc(), ProjectResultApproval.approved_at.desc(), ProjectResultApproval.id.desc()))).all())
    latest = {}
    for approval in approvals:
        latest.setdefault(approval.project_id, approval)
    project_rows = []
    for project in projects:
        result = latest.get(project.id)
        auto = await overview_projection(db, project, user)
        transfers = [entry for entry in entries if entry.voided_at is None and entry.project_id == project.id]
        project_rows.append({
            "id": str(project.id), "name": project.name, "status": project.status,
            "archived": project.archived_at is not None,
            "calculated": auto,
            "approval": approval_dto(result, names, users) if result else None,
            "pending_approval": result is None or result.snapshot.get("fingerprint") != auto["fingerprint"],
            "cash_received": money(sum((category_amount(entry) for entry in transfers if entry.kind == "project_received"), Decimal(0))),
            "cash_sent": money(sum((category_amount(entry) for entry in transfers if entry.kind == "project_funding"), Decimal(0))),
        })
    profits = sum((result.amount for result in latest.values() if result.amount > 0), Decimal(0))
    losses = -sum((result.amount for result in latest.values() if result.amount < 0), Decimal(0))
    return {
        "currency": "INR", "start": start.isoformat() if start else None, "end": end.isoformat(),
        "options": [option_dto(option) for option in (await db.scalars(select(CompanyCashOption).order_by(CompanyCashOption.name))).all()],
        "summary": summary, "lifetime": lifetime, "items": [entry_dto(entry, names, users) for entry in items[(page - 1) * page_size:page * page_size]],
        "page": page, "page_size": page_size, "total": len(items),
        "filtered_in": money(sum((entry.amount for entry in items if entry.voided_at is None and entry.direction == "in"), Decimal(0))),
        "filtered_out": money(sum((entry.amount for entry in items if entry.voided_at is None and entry.direction == "out"), Decimal(0))),
        "projects": project_rows, "results": [result_dto(result, names, users) for result in all_results],
        "approvals": [approval_dto(record, names, users) for record in approvals],
        "calculation_as_of": date.today().isoformat(),
        "project_totals": {"profits": money(profits), "losses": money(losses), "net": money(profits - losses), "reported": len(latest), "unreported": len(projects) - len(latest)},
    }


async def check_project(db: AsyncSession, project_id: UUID | None):
    if project_id:
        project = await require_writable_project(db, project_id)
        if project is None or project.currency != "INR":
            raise HTTPException(status_code=422, detail="Select an existing INR project")
        await require_writable_project(db, project.id)


async def commit_record(db: AsyncSession):
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate submission or an active result already exists for that project/date. Refresh before retrying; void an incorrect result before replacing it.") from error


@router.post("/entries", status_code=201, dependencies=[Depends(require_csrf)])
async def create_entry(payload: CashEntryCreate, user: User = Depends(require_cashbook("write")), db: AsyncSession = Depends(get_db)):
    direction = await validate_entry_options(db, payload)
    await check_project(db, payload.project_id)
    entry = CompanyCashEntry(id=uuid4(), recorded_by_id=user.id, direction=direction, **payload.model_dump())
    db.add(entry)
    await add_audit(db, user, "cashbook_entry_recorded", "CompanyCashbook", entry.id, {"after": {**payload.model_dump(mode="json"), "direction": direction}})
    await commit_record(db)
    return {"id": str(entry.id)}


class BorrowingCreate(BaseModel):
    """A loan receipt, or a repayment split into principal and interest."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    request_id: UUID
    action: Literal["loan", "repayment"]
    transaction_date: date
    lender: str = Field(min_length=1, max_length=160)
    principal: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    interest: Decimal = Field(default=Decimal(0), ge=0, max_digits=18, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    account: str = Field(default="", max_length=100)
    payment_mode: Literal["Bank transfer", "Cash", "UPI", "Cheque", "Other"]
    reference: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def valid_borrowing(self):
        if self.transaction_date > date.today():
            raise ValueError("Future cash transactions are not allowed")
        if self.action == "loan" and (self.principal <= 0 or self.interest):
            raise ValueError("A loan needs a principal amount and no interest")
        if self.action == "repayment" and self.principal + self.interest <= 0:
            raise ValueError("Enter a principal and/or interest amount")
        if not self.account:
            if self.payment_mode not in DEFAULT_ACCOUNTS:
                raise ValueError("Company account is required for bank transfer, UPI and cheque payments")
            self.account = DEFAULT_ACCOUNTS[self.payment_mode]
        return self


@router.post("/borrowings", status_code=201, dependencies=[Depends(require_csrf)])
async def record_borrowing(payload: BorrowingCreate, user: User = Depends(require_cashbook("write")), db: AsyncSession = Depends(get_db)):
    existing = list((await db.scalars(select(CompanyCashEntry).where(CompanyCashEntry.kind == "borrowings", CompanyCashEntry.voided_at.is_(None)))).all())
    lender = next((entry.party for entry in existing if entry.party.casefold() == payload.lender.casefold()), None)
    if payload.action == "repayment":
        if lender is None:
            raise HTTPException(status_code=422, detail="Select a lender with a recorded loan")
        balance = sum((entry.amount if entry.category == LOAN_RECEIVED else -entry.amount for entry in existing if entry.party == lender and entry.category != LOAN_INTEREST), Decimal(0))
        if balance <= 0:
            raise HTTPException(status_code=422, detail="This loan is settled; there is no outstanding principal to repay")
        if payload.principal > balance:
            raise HTTPException(status_code=422, detail=f"Principal repayment exceeds the outstanding balance of {money(balance)}")
    lender = lender or payload.lender
    common = {"transaction_date": payload.transaction_date, "kind": "borrowings", "party": lender, "description": payload.description,
              "account": payload.account, "payment_mode": payload.payment_mode, "reference": payload.reference, "recorded_by_id": user.id}
    parts = [(LOAN_RECEIVED, "in", payload.principal)] if payload.action == "loan" else [(LOAN_PRINCIPAL_REPAYMENT, "out", payload.principal), (LOAN_INTEREST, "out", payload.interest)]
    # Each part needs its own idempotency key derived from the single form submission.
    entries = [CompanyCashEntry(id=uuid4(), request_id=payload.request_id if index == 0 else uuid5(payload.request_id, category), category=category, direction=direction, amount=amount, **common)
               for index, (category, direction, amount) in enumerate(parts) if amount > 0]
    db.add_all(entries)
    for entry in entries:
        await add_audit(db, user, "cashbook_borrowing_recorded", "CompanyCashbook", entry.id, {"after": {
            "action": payload.action, "transaction_date": payload.transaction_date.isoformat(), "lender": lender, "transaction_type": entry.category,
            "amount": money(entry.amount), "direction": entry.direction, "description": payload.description, "account": payload.account,
            "payment_mode": payload.payment_mode, "reference": payload.reference}})
    await commit_record(db)
    return {"ids": [str(entry.id) for entry in entries]}


@router.post("/results", status_code=201, dependencies=[Depends(require_csrf)])
async def create_result(payload: ProjectResultCreate, user: User = Depends(require_cashbook("write")), db: AsyncSession = Depends(get_db)):
    raise HTTPException(status_code=409, detail="Manual results are historical only. Review and approve the automatically calculated project result instead.")


@router.post("/result-approvals", status_code=201, dependencies=[Depends(require_csrf)])
async def approve_result(payload: ResultApprovalCreate, user: User = Depends(require_cashbook()), db: AsyncSession = Depends(get_db)):
    if not user.global_access:
        raise HTTPException(status_code=403, detail="Only global-access users can approve projected profit/loss")
    project = await db.scalar(select(Project).where(Project.id == payload.project_id).with_for_update())
    if project is None or project.currency != "INR":
        raise HTTPException(status_code=422, detail="Select an existing INR project")
    existing = await db.scalar(select(ProjectResultApproval).where(ProjectResultApproval.request_id == payload.request_id))
    if existing:
        if (existing.project_id, existing.as_of, existing.snapshot["fingerprint"], existing.note) != (
            payload.project_id, payload.as_of, payload.fingerprint, payload.note
        ):
            raise HTTPException(status_code=409, detail="This request was already used for a different approval")
        return {"id": str(existing.id)}
    snapshot = await overview_projection(db, project, user)
    if snapshot["fingerprint"] != payload.fingerprint:
        raise HTTPException(status_code=409, detail="The project calculation changed. Refresh and review the new figures before approving.")
    if abs(Decimal(snapshot["amount"])) >= Decimal("10000000000000000"):
        raise HTTPException(status_code=422, detail="The calculated result exceeds the supported amount range")
    latest = await db.scalar(select(ProjectResultApproval).where(
        ProjectResultApproval.project_id == project.id
    ).order_by(ProjectResultApproval.as_of.desc(), ProjectResultApproval.approved_at.desc(), ProjectResultApproval.id.desc()).limit(1))
    if latest and latest.as_of > payload.as_of:
        raise HTTPException(status_code=409, detail="A later result is already approved. Select that date or a later date.")
    if latest and latest.snapshot.get("fingerprint") == snapshot["fingerprint"]:
        raise HTTPException(status_code=409, detail="This project result is already approved and its amount has not changed.")
    record = ProjectResultApproval(id=uuid4(), request_id=payload.request_id, project_id=project.id,
                                   as_of=payload.as_of, amount=Decimal(snapshot["amount"]), snapshot=snapshot,
                                   note=payload.note, approved_by_id=user.id, approved_at=datetime.now(timezone.utc))
    db.add(record)
    await add_audit(db, user, "project_result_approved", "CompanyCashbook", record.id, {
        "project_id": str(project.id), "as_of": payload.as_of.isoformat(),
        "snapshot": snapshot, "note": payload.note,
        "previous_approved_amount": money(latest.amount) if latest else None,
    })
    await commit_record(db)
    return {"id": str(record.id)}


@router.post("/{record_type}/{record_id}/void", dependencies=[Depends(require_csrf)])
async def void_record(record_type: Literal["entries", "results"], record_id: UUID, payload: VoidCreate, user: User = Depends(require_cashbook("write")), db: AsyncSession = Depends(get_db)):
    model = CompanyCashEntry if record_type == "entries" else CompanyProjectResult
    record = await db.scalar(select(model).where(model.id == record_id).with_for_update())
    if record is None:
        raise HTTPException(status_code=404, detail="Cashbook record not found")
    if record.project_id:
        await require_writable_project(db, record.project_id)
    if record.voided_at:
        raise HTTPException(status_code=409, detail="This record has already been voided")
    record.voided_at = datetime.now(timezone.utc)
    record.voided_by_id = user.id
    record.void_reason = payload.reason
    await add_audit(db, user, "cashbook_record_voided", "CompanyCashbook", record.id, {"record_type": record_type, "reason": payload.reason, "amount": money(record.amount)})
    await db.commit()
    return {"status": "voided"}


class CashbookActivityCreate(BaseModel):
    page: Literal["cash", "borrowings", "results", "capital", "history", "audit-log"]


@router.post("/activities", status_code=204, dependencies=[Depends(require_csrf)])
async def record_cashbook_activity(payload: CashbookActivityCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    if payload.page == "audit-log":
        await require_company_audit()(user)
    else:
        await require_cashbook()(user)
    action, label = {
        "cash": ("visit_cash_transactions", "Cash Transactions"),
        "borrowings": ("visit_borrowings", "Borrowings"),
        "results": ("visit_project_profit_loss", "Project Profit & Loss"),
        "capital": ("visit_owner_capital", "Owner Capital"),
        "history": ("visit_cashbook_history", "Company Cashbook history"),
        "audit-log": ("visit_company_audit_log", "Company Audit Log"),
    }[payload.page]
    await add_audit(db, user, action, "CompanyCashbook", uuid4(), {"page": label, "activity": "visit"})
    await db.commit()
    return Response(status_code=204)


@router.get("/history")
async def history(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), search: str = Query("", max_length=200), start_time: datetime | None = None, end_time: datetime | None = None, user: User = Depends(require_cashbook()), db: AsyncSession = Depends(get_db)):
    return await cashbook_history_page(page, page_size, search, start_time, end_time, db)


@router.get("/records/{record_id}")
async def activity_record(record_id: UUID, user: User = Depends(require_cashbook()), db: AsyncSession = Depends(get_db)):
    for model, record_type, serialize in (
        (CompanyCashEntry, "entry", entry_dto),
        (CompanyProjectResult, "result", result_dto),
        (ProjectResultApproval, "approval", approval_dto),
    ):
        record = await db.get(model, record_id)
        if record is not None:
            names = dict((await db.execute(select(Project.id, Project.name).where(Project.id == record.project_id))).all())
            users = dict((await db.execute(select(User.id, User.name).where(User.id.in_([
                getattr(record, "recorded_by_id", None), getattr(record, "voided_by_id", None),
                getattr(record, "approved_by_id", None),
            ])))).all())
            return {"type": record_type, "record": serialize(record, names, users)}
    option = await db.get(CompanyCashOption, record_id)
    if option is not None:
        return {"type": "option", "record": option_dto(option)}
    raise HTTPException(status_code=404, detail="No saved Cashbook entry exists for this activity. Report requests do not create an entry.")


@router.get("/audit-log")
async def company_audit_log(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), search: str = Query("", max_length=200), start_time: datetime | None = None, end_time: datetime | None = None, user: User = Depends(require_company_audit()), db: AsyncSession = Depends(get_db)):
    return await cashbook_history_page(page, page_size, search, start_time, end_time, db, include_system=True)


@router.post("/history/export", dependencies=[Depends(require_csrf)])
async def export_history(search: str = Query("", max_length=200), start_time: datetime | None = None, end_time: datetime | None = None, user: User = Depends(require_cashbook("export_report")), db: AsyncSession = Depends(get_db)):
    return await cashbook_history_report(search, start_time, end_time, user, db)


@router.post("/audit-log/export", dependencies=[Depends(require_csrf)])
async def export_audit_log(search: str = Query("", max_length=200), start_time: datetime | None = None, end_time: datetime | None = None, user: User = Depends(require_company_audit("export_report")), db: AsyncSession = Depends(get_db)):
    return await cashbook_history_report(search, start_time, end_time, user, db, include_system=True)


@router.post("/activities/{activity_id}/export", status_code=204, dependencies=[Depends(require_csrf)])
async def export_activity(activity_id: UUID, source: Literal["history", "audit-log"], user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await (require_company_audit("export_report") if source == "audit-log" else require_cashbook("export_report"))(user)
    event = await db.scalar(select(AuditEvent).where(AuditEvent.id == activity_id, AuditEvent.entity_type.in_(["CompanyCashbook", "SystemBackup"] if source == "audit-log" else ["CompanyCashbook"])))
    if event is None:
        raise HTTPException(status_code=404, detail="Company Cashbook activity not found")
    if event.action in {"cashbook_entry_recorded", "cashbook_borrowing_recorded", "cashbook_record_voided", "project_result_approved", "cashbook_option_created"}:
        await require_cashbook()(user)
        await activity_record(event.entity_id, user, db)
    await add_audit(db, user, "cashbook_activity_export_requested", "CompanyCashbook", event.entity_id, {
        "activity_id": str(event.id), "activity": event.action,
        "completion": "Browser print/save completion is not observable",
    })
    await db.commit()
    return Response(status_code=204)


async def cashbook_history_report(search: str, start_time: datetime | None, end_time: datetime | None, user: User, db: AsyncSession, include_system: bool = False) -> dict:
    report = await cashbook_history_page(None, 100, search, start_time, end_time, db, include_system)
    await add_audit(db, user, "cashbook_history_export_requested", "CompanyCashbook", uuid4(), {
        "search": search, "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "completion": "Browser print/save completion is not observable",
    })
    await db.commit()
    return report


async def cashbook_history_page(page: int | None, page_size: int, search: str, start_time: datetime | None, end_time: datetime | None, db: AsyncSession, include_system: bool = False) -> dict:
    if page_size not in {10, 20, 50, 100}:
        raise HTTPException(status_code=422, detail="Page size must be 10, 20, 50, or 100")
    if any(value is not None and value.utcoffset() is None for value in (start_time, end_time)):
        raise HTTPException(status_code=422, detail="Date and time filters must include a timezone")
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=422, detail="From date and time must be before To date and time")
    filters = [AuditEvent.entity_type.in_(["CompanyCashbook", "SystemBackup"]) if include_system else AuditEvent.entity_type == "CompanyCashbook"]
    if start_time:
        filters.append(AuditEvent.occurred_at >= start_time.astimezone(timezone.utc))
    if end_time:
        filters.append(AuditEvent.occurred_at <= end_time.astimezone(timezone.utc))
    if search.strip():
        term = f"%{search.strip()}%"
        activity_term = f"%{search.strip().lower().replace('visited ', 'visit_').replace(' ', '_')}%"
        filters.append(or_(
            AuditEvent.action.ilike(term), AuditEvent.action.ilike(activity_term),
            User.username.ilike(term), User.name.ilike(term),
            cast(AuditEvent.entity_id, String).ilike(term), cast(AuditEvent.details, String).ilike(term),
        ))
    query = select(AuditEvent, User.username).outerjoin(User, AuditEvent.actor_id == User.id).where(*filters).order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    if page is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()
    total = await db.scalar(select(func.count(AuditEvent.id)).outerjoin(User, AuditEvent.actor_id == User.id).where(*filters)) or 0
    return {"items": [{"id": str(event.id), "occurred_at": event.occurred_at.isoformat(), "actor": username or "System", "action": event.action, "record_id": str(event.entity_id) if event.entity_id else None, "details": event.details} for event, username in rows], "page": page or 1, "page_size": page_size, "total": total}


@router.post("/export", dependencies=[Depends(require_csrf)])
async def export_report(start: date | None = None, end: date | None = None, search: str = Query("", max_length=200), kind: Kind | None = None, direction: Literal["in", "out"] | None = None, status: Literal["posted", "voided", "all"] = "posted", user: User = Depends(require_cashbook("export_report")), db: AsyncSession = Depends(get_db), category: str = Query("", max_length=80), custom_category: str = Query("", max_length=80), lender: str = Query("", max_length=160)):
    # Internal call bypasses the screen page limit; filtering and summaries use the same loaded entries.
    report = await cashbook(start, end, search, kind, direction, status, 1, 2**63 - 1, user, db, category, custom_category, lender)
    await add_audit(db, user, "cashbook_export_requested", "CompanyCashbook", uuid4(), {"start": report["start"], "end": report["end"], "search": search, "kind": kind, "custom_category": custom_category, "category": category, "lender": lender, "direction": direction, "status": status, "completion": "Browser print/save completion is not observable"})
    await db.commit()
    return report
