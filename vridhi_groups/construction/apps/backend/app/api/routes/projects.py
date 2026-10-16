import secrets
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.models import BillingEntry, CashReceipt, Contract, LaborProgressClaim, LaborWorkEntry, PROJECT_STATUS_TRANSITIONS, Project, ProjectDocument, ProjectMembership, ProjectStatusHistory, ProjectValueHistory, PurchaseOrder, PurchaseOrderLine, User
from app.security import current_user, require_csrf, require_permission, require_project_access
from app.services.common import add_audit, dashboard_cost_summary, money, order_totals, project_dto, purchase_order_query

router = APIRouter()


@router.get("/api/v1/me/projects")
async def list_projects(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str | None = None, status_filter: str | None = Query(None, alias="status"), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    query = select(Project).order_by(Project.name)
    if not user.global_access:
        query = query.join(ProjectMembership).where(ProjectMembership.user_id == user.id)
    if search:
        query = query.where(Project.name.ilike(f"%{search.strip()}%"))
    if status_filter:
        query = query.where(Project.status == status_filter)
    projects = list((await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).all())
    count_query = select(func.count(Project.id))
    if not user.global_access:
        count_query = count_query.join(ProjectMembership).where(ProjectMembership.user_id == user.id)
    if search:
        count_query = count_query.where(Project.name.ilike(f"%{search.strip()}%"))
    if status_filter:
        count_query = count_query.where(Project.status == status_filter)
    total = await db.scalar(count_query) or 0
    contract_values = {}
    actual_costs = {}
    hold_reasons = {}
    if projects:
        project_ids = [project.id for project in projects]
        contract_rows = (await db.execute(select(Contract.project_id, func.sum(Contract.original_value)).where(Contract.project_id.in_(project_ids)).group_by(Contract.project_id))).all()
        direct_labor_rows = (await db.execute(select(LaborWorkEntry.project_id, func.sum(LaborWorkEntry.quantity * LaborWorkEntry.rate)).where(LaborWorkEntry.project_id.in_(project_ids)).group_by(LaborWorkEntry.project_id))).all()
        contract_labor_rows = (await db.execute(select(LaborProgressClaim.project_id, func.sum(LaborProgressClaim.amount)).where(LaborProgressClaim.project_id.in_(project_ids), LaborProgressClaim.status == "Certified").group_by(LaborProgressClaim.project_id))).all()
        material_rows = (await db.execute(select(PurchaseOrder.project_id, func.sum(PurchaseOrderLine.quantity * PurchaseOrderLine.unit_price)).join(PurchaseOrderLine, PurchaseOrderLine.purchase_order_id == PurchaseOrder.id).where(PurchaseOrder.project_id.in_(project_ids)).group_by(PurchaseOrder.project_id))).all()
        contract_values = {project_id: value for project_id, value in contract_rows}
        labor_costs = {project_id: value for project_id, value in direct_labor_rows}
        for project_id, value in contract_labor_rows:
            labor_costs[project_id] = (labor_costs.get(project_id, Decimal("0")) or Decimal("0")) + (value or Decimal("0"))
        material_costs = {project_id: value for project_id, value in material_rows}
        actual_costs = {
            project_id: (labor_costs.get(project_id, Decimal("0")) or Decimal("0")) + (material_costs.get(project_id, Decimal("0")) or Decimal("0"))
            for project_id in project_ids
        }
        on_hold_ids = [p.id for p in projects if p.status == "On Hold"]
        if on_hold_ids:
            histories = list((await db.scalars(
                select(ProjectStatusHistory)
                .where(ProjectStatusHistory.project_id.in_(on_hold_ids), ProjectStatusHistory.new_status == "On Hold")
                .order_by(ProjectStatusHistory.occurred_at.desc())
            )).all())
            for h in histories:
                if h.project_id not in hold_reasons:
                    hold_reasons[h.project_id] = h.comment
    memberships = {membership.project_id: membership for membership in (await db.scalars(select(ProjectMembership).where(ProjectMembership.user_id == user.id, ProjectMembership.project_id.in_([project.id for project in projects])))).all()} if projects else {}
    items = [{**project_dto(project), "contract_value": money(contract_values.get(project.id, Decimal("0"))),
              "actual_cost": money(actual_costs.get(project.id, Decimal("0"))), "hold_reason": hold_reasons.get(project.id),
              "permissions": ({**(user.global_permissions or {}), **(memberships[project.id].permissions or {})} if user.global_access and project.id in memberships else memberships[project.id].permissions if project.id in memberships else user.global_permissions if user.global_access else None)}
             for project in projects]
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/api/v1/projects/{project_id}", dependencies=[Depends(require_permission("overview", "read"))])
async def project_detail(project: Project = Depends(require_project_access), _: User = Depends(require_permission("overview", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    contracts = list((await db.scalars(select(Contract).where(Contract.project_id == project.id))).all())
    return {**project_dto(project), "contracts": [{"id": str(item.id), "number": item.number, "currency": item.currency, "approved_value": money(item.original_value), "version": item.version} for item in contracts], "capabilities": ["projects.read", "projects.write", "procurement.read", "procurement.write"]}


@router.get("/api/v1/projects/{project_id}/dashboard", dependencies=[Depends(require_permission("overview", "read"))])
async def dashboard(project: Project = Depends(require_project_access), _: User = Depends(require_permission("overview", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    contracts = list((await db.scalars(select(Contract).where(Contract.project_id == project.id))).all())
    orders = list((await db.scalars(purchase_order_query().where(PurchaseOrder.project_id == project.id))).all())
    direct_labor = await db.scalar(select(func.coalesce(func.sum(LaborWorkEntry.quantity * LaborWorkEntry.rate), 0)).where(LaborWorkEntry.project_id == project.id)) or 0
    contract_labor = await db.scalar(select(func.coalesce(func.sum(LaborProgressClaim.amount), 0)).where(LaborProgressClaim.project_id == project.id, LaborProgressClaim.status == "Certified")) or 0
    invoiced_amount = await db.scalar(select(func.coalesce(func.sum(BillingEntry.amount), 0)).where(BillingEntry.project_id == project.id)) or 0
    cash_received = await db.scalar(select(func.coalesce(func.sum(CashReceipt.amount), 0)).where(CashReceipt.project_id == project.id)) or 0
    contract_value = sum((item.original_value for item in contracts), Decimal("0"))
    total, paid, balance = (sum((order_totals(order)[i] for order in orders), Decimal("0")) for i in range(3))
    direct_labor_decimal = Decimal(str(direct_labor))
    contract_labor_decimal = Decimal(str(contract_labor))
    labor_cost = direct_labor_decimal + contract_labor_decimal
    direct_work_entries = list((await db.scalars(select(LaborWorkEntry).where(LaborWorkEntry.project_id == project.id).order_by(LaborWorkEntry.work_date))).all())
    certified_contract_claims = list((await db.scalars(select(LaborProgressClaim).where(LaborProgressClaim.project_id == project.id, LaborProgressClaim.status == "Certified").order_by(LaborProgressClaim.period_end))).all())
    costs = dashboard_cost_summary(labor_cost, orders, direct_work=direct_work_entries, contract_claims=certified_contract_claims)
    actual_decimal = costs["actual_cost"]
    margin = ((contract_value - actual_decimal) / contract_value * 100) if contract_value else Decimal("0")
    return {"project_id": str(project.id), "as_of": datetime.now(timezone.utc).isoformat(), "currency": project.currency,
            "budget": money(project.baseline_budget), "approved_contract_value": money(contract_value), "actual_cost": money(actual_decimal),
            "open_commitments": money(balance), "invoiced_amount": money(invoiced_amount), "cash_received": money(cash_received), "forecast_cost": money(actual_decimal),
            "margin_percent": str(margin.quantize(Decimal("0.01"))),
            "labor_cost_breakdown": {"contract_claims": money(contract_labor_decimal), "direct_workers": money(direct_labor_decimal)},
            "cost_breakdown": [{"category": "Labor", "amount": money(costs["labor_cost"]), "recorded": True},
                               {"category": "Materials", "amount": money(costs["material_cost"]), "recorded": True},
                               {"category": "Equipment & other", "amount": None, "recorded": False}],
            "monthly_costs": [{"month": item["month"], "amount": money(item["amount"])} for item in costs["monthly_costs"]]}


@router.post("/api/v1/projects", status_code=201, dependencies=[Depends(require_csrf)])
async def create_project(request: Request, user: User = Depends(require_permission("overview", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    form = await request.form(max_files=1, max_fields=12, max_part_size=settings.upload_max_bytes)

    def required_text(field: str, maximum: int) -> str:
        value = form.get(field)
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(status_code=422, detail=f"{field}: This field is required")
        value = value.strip()
        if len(value) > maximum:
            raise HTTPException(status_code=422, detail=f"{field}: Must be {maximum} characters or fewer")
        return value

    name = required_text("name", 160)
    location = required_text("location", 200)
    try:
        baseline_budget = Decimal(required_text("baseline_budget", 32))
        contract_value = Decimal(required_text("contract_value", 32))
    except InvalidOperation as error:
        raise HTTPException(status_code=422, detail="Budget and contract value must be valid numbers") from error
    if baseline_budget < 0 or contract_value < 0:
        raise HTTPException(status_code=422, detail="Budget and contract value cannot be negative")
    try:
        start_date = date.fromisoformat(required_text("start_date", 10))
    except ValueError as error:
        raise HTTPException(status_code=422, detail="start_date: Enter a valid date") from error
    project_status = str(form.get("status") or "Planning").strip()
    if project_status not in {"Planning", "Active"}:
        raise HTTPException(status_code=422, detail="status: Choose Planning or Active")
    currency = str(form.get("currency") or "INR").strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise HTTPException(status_code=422, detail="currency: Enter a three-letter currency code")
    raw_comment = form.get("plan_comment")
    plan_comment = raw_comment.strip() if isinstance(raw_comment, str) else ""
    if len(plan_comment) > 500:
        raise HTTPException(status_code=422, detail="plan_comment: Must be 500 characters or fewer")
    plan_document = form.get("plan_document")
    document_bytes = b""
    original_name = ""
    content_type = ""
    if plan_document and hasattr(plan_document, "filename") and plan_document.filename:
        original_name = Path(plan_document.filename).name
        suffix = Path(original_name).suffix.lower()
        allowed_types = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        if suffix not in allowed_types:
            raise HTTPException(status_code=415, detail="Plan files must be PDF, PNG, JPG, or DOCX")
        content_type = allowed_types[suffix]
        if plan_document.content_type and plan_document.content_type not in {content_type, "application/octet-stream"}:
            raise HTTPException(status_code=415, detail="File extension and content type do not match")
        document_bytes = await plan_document.read(settings.upload_max_bytes + 1)
        if len(document_bytes) > settings.upload_max_bytes:
            raise HTTPException(status_code=413, detail="Plan document exceeds the 10 MB upload limit")
        signatures = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff"}
        if suffix in signatures and not document_bytes.startswith(signatures[suffix]):
            raise HTTPException(status_code=415, detail="Uploaded file content does not match its file type")

    project = Project(name=name, location=location, status=project_status, baseline_budget=baseline_budget, currency=currency, start_date=start_date, created_by_id=user.id)
    project.memberships.append(ProjectMembership(user=user))
    project.contracts.append(Contract(number=f"VC-{secrets.token_hex(4).upper()}", original_value=contract_value, currency=currency))
    db.add(project)
    stored_path: Path | None = None
    try:
        await db.flush()
        if document_bytes:
            storage_name = f"{secrets.token_hex(24)}{Path(original_name).suffix.lower()}"
            stored_path = settings.upload_directory / storage_name
            stored_path.parent.mkdir(parents=True, exist_ok=True)
            stored_path.write_bytes(document_bytes)
            db.add(ProjectDocument(project_id=project.id, uploaded_by_id=user.id, storage_name=storage_name, filename=original_name, content_type=content_type, byte_size=len(document_bytes), category="initial_approval", comment=plan_comment))
        await add_audit(db, user, "project_created", "Project", project.id)
        await db.commit()
        await db.refresh(project)
        return {**project_dto(project), "initial_document_uploaded": bool(document_bytes)}
    except Exception:
        await db.rollback()
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise


@router.post("/api/v1/projects/{project_id}/documents", status_code=201, dependencies=[Depends(require_csrf), Depends(require_permission("overview", "write"))])
async def upload_project_document(request: Request, project: Project = Depends(require_project_access), user: User = Depends(require_permission("overview", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    if project.status not in {"Planning", "Active", "On Hold"}:
        raise HTTPException(status_code=409, detail="Plan uploads are unavailable for Completed or Cancelled projects")
    form = await request.form(max_files=1, max_fields=4, max_part_size=settings.upload_max_bytes)
    try:
        new_value = Decimal(str(form.get("new_estimate", "")))
        expected_value = Decimal(str(form.get("current_value", "")))
    except InvalidOperation as error:
        raise HTTPException(status_code=422, detail="Enter a valid new estimated value") from error
    if not new_value.is_finite() or not expected_value.is_finite() or new_value < 0 or new_value > Decimal("9999999999999999.99") or new_value != new_value.quantize(Decimal("0.01")):
        raise HTTPException(status_code=422, detail="New estimated value must be nonnegative with no more than two decimal places")
    document = form.get("plan_document")
    if not document or not hasattr(document, "filename") or not document.filename:
        raise HTTPException(status_code=422, detail="Choose a plan document")
    raw_comment = form.get("plan_comment", "")
    comment = raw_comment.strip() if isinstance(raw_comment, str) else ""
    if len(comment) > 500:
        raise HTTPException(status_code=422, detail="Comment must be 500 characters or fewer")
    filename = Path(document.filename).name
    suffix = Path(filename).suffix.lower()
    types = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if suffix not in types or document.content_type not in {types.get(suffix), "application/octet-stream", None}:
        raise HTTPException(status_code=415, detail="Choose a PDF, PNG, JPG, or DOCX with a matching file type")
    content = await document.read(settings.upload_max_bytes + 1)
    if not content:
        raise HTTPException(status_code=422, detail="Plan document is empty")
    if len(content) > settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="Plan document exceeds the 10 MB upload limit")
    signatures = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".docx": b"PK\x03\x04"}
    if not content.startswith(signatures[suffix]):
        raise HTTPException(status_code=415, detail="Uploaded content does not match its file type")
    contracts = list((await db.scalars(select(Contract).where(Contract.project_id == project.id).with_for_update())).all())
    current_value = sum((contract.original_value for contract in contracts), Decimal("0"))
    if expected_value != current_value:
        raise HTTPException(status_code=409, detail="Project value changed. Close and reopen the upload window to refresh.")
    if len(contracts) > 1 and new_value != current_value:
        raise HTTPException(status_code=409, detail="This project has multiple contracts. Revise the individual contracts instead.")
    storage_name = f"{secrets.token_hex(24)}{suffix}"
    path = settings.upload_directory / storage_name
    record = ProjectDocument(project_id=project.id, uploaded_by_id=user.id, storage_name=storage_name, filename=filename, content_type=types[suffix], byte_size=len(content), category="updated_plan", comment=comment)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        db.add(record)
        await db.flush()
        if new_value != current_value:
            if contracts:
                contracts[0].original_value = new_value
                contracts[0].version += 1
            else:
                db.add(Contract(project_id=project.id, number=f"VC-{secrets.token_hex(4).upper()}", original_value=new_value, currency=project.currency))
        db.add(ProjectValueHistory(project_id=project.id, document_id=record.id, actor_id=user.id, previous_value=current_value, new_value=new_value))
        await add_audit(db, user, "project_plan_uploaded", "ProjectDocument", record.id)
        await db.commit()
    except Exception:
        await db.rollback()
        path.unlink(missing_ok=True)
        raise
    return {"id": str(record.id), "filename": filename, "comment": comment}


@router.get("/api/v1/projects/{project_id}/value-history", dependencies=[Depends(require_permission("overview", "read"))])
async def project_value_history(project: Project = Depends(require_project_access), _: User = Depends(require_permission("overview", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    records = (await db.execute(select(ProjectValueHistory, ProjectDocument, User.name).join(ProjectDocument, ProjectDocument.id == ProjectValueHistory.document_id).join(User, User.id == ProjectValueHistory.actor_id).where(ProjectValueHistory.project_id == project.id).order_by(ProjectValueHistory.changed_at.desc()))).all()
    return {"items": [{"id": str(entry.id), "changed_at": entry.changed_at.isoformat(), "previous_value": money(entry.previous_value), "new_value": money(entry.new_value), "changed_by": name, "filename": document.filename, "comment": document.comment} for entry, document, name in records], "total": len(records), "page": 1, "page_size": len(records)}


@router.get("/api/v1/projects/{project_id}/documents", dependencies=[Depends(require_permission("overview", "read"))])
async def project_documents(project: Project = Depends(require_project_access), _: User = Depends(require_permission("overview", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    records = (await db.execute(select(ProjectDocument, User.name, ProjectValueHistory).join(User, User.id == ProjectDocument.uploaded_by_id).outerjoin(ProjectValueHistory, ProjectValueHistory.document_id == ProjectDocument.id).where(ProjectDocument.project_id == project.id).order_by(ProjectDocument.uploaded_at.desc()))).all()
    return {"items": [{"id": str(document.id), "filename": document.filename, "content_type": document.content_type, "uploaded_at": document.uploaded_at.isoformat(), "uploaded_by": name, "comment": document.comment, "current_value": money(history.previous_value) if history else None, "new_estimate": money(history.new_value) if history else None} for document, name, history in records], "total": len(records), "page": 1, "page_size": len(records)}


@router.get("/api/v1/projects/{project_id}/documents/{document_id}/file", dependencies=[Depends(require_permission("overview", "read"))])
async def download_project_document(document_id: UUID, project: Project = Depends(require_project_access), _: User = Depends(require_permission("overview", "read")), db: AsyncSession = Depends(get_db)) -> FileResponse:
    document = await db.scalar(select(ProjectDocument).where(ProjectDocument.id == document_id, ProjectDocument.project_id == project.id))
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    directory = settings.upload_directory.resolve()
    path = (directory / document.storage_name).resolve()
    if path.parent != directory or not path.is_file():
        raise HTTPException(status_code=404, detail="Document file unavailable")
    return FileResponse(path, media_type=document.content_type, filename=document.filename)


@router.patch("/api/v1/projects/{project_id}/status", dependencies=[Depends(require_csrf), Depends(require_permission("overview", "write"))])
async def update_project_status(project_id: UUID, payload: dict, expected_version: int = Query(...), project: Project = Depends(require_project_access), user: User = Depends(require_permission("overview", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    if project.version != expected_version:
        raise HTTPException(status_code=409, detail="Project changed. Refresh and try again.")
    target = str(payload.get("status", ""))
    if target not in PROJECT_STATUS_TRANSITIONS.get(project.status, ()):
        raise HTTPException(status_code=422, detail=f"Cannot change project status from {project.status} to {target}.")
    comment = str(payload.get("comment", "")).strip()
    if not comment or (target == "On Hold" and not str(payload.get("hold_reason", "")).strip()) or (target == "Completed" and payload.get("confirm_complete") is not True):
        raise HTTPException(status_code=422, detail="Status comment and required status-specific fields are required")
    previous = project.status
    project.status = target
    project.version += 1
    db.add(ProjectStatusHistory(project_id=project.id, previous_status=previous, new_status=target, comment=comment, actor_id=user.id))
    await add_audit(db, user, "project_status_changed", "Project", project.id)
    await db.commit()
    return project_dto(project)


@router.get("/api/v1/projects/{project_id}/status-history", dependencies=[Depends(require_permission("overview", "read"))])
async def status_history(page: int = 1, page_size: int = 25, project: Project = Depends(require_project_access), _: User = Depends(require_permission("overview", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    query = select(ProjectStatusHistory).where(ProjectStatusHistory.project_id == project.id).order_by(ProjectStatusHistory.occurred_at.desc(), ProjectStatusHistory.id.desc())
    items = list((await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).all())
    total = await db.scalar(select(func.count(ProjectStatusHistory.id)).where(ProjectStatusHistory.project_id == project.id)) or 0
    users = {str(user.id): user for user in (await db.scalars(select(User).where(User.id.in_([item.actor_id for item in items])))).all()} if items else {}
    return {"items": [{"id": str(item.id), "previous_status": item.previous_status, "new_status": item.new_status, "comment": item.comment, "occurred_at": item.occurred_at.isoformat(), "actor": {"id": str(item.actor_id), "name": users[str(item.actor_id)].name}} for item in items], "page": page, "page_size": page_size, "total": total}
