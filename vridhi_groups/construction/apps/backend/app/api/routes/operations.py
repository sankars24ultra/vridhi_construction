from datetime import date, datetime, timezone
from decimal import Decimal
from secrets import randbelow
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import BillingEntry, CashReceipt, Contract, Project, Timecard, User
from app.schemas import BillingCreate, CashReceiptCreate, TimecardCreate
from app.security import current_user, require_csrf, require_permission, require_project_access
from app.services.common import add_audit, money

router = APIRouter()


@router.get("/api/v1/projects/{project_id}/billing-summary", dependencies=[Depends(require_permission("cashflow", "read"))])
async def billing_summary(project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    contract = await db.scalar(select(Contract).where(Contract.project_id == project.id))
    entries = list((await db.scalars(select(BillingEntry).where(BillingEntry.project_id == project.id))).all())
    billed = sum((entry.amount for entry in entries), Decimal("0"))
    receipts = list((await db.scalars(select(CashReceipt).where(CashReceipt.project_id == project.id))).all())
    received_total = sum((receipt.amount for receipt in receipts), Decimal("0"))
    allocated_by_billing: dict[UUID, Decimal] = {}
    for receipt in receipts:
        if receipt.billing_entry_id:
            allocated_by_billing[receipt.billing_entry_id] = allocated_by_billing.get(receipt.billing_entry_id, Decimal("0")) + receipt.amount
    allocated_total = sum((min(entry.amount, allocated_by_billing.get(entry.id, Decimal("0"))) for entry in entries), Decimal("0"))
    return {"currency": project.currency, "approved_contract_value": money(contract.original_value if contract else 0), "billed_work": money(billed), "invoiced_amount": money(billed), "cash_received": money(received_total), "outstanding_invoices": money(max(Decimal("0"), billed - allocated_total)), "retainage_held": "0.00", "retainage_released": "0.00", "as_of": datetime.now(timezone.utc).isoformat()}


@router.get("/api/v1/projects/{project_id}/cash-flow", dependencies=[Depends(require_permission("cashflow", "read"))])
async def project_cash_flow(project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    summary = await billing_summary(project, db)
    billing_entries = list((await db.scalars(select(BillingEntry).where(BillingEntry.project_id == project.id).order_by(BillingEntry.submitted_date.desc(), BillingEntry.created_at.desc(), BillingEntry.id.desc()))).all())
    applications = []
    for application in billing_entries:
        received = await db.scalar(select(func.coalesce(func.sum(CashReceipt.amount), 0)).where(CashReceipt.billing_entry_id == application.id)) or 0
        received_amount = Decimal(str(received))
        applications.append({"id": str(application.id), "application_number": application.application_number,
                             "description": application.description, "submitted_date": application.submitted_date.isoformat(),
                             "billed_amount": money(application.amount), "received_amount": money(received_amount),
                             "outstanding_amount": money(max(Decimal("0"), application.amount - received_amount)), "status": application.status})
    receipts = list((await db.scalars(select(CashReceipt).where(CashReceipt.project_id == project.id).order_by(CashReceipt.received_date.desc(), CashReceipt.recorded_at.desc(), CashReceipt.id.desc()))).all())
    users = {user.id: user for user in (await db.scalars(select(User).where(User.id.in_([receipt.recorded_by_id for receipt in receipts])))).all()} if receipts else {}
    applications_by_id = {application.id: application for application in billing_entries}
    receipt_rows = [{"id": str(receipt.id), "received_date": receipt.received_date.isoformat(), "amount": money(receipt.amount),
                     "payment_method": receipt.payment_method, "reference": receipt.reference, "comment": receipt.comment,
                     "billing_entry_id": str(receipt.billing_entry_id) if receipt.billing_entry_id else None,
                     "application_number": applications_by_id[receipt.billing_entry_id].application_number if receipt.billing_entry_id in applications_by_id else None,
                     "application_description": applications_by_id[receipt.billing_entry_id].description if receipt.billing_entry_id in applications_by_id else None,
                     "recorded_by": users[receipt.recorded_by_id].name if receipt.recorded_by_id in users else "Unknown"}
                    for receipt in receipts]
    return {**summary, "applications": applications, "receipts": receipt_rows}


@router.post("/api/v1/projects/{project_id}/cash-receipts", status_code=201, dependencies=[Depends(require_csrf), Depends(require_permission("cashflow", "write"))])
async def create_cash_receipt(payload: CashReceiptCreate, project: Project = Depends(require_project_access), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if payload.billing_entry_id:
        application = await db.scalar(select(BillingEntry).where(BillingEntry.id == payload.billing_entry_id, BillingEntry.project_id == project.id).with_for_update())
        if not application:
            raise HTTPException(status_code=404, detail="Billing application not found")
        received = await db.scalar(select(func.coalesce(func.sum(CashReceipt.amount), 0)).where(CashReceipt.billing_entry_id == application.id)) or 0
        if payload.amount > max(Decimal("0"), application.amount - Decimal(str(received))):
            raise HTTPException(status_code=409, detail="Receipt exceeds the application's outstanding amount")
    receipt = CashReceipt(project_id=project.id, billing_entry_id=payload.billing_entry_id, received_date=payload.received_date,
                          amount=payload.amount, payment_method=payload.payment_method, reference=payload.reference,
                          comment=payload.comment, recorded_by_id=user.id)
    db.add(receipt)
    await db.flush()
    await add_audit(db, user, "client_cash_receipt_recorded", "CashReceipt", receipt.id)
    await db.commit()
    return {"id": str(receipt.id), "received_date": receipt.received_date.isoformat(), "amount": money(receipt.amount),
            "payment_method": receipt.payment_method, "reference": receipt.reference, "comment": receipt.comment,
            "billing_entry_id": str(receipt.billing_entry_id) if receipt.billing_entry_id else None}


@router.get("/api/v1/projects/{project_id}/progress-billings", dependencies=[Depends(require_permission("cashflow", "read"))])
async def list_billings(page: int = 1, page_size: int = Query(25, ge=1, le=100), project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    entries = list((await db.scalars(select(BillingEntry).where(BillingEntry.project_id == project.id).order_by(BillingEntry.submitted_date.desc(), BillingEntry.created_at.desc(), BillingEntry.id.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    total = await db.scalar(select(func.count(BillingEntry.id)).where(BillingEntry.project_id == project.id)) or 0
    return {"items": [{"id": str(item.id), "application_number": item.application_number, "description": item.description, "period_start": item.submitted_date.isoformat(), "period_end": item.submitted_date.isoformat(), "status": item.status, "currency": project.currency, "current_work_total": money(item.amount), "retainage_total": "0.00", "net_billable": money(item.amount), "version": item.version} for item in entries], "page": page, "page_size": page_size, "total": total}


@router.post("/api/v1/projects/{project_id}/progress-billings", status_code=201, dependencies=[Depends(require_csrf), Depends(require_permission("cashflow", "write"))])
async def create_billing(payload: BillingCreate, project: Project = Depends(require_project_access), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    entry = BillingEntry(project_id=project.id, application_number=f"PB-{randbelow(90000) + 10000}", description=payload.description, submitted_date=payload.submitted_date, amount=payload.amount, status="Submitted")
    db.add(entry)
    await db.flush()
    await add_audit(db, user, "billing_entry_created", "BillingEntry", entry.id)
    await db.commit()
    return {"id": str(entry.id), "project_id": str(project.id), "application_number": entry.application_number, "description": entry.description, "period_start": entry.submitted_date.isoformat(), "period_end": entry.submitted_date.isoformat(), "currency": project.currency, "current_work_total": money(entry.amount), "retainage_total": "0.00", "net_billable": money(entry.amount), "status": entry.status, "version": entry.version}


@router.post("/api/v1/projects/{project_id}/timecards", status_code=201, dependencies=[Depends(require_csrf)])
async def create_timecard(payload: TimecardCreate, project: Project = Depends(require_project_access), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    card = Timecard(project_id=project.id, employee_name=payload.employee_name, cost_code=payload.cost_code, work_date=payload.work_date, regular_hours=payload.regular_hours, hourly_rate=payload.hourly_rate, status="Pending", created_by_id=user.id)
    db.add(card)
    await db.flush()
    await add_audit(db, user, "timecard_created", "Timecard", card.id)
    await db.commit()
    return {"id": str(card.id), "project_id": str(card.project_id), "employee": {"name": card.employee_name}, "cost_code": {"name": card.cost_code}, "work_date": card.work_date.isoformat(), "regular_hours": str(card.regular_hours), "overtime_hours": "0", "labor_cost": money(card.regular_hours * card.hourly_rate), "status": card.status, "version": card.version, "permitted_actions": ["approve"]}


@router.get("/api/v1/projects/{project_id}/timecards")
async def list_timecards(page: int = 1, page_size: int = Query(25, ge=1, le=100), project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    cards = list((await db.scalars(select(Timecard).where(Timecard.project_id == project.id).order_by(Timecard.work_date.desc(), Timecard.id.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    total = await db.scalar(select(func.count(Timecard.id)).where(Timecard.project_id == project.id)) or 0
    return {"items": [{"id": str(card.id), "project_id": str(card.project_id), "employee": {"name": card.employee_name}, "cost_code": {"name": card.cost_code}, "work_date": card.work_date.isoformat(), "regular_hours": str(card.regular_hours), "overtime_hours": "0", "captured_regular_rate": money(card.hourly_rate), "labor_cost": money(card.regular_hours * card.hourly_rate), "status": card.status, "version": card.version, "permitted_actions": ["approve"] if card.status == "Pending" else []} for card in cards], "page": page, "page_size": page_size, "total": total}


@router.get("/api/v1/projects/{project_id}/attendance-summary")
async def attendance_summary(project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    cards = list((await db.scalars(select(Timecard).where(Timecard.project_id == project.id))).all())
    return {"date_from": date.today().isoformat(), "date_to": date.today().isoformat(), "regular_hours": str(sum((item.regular_hours for item in cards), Decimal("0"))), "overtime_hours": "0", "pending_count": sum(item.status == "Pending" for item in cards), "approved_count": sum(item.status == "Approved" for item in cards), "labor_cost": money(sum((item.regular_hours * item.hourly_rate for item in cards if item.status == "Approved"), Decimal("0"))), "currency": project.currency}
