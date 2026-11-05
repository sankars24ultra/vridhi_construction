from decimal import Decimal
from uuid import UUID

from datetime import datetime, timezone
from pathlib import Path
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.core.config import settings
from app.models import LaborContract, LaborContractAddendum, LaborContractDocument, LaborContractPayment, LaborProgressClaim, LaborWagePayment, LaborWorkEntry, LaborWorker, Project, ProjectDocument, User
from app.schemas import LaborContractAddendumCreate, LaborContractCreate, LaborContractPaymentCreate, LaborDecisionCreate, LaborProgressClaimCreate, LaborWagePaymentCreate, LaborWorkEntryCreate, LaborWorkerCreate, LaborWorkerUpdate
from app.security import current_user, require_csrf, require_permission, require_project_access
from app.services.common import add_audit, money

router = APIRouter()


def contract_dto(contract: LaborContract) -> dict:
    return {"id": str(contract.id), "contract_number": contract.contract_number, "subcontractor_name": contract.subcontractor_name, "scope": contract.scope, "pricing_type": contract.pricing_type, "currency": contract.currency, "contract_value": money(contract.contract_value), "unit": contract.unit, "unit_rate": money(contract.unit_rate) if contract.unit_rate is not None else None, "baseline_document_id": str(contract.baseline_document_id) if contract.baseline_document_id else None, "baseline_document": contract.baseline_document.filename if contract.baseline_document else None, "status": contract.status, "version": contract.version}


@router.get("/api/v1/projects/{project_id}/labor/contracts")
async def list_labor_contracts(project: Project = Depends(require_project_access), _: User = Depends(require_permission("labor", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    contracts = list((await db.scalars(select(LaborContract).options(selectinload(LaborContract.baseline_document)).where(LaborContract.project_id == project.id).order_by(LaborContract.created_at.desc()))).all())
    contract_ids = [contract.id for contract in contracts]
    claims = list((await db.scalars(select(LaborProgressClaim).where(LaborProgressClaim.project_id == project.id).order_by(LaborProgressClaim.period_end.desc(), LaborProgressClaim.submitted_at.desc()))).all())
    addenda = list((await db.scalars(select(LaborContractAddendum).options(selectinload(LaborContractAddendum.plan_document)).where(LaborContractAddendum.project_id == project.id).order_by(LaborContractAddendum.submitted_at.desc()))).all())
    addendum_submitters = {addendum_id: name for addendum_id, name in (await db.execute(select(LaborContractAddendum.id, User.name).join(User, User.id == LaborContractAddendum.submitted_by_id).where(LaborContractAddendum.project_id == project.id))).all()}
    addendum_deciders = {addendum_id: name for addendum_id, name in (await db.execute(select(LaborContractAddendum.id, User.name).join(User, User.id == LaborContractAddendum.decided_by_id).where(LaborContractAddendum.project_id == project.id, LaborContractAddendum.decided_by_id.is_not(None)))).all()}
    claim_ids = [claim.id for claim in claims]
    payments = list((await db.scalars(select(LaborContractPayment).where(LaborContractPayment.project_id == project.id, LaborContractPayment.claim_id.in_(claim_ids)).order_by(LaborContractPayment.payment_date.desc(), LaborContractPayment.recorded_at.desc()))).all()) if claim_ids else []
    payments_by_claim: dict[UUID, list[dict]] = {claim_id: [] for claim_id in claim_ids}
    paid_by_claim: dict[UUID, Decimal] = {}
    for payment in payments:
        payments_by_claim.setdefault(payment.claim_id, []).append({"id": str(payment.id), "payment_date": payment.payment_date.isoformat(), "amount": money(payment.amount), "payment_mode": payment.payment_mode, "reference": payment.reference, "comment": payment.comment})
        paid_by_claim[payment.claim_id] = paid_by_claim.get(payment.claim_id, Decimal("0")) + payment.amount
    claims_by_contract: dict[UUID, list[dict]] = {contract_id: [] for contract_id in contract_ids}
    for claim in claims:
        paid = paid_by_claim.get(claim.id, Decimal("0"))
        claims_by_contract.setdefault(claim.contract_id, []).append({"id": str(claim.id), "claim_number": claim.claim_number, "period_start": claim.period_start.isoformat(), "period_end": claim.period_end.isoformat(), "work_description": claim.work_description, "quantity": str(claim.quantity) if claim.quantity is not None else None, "amount": money(claim.amount), "paid": money(paid), "payable": money(max(Decimal("0"), claim.amount - paid)), "status": claim.status, "decision_comment": claim.decision_comment, "payments": payments_by_claim.get(claim.id, [])})
    addenda_by_contract: dict[UUID, list[dict]] = {contract_id: [] for contract_id in contract_ids}
    for addendum in addenda:
        addenda_by_contract.setdefault(addendum.contract_id, []).append({"id": str(addendum.id), "plan_document_id": str(addendum.plan_document_id), "plan_filename": addendum.plan_document.filename, "reason": addendum.reason, "previous_value": money(addendum.previous_value), "revised_value": money(addendum.revised_value), "status": addendum.status, "submitted_at": addendum.submitted_at.isoformat(), "submitted_by": addendum_submitters.get(addendum.id), "decided_at": addendum.decided_at.isoformat() if addendum.decided_at else None, "decided_by": addendum_deciders.get(addendum.id), "decision_comment": addendum.decision_comment, "document_filename": addendum.document_filename, "document_content_type": addendum.document_content_type, "document_byte_size": addendum.document_byte_size, "document_url": f"/api/v1/projects/{project.id}/labor/addenda/{addendum.id}/file" if addendum.document_storage_name else None})
    contract_items = []
    for contract in contracts:
        contract_claims = claims_by_contract.get(contract.id, [])
        certified = sum((Decimal(item["amount"]) for item in contract_claims if item["status"] == "Certified"), Decimal("0"))
        paid = sum((Decimal(item["paid"]) for item in contract_claims), Decimal("0"))
        contract_items.append({**contract_dto(contract), "certified": money(certified), "paid": money(paid), "payable": money(max(Decimal("0"), certified - paid)), "claims": contract_claims, "addenda": addenda_by_contract.get(contract.id, [])})
    return {"currency": project.currency, "contracts": contract_items, "plan_documents": [{"id": str(document.id), "filename": document.filename, "category": document.category, "uploaded_at": document.uploaded_at.isoformat(), "comment": document.comment} for document in (await db.scalars(select(ProjectDocument).where(ProjectDocument.project_id == project.id, ProjectDocument.category.in_(("initial_approval", "updated_plan"))).order_by(ProjectDocument.uploaded_at.desc()))).all()]}


@router.post("/api/v1/projects/{project_id}/labor/contracts", status_code=201, dependencies=[Depends(require_csrf)])
async def create_labor_contract(request: Request, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    form = await request.form(max_files=1, max_fields=12, max_part_size=settings.upload_max_bytes)
    try:
        payload = LaborContractCreate.model_validate({key: form.get(key) for key in ("subcontractor_name", "scope", "pricing_type", "contract_value", "unit", "unit_rate", "baseline_document_id") if form.get(key) not in (None, "")})
    except Exception as error:
        raise HTTPException(status_code=422, detail="Enter valid labor contract details and pricing basis") from error
    if payload.baseline_document_id:
        document = await db.scalar(select(ProjectDocument).where(ProjectDocument.id == payload.baseline_document_id, ProjectDocument.project_id == project.id, ProjectDocument.category.in_(("initial_approval", "updated_plan"))))
        if not document:
            raise HTTPException(status_code=404, detail="Plan revision not found for this project")
    upload = form.get("contract_document")
    attachment = None
    file_path = None
    if upload and hasattr(upload, "filename") and upload.filename:
        filename = Path(upload.filename).name
        suffix = Path(filename).suffix.lower()
        types = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        signatures = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".docx": b"PK\x03\x04"}
        if suffix not in types or upload.content_type not in {types.get(suffix), "application/octet-stream", None}:
            raise HTTPException(status_code=415, detail="Choose a PDF, PNG, JPG, or DOCX with a matching file type")
        content = await upload.read(settings.upload_max_bytes + 1)
        if not content:
            raise HTTPException(status_code=422, detail="Contract document is empty")
        if len(content) > settings.upload_max_bytes:
            raise HTTPException(status_code=413, detail="Contract document exceeds the 10 MB upload limit")
        if not content.startswith(signatures[suffix]):
            raise HTTPException(status_code=415, detail="Uploaded content does not match its file type")
        storage_name = f"{secrets.token_hex(24)}{suffix}"
        file_path = settings.upload_directory / storage_name
        attachment = (storage_name, filename, types[suffix], len(content), content)
    contract = LaborContract(project_id=project.id, contract_number=f"LC-{secrets.token_hex(4).upper()}", subcontractor_name=payload.subcontractor_name.strip(), scope=payload.scope.strip(), pricing_type=payload.pricing_type, currency=project.currency, contract_value=payload.contract_value, unit=payload.unit.strip() if payload.unit else None, unit_rate=payload.unit_rate, baseline_document_id=payload.baseline_document_id, created_by_id=user.id)
    db.add(contract)
    try:
        await db.flush()
        if attachment and file_path:
            storage_name, filename, content_type, byte_size, content = attachment
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
            db.add(LaborContractDocument(project_id=project.id, contract_id=contract.id, uploaded_by_id=user.id, storage_name=storage_name, filename=filename, content_type=content_type, byte_size=byte_size, comment="Contract document"))
        await add_audit(db, user, "labor_contract_created", "LaborContract", contract.id)
        await db.commit()
    except Exception:
        await db.rollback()
        if file_path:
            file_path.unlink(missing_ok=True)
        raise
    return {**contract_dto(contract), "certified": "0.00", "paid": "0.00", "payable": "0.00", "claims": [], "addenda": []}


@router.get("/api/v1/projects/{project_id}/labor/documents")
async def list_labor_contract_documents(project: Project = Depends(require_project_access), _: User = Depends(require_permission("labor", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    rows = (await db.execute(select(LaborContractDocument, LaborContract.contract_number, LaborContract.subcontractor_name, User.name).join(LaborContract, LaborContract.id == LaborContractDocument.contract_id).join(User, User.id == LaborContractDocument.uploaded_by_id).where(LaborContractDocument.project_id == project.id).order_by(LaborContractDocument.uploaded_at.desc()))).all()
    return {"items": [{"id": str(document.id), "contract_id": str(document.contract_id), "contract_number": number, "subcontractor_name": subcontractor, "filename": document.filename, "content_type": document.content_type, "byte_size": document.byte_size, "uploaded_at": document.uploaded_at.isoformat(), "uploaded_by": uploader, "comment": document.comment, "url": f"/api/v1/projects/{project.id}/labor/documents/{document.id}/file"} for document, number, subcontractor, uploader in rows], "total": len(rows)}


@router.get("/api/v1/projects/{project_id}/labor/documents/{document_id}/file")
async def download_labor_contract_document(document_id: UUID, project: Project = Depends(require_project_access), _: User = Depends(require_permission("labor", "read")), db: AsyncSession = Depends(get_db)) -> FileResponse:
    document = await db.scalar(select(LaborContractDocument).where(LaborContractDocument.id == document_id, LaborContractDocument.project_id == project.id))
    if not document:
        raise HTTPException(status_code=404, detail="Labor contract document not found")
    directory = settings.upload_directory.resolve()
    path = (directory / document.storage_name).resolve()
    if path.parent != directory or not path.is_file():
        raise HTTPException(status_code=404, detail="Labor contract document unavailable")
    return FileResponse(path, media_type=document.content_type, filename=document.filename)


@router.post("/api/v1/projects/{project_id}/labor/contracts/{contract_id}/addenda", status_code=201, dependencies=[Depends(require_csrf)])
async def create_labor_contract_addendum(contract_id: UUID, request: Request, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    form = await request.form(max_files=1, max_fields=5, max_part_size=settings.upload_max_bytes)
    try:
        payload = LaborContractAddendumCreate.model_validate({key: form.get(key) for key in ("plan_document_id", "reason", "revised_value")})
    except Exception as error:
        raise HTTPException(status_code=422, detail="Enter a plan revision, reason, and revised contract value") from error
    contract = await db.scalar(select(LaborContract).where(LaborContract.id == contract_id, LaborContract.project_id == project.id).with_for_update())
    if not contract or contract.status != "Active":
        raise HTTPException(status_code=404, detail="Active labor contract not found")
    document = await db.scalar(select(ProjectDocument).where(ProjectDocument.id == payload.plan_document_id, ProjectDocument.project_id == project.id, ProjectDocument.category.in_(("initial_approval", "updated_plan"))))
    if not document:
        raise HTTPException(status_code=404, detail="Plan revision not found for this project")
    pending = await db.scalar(select(LaborContractAddendum.id).where(LaborContractAddendum.contract_id == contract.id, LaborContractAddendum.status == "Pending approval"))
    if pending:
        raise HTTPException(status_code=409, detail="Resolve the pending addendum before creating another")
    upload = form.get("addendum_document")
    file_path = None
    attachment = None
    if upload and hasattr(upload, "filename") and upload.filename:
        filename = Path(upload.filename).name
        suffix = Path(filename).suffix.lower()
        types = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        signatures = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".docx": b"PK\x03\x04"}
        if suffix not in types or upload.content_type not in {types.get(suffix), "application/octet-stream", None}:
            raise HTTPException(status_code=415, detail="Choose a PDF, PNG, JPG, or DOCX with a matching file type")
        content = await upload.read(settings.upload_max_bytes + 1)
        if not content:
            raise HTTPException(status_code=422, detail="Addendum document is empty")
        if len(content) > settings.upload_max_bytes:
            raise HTTPException(status_code=413, detail="Addendum document exceeds the 10 MB upload limit")
        if not content.startswith(signatures[suffix]):
            raise HTTPException(status_code=415, detail="Uploaded content does not match its file type")
        storage_name = f"{secrets.token_hex(24)}{suffix}"
        file_path = settings.upload_directory / storage_name
        attachment = (storage_name, filename, types[suffix], len(content), content)
    addendum = LaborContractAddendum(project_id=project.id, contract_id=contract.id, plan_document_id=document.id, reason=payload.reason.strip(), previous_value=contract.contract_value, revised_value=payload.revised_value, submitted_by_id=user.id)
    db.add(addendum)
    try:
        await db.flush()
        if attachment and file_path:
            addendum.document_storage_name, addendum.document_filename, addendum.document_content_type, addendum.document_byte_size, content = attachment
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
        await add_audit(db, user, "labor_contract_addendum_submitted", "LaborContractAddendum", addendum.id)
        await db.commit()
    except Exception:
        await db.rollback()
        if file_path:
            file_path.unlink(missing_ok=True)
        raise
    return {"id": str(addendum.id), "contract_id": str(contract.id), "previous_value": money(addendum.previous_value), "revised_value": money(addendum.revised_value), "status": addendum.status}


@router.get("/api/v1/projects/{project_id}/labor/addenda/{addendum_id}/file")
async def download_labor_addendum_document(addendum_id: UUID, project: Project = Depends(require_project_access), _: User = Depends(require_permission("labor", "read")), db: AsyncSession = Depends(get_db)) -> FileResponse:
    addendum = await db.scalar(select(LaborContractAddendum).where(LaborContractAddendum.id == addendum_id, LaborContractAddendum.project_id == project.id))
    if not addendum or not addendum.document_storage_name or not addendum.document_filename or not addendum.document_content_type:
        raise HTTPException(status_code=404, detail="Labor addendum document not found")
    directory = settings.upload_directory.resolve()
    path = (directory / addendum.document_storage_name).resolve()
    if path.parent != directory or not path.is_file():
        raise HTTPException(status_code=404, detail="Labor addendum document unavailable")
    return FileResponse(path, media_type=addendum.document_content_type, filename=addendum.document_filename)


@router.post("/api/v1/projects/{project_id}/labor/addenda/{addendum_id}/decision", dependencies=[Depends(require_csrf)])
async def decide_labor_contract_addendum(addendum_id: UUID, payload: LaborDecisionCreate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    addendum = await db.scalar(select(LaborContractAddendum).where(LaborContractAddendum.id == addendum_id, LaborContractAddendum.project_id == project.id).with_for_update())
    if not addendum or addendum.status != "Pending approval":
        raise HTTPException(status_code=404, detail="Pending labor addendum not found")
    contract = await db.scalar(select(LaborContract).where(LaborContract.id == addendum.contract_id, LaborContract.project_id == project.id).with_for_update())
    if not contract or contract.contract_value != addendum.previous_value:
        raise HTTPException(status_code=409, detail="Contract changed since this addendum was submitted")
    addendum.status = "Approved" if payload.decision == "approve" else "Rejected"
    addendum.decided_by_id = user.id
    addendum.decision_comment = payload.comment.strip() if payload.comment else None
    addendum.decided_at = datetime.now(timezone.utc)
    if payload.decision == "approve":
        contract.contract_value = addendum.revised_value
        contract.version += 1
    await add_audit(db, user, f"labor_contract_addendum_{payload.decision}d", "LaborContractAddendum", addendum.id)
    await db.commit()
    return {"id": str(addendum.id), "status": addendum.status, "contract_value": money(contract.contract_value)}


@router.post("/api/v1/projects/{project_id}/labor/contracts/{contract_id}/claims", status_code=201, dependencies=[Depends(require_csrf)])
async def create_labor_progress_claim(contract_id: UUID, payload: LaborProgressClaimCreate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    contract = await db.scalar(select(LaborContract).where(LaborContract.id == contract_id, LaborContract.project_id == project.id).with_for_update())
    if not contract or contract.status != "Active":
        raise HTTPException(status_code=404, detail="Active labor contract not found")
    if contract.pricing_type == "unit_rate" and (payload.quantity is None or payload.amount != (payload.quantity * contract.unit_rate).quantize(Decimal("0.01"))):
        raise HTTPException(status_code=422, detail="Claim amount must equal certified quantity multiplied by contract unit rate")
    if contract.pricing_type == "lump_sum" and payload.quantity is not None:
        raise HTTPException(status_code=422, detail="Lump-sum claims cannot specify a contract unit quantity")
    certified_to_date = await db.scalar(select(func.coalesce(func.sum(LaborProgressClaim.amount), 0)).where(LaborProgressClaim.contract_id == contract.id, LaborProgressClaim.status == "Certified")) or 0
    pending_to_date = await db.scalar(select(func.coalesce(func.sum(LaborProgressClaim.amount), 0)).where(LaborProgressClaim.contract_id == contract.id, LaborProgressClaim.status == "Pending certification")) or 0
    if Decimal(str(certified_to_date)) + Decimal(str(pending_to_date)) + payload.amount > contract.contract_value:
        raise HTTPException(status_code=409, detail="Claim would exceed the current authorized contract value")
    claim = LaborProgressClaim(project_id=project.id, contract_id=contract.id, claim_number=f"LPC-{secrets.token_hex(4).upper()}", period_start=payload.period_start, period_end=payload.period_end, work_description=payload.work_description.strip(), quantity=payload.quantity, amount=payload.amount, submitted_by_id=user.id)
    db.add(claim)
    await db.flush()
    await add_audit(db, user, "labor_progress_claim_submitted", "LaborProgressClaim", claim.id)
    await db.commit()
    return {"id": str(claim.id), "claim_number": claim.claim_number, "status": claim.status, "amount": money(claim.amount)}


@router.post("/api/v1/projects/{project_id}/labor/claims/{claim_id}/decision", dependencies=[Depends(require_csrf)])
async def decide_labor_progress_claim(claim_id: UUID, payload: LaborDecisionCreate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    claim = await db.scalar(select(LaborProgressClaim).where(LaborProgressClaim.id == claim_id, LaborProgressClaim.project_id == project.id).with_for_update())
    if not claim or claim.status != "Pending certification":
        raise HTTPException(status_code=404, detail="Pending labor claim not found")
    contract = await db.scalar(select(LaborContract).where(LaborContract.id == claim.contract_id, LaborContract.project_id == project.id).with_for_update())
    if payload.decision == "approve":
        existing_authorized = await db.scalar(select(func.coalesce(func.sum(LaborProgressClaim.amount), 0)).where(LaborProgressClaim.contract_id == contract.id, LaborProgressClaim.status.in_(("Certified", "Pending certification")), LaborProgressClaim.id != claim.id)) or 0
        if Decimal(str(existing_authorized)) + claim.amount > contract.contract_value:
            raise HTTPException(status_code=409, detail="Claim would exceed the current authorized contract value")
    claim.status = "Certified" if payload.decision == "approve" else "Rejected"
    claim.decided_by_id = user.id
    claim.decision_comment = payload.comment.strip() if payload.comment else None
    claim.decided_at = datetime.now(timezone.utc)
    await add_audit(db, user, f"labor_claim_{payload.decision}d", "LaborProgressClaim", claim.id)
    await db.commit()
    return {"id": str(claim.id), "status": claim.status}


@router.post("/api/v1/projects/{project_id}/labor/claims/{claim_id}/payments", status_code=201, dependencies=[Depends(require_csrf)])
async def pay_labor_progress_claim(claim_id: UUID, payload: LaborContractPaymentCreate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    claim = await db.scalar(select(LaborProgressClaim).where(LaborProgressClaim.id == claim_id, LaborProgressClaim.project_id == project.id).with_for_update())
    if not claim or claim.status != "Certified":
        raise HTTPException(status_code=409, detail="Only certified labor claims can be paid")
    paid = await db.scalar(select(func.coalesce(func.sum(LaborContractPayment.amount), 0)).where(LaborContractPayment.claim_id == claim.id)) or 0
    balance = claim.amount - Decimal(str(paid))
    if payload.amount > balance:
        raise HTTPException(status_code=409, detail="Payment exceeds the certified unpaid claim balance")
    payment = LaborContractPayment(project_id=project.id, claim_id=claim.id, payment_date=payload.payment_date, amount=payload.amount, payment_mode=payload.payment_mode, reference=payload.reference, comment=payload.comment, recorded_by_id=user.id)
    db.add(payment)
    await db.flush()
    await add_audit(db, user, "labor_contract_payment_recorded", "LaborContractPayment", payment.id)
    await db.commit()
    return {"id": str(payment.id), "claim_id": str(claim.id), "amount": money(payment.amount), "payment_date": payment.payment_date.isoformat(), "payment_mode": payment.payment_mode, "reference": payment.reference}


@router.get("/api/v1/projects/{project_id}/labor")
async def labor_ledger(project: Project = Depends(require_project_access), _: User = Depends(require_permission("labor", "read")), db: AsyncSession = Depends(get_db)) -> dict:
    workers = list((await db.scalars(select(LaborWorker).where(LaborWorker.project_id == project.id).order_by(LaborWorker.active.desc(), LaborWorker.name))).all())
    work_entries = list((await db.scalars(select(LaborWorkEntry).where(LaborWorkEntry.project_id == project.id).order_by(LaborWorkEntry.work_date.desc(), LaborWorkEntry.recorded_at.desc()).limit(200))).all())
    payments = list((await db.scalars(select(LaborWagePayment).where(LaborWagePayment.project_id == project.id).order_by(LaborWagePayment.payment_date.desc(), LaborWagePayment.recorded_at.desc()).limit(200))).all())
    worker_ids = [worker.id for worker in workers]
    earned_rows = (await db.execute(select(LaborWorkEntry.worker_id, func.sum(LaborWorkEntry.quantity * LaborWorkEntry.rate)).where(LaborWorkEntry.project_id == project.id, LaborWorkEntry.worker_id.in_(worker_ids)).group_by(LaborWorkEntry.worker_id))).all() if worker_ids else []
    unit_rows = (await db.execute(select(LaborWorkEntry.worker_id, LaborWorkEntry.unit, func.sum(LaborWorkEntry.quantity), func.count(LaborWorkEntry.id)).where(LaborWorkEntry.project_id == project.id, LaborWorkEntry.worker_id.in_(worker_ids)).group_by(LaborWorkEntry.worker_id, LaborWorkEntry.unit))).all() if worker_ids else []
    paid_rows = (await db.execute(select(LaborWagePayment.worker_id, func.sum(LaborWagePayment.amount)).where(LaborWagePayment.project_id == project.id, LaborWagePayment.worker_id.in_(worker_ids)).group_by(LaborWagePayment.worker_id))).all() if worker_ids else []
    earned_by_worker = {worker_id: Decimal(str(amount or 0)) for worker_id, amount in earned_rows}
    paid_by_worker = {worker_id: Decimal(str(amount or 0)) for worker_id, amount in paid_rows}
    units_by_worker: dict[UUID, list[dict]] = {worker_id: [] for worker_id in worker_ids}
    work_count_by_worker: dict[UUID, int] = {worker_id: 0 for worker_id in worker_ids}
    for worker_id, unit, quantity, entry_count in unit_rows:
        units_by_worker.setdefault(worker_id, []).append({"unit": unit, "quantity": str(quantity or 0)})
        work_count_by_worker[worker_id] = work_count_by_worker.get(worker_id, 0) + int(entry_count or 0)
    workers_by_id = {worker.id: worker for worker in workers}
    total_earned = sum(earned_by_worker.values(), Decimal("0"))
    total_paid = sum(paid_by_worker.values(), Decimal("0"))
    return {
        "currency": project.currency,
        "summary": {"worker_count": sum(worker.active for worker in workers), "total_earned": money(total_earned), "total_paid": money(total_paid), "payable": money(max(Decimal("0"), total_earned - total_paid)), "total_work_entries": sum(work_count_by_worker.values()), "work_units": [{"unit": unit, "quantity": str(sum((Decimal(item["quantity"]) for worker_units in units_by_worker.values() for item in worker_units if item["unit"] == unit), Decimal("0")))} for unit in sorted({item["unit"] for worker_units in units_by_worker.values() for item in worker_units})]},
        "workers": [{"id": str(worker.id), "name": worker.name, "trade": worker.trade, "phone": worker.phone, "active": worker.active, "version": worker.version, "earned": money(earned_by_worker.get(worker.id, Decimal("0"))), "paid": money(paid_by_worker.get(worker.id, Decimal("0"))), "payable": money(max(Decimal("0"), earned_by_worker.get(worker.id, Decimal("0")) - paid_by_worker.get(worker.id, Decimal("0")))), "work_entry_count": work_count_by_worker.get(worker.id, 0), "work_units": units_by_worker.get(worker.id, [])} for worker in workers],
        "work_entries": [{"id": str(entry.id), "worker_id": str(entry.worker_id), "worker_name": workers_by_id[entry.worker_id].name, "trade": workers_by_id[entry.worker_id].trade, "work_date": entry.work_date.isoformat(), "description": entry.description, "quantity": str(entry.quantity), "unit": entry.unit, "rate": money(entry.rate), "amount": money(entry.quantity * entry.rate)} for entry in work_entries if entry.worker_id in workers_by_id],
        "payments": [{"id": str(payment.id), "worker_id": str(payment.worker_id), "worker_name": workers_by_id[payment.worker_id].name, "payment_date": payment.payment_date.isoformat(), "amount": money(payment.amount), "payment_mode": payment.payment_mode, "reference": payment.reference, "comment": payment.comment} for payment in payments if payment.worker_id in workers_by_id],
    }


@router.post("/api/v1/projects/{project_id}/labor/workers", status_code=201, dependencies=[Depends(require_csrf)])
async def create_labor_worker(payload: LaborWorkerCreate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    worker = LaborWorker(project_id=project.id, name=payload.name.strip(), trade=payload.trade.strip(), phone=payload.phone.strip() if payload.phone else None)
    db.add(worker)
    await db.flush()
    await add_audit(db, user, "labor_worker_created", "LaborWorker", worker.id)
    await db.commit()
    return {"id": str(worker.id), "name": worker.name, "trade": worker.trade, "phone": worker.phone, "active": worker.active}


@router.put("/api/v1/projects/{project_id}/labor/workers/{worker_id}", dependencies=[Depends(require_csrf)])
async def update_labor_worker(worker_id: UUID, payload: LaborWorkerUpdate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    worker = await db.scalar(select(LaborWorker).where(LaborWorker.id == worker_id, LaborWorker.project_id == project.id).with_for_update())
    if not worker:
        raise HTTPException(status_code=404, detail="Labor worker not found")
    if worker.version != payload.expected_version:
        raise HTTPException(status_code=409, detail="Worker details changed. Refresh and try again.")
    worker.name = payload.name.strip()
    worker.trade = payload.trade.strip()
    worker.phone = payload.phone.strip() if payload.phone else None
    worker.version += 1
    await add_audit(db, user, "labor_worker_updated", "LaborWorker", worker.id)
    await db.commit()
    return {"id": str(worker.id), "name": worker.name, "trade": worker.trade, "phone": worker.phone, "active": worker.active, "version": worker.version}


@router.patch("/api/v1/projects/{project_id}/labor/workers/{worker_id}/status", dependencies=[Depends(require_csrf)])
async def set_labor_worker_status(worker_id: UUID, payload: dict, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    worker = await db.scalar(select(LaborWorker).where(LaborWorker.id == worker_id, LaborWorker.project_id == project.id).with_for_update())
    if not worker:
        raise HTTPException(status_code=404, detail="Labor worker not found")
    active = payload.get("active")
    if not isinstance(active, bool):
        raise HTTPException(status_code=422, detail="active must be true or false")
    if worker.active == active:
        return {"id": str(worker.id), "active": worker.active, "version": worker.version}
    if not active:
        earned = await db.scalar(select(func.coalesce(func.sum(LaborWorkEntry.quantity * LaborWorkEntry.rate), 0)).where(LaborWorkEntry.project_id == project.id, LaborWorkEntry.worker_id == worker.id)) or 0
        paid = await db.scalar(select(func.coalesce(func.sum(LaborWagePayment.amount), 0)).where(LaborWagePayment.project_id == project.id, LaborWagePayment.worker_id == worker.id)) or 0
        if Decimal(str(earned)) > Decimal(str(paid)):
            raise HTTPException(status_code=409, detail="Pay the worker's outstanding recorded balance before deactivating")
    worker.active = active
    worker.version += 1
    await add_audit(db, user, "labor_worker_activated" if active else "labor_worker_deactivated", "LaborWorker", worker.id)
    await db.commit()
    return {"id": str(worker.id), "active": worker.active, "version": worker.version}


@router.post("/api/v1/projects/{project_id}/labor/work-entries", status_code=201, dependencies=[Depends(require_csrf)])
async def create_labor_work_entry(payload: LaborWorkEntryCreate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    worker = await db.scalar(select(LaborWorker).where(LaborWorker.id == payload.worker_id, LaborWorker.project_id == project.id, LaborWorker.active.is_(True)))
    if not worker:
        raise HTTPException(status_code=404, detail="Active labor worker not found")
    entry = LaborWorkEntry(project_id=project.id, worker_id=worker.id, work_date=payload.work_date, description=payload.description.strip(), quantity=payload.quantity, unit=payload.unit, rate=payload.rate, recorded_by_id=user.id)
    db.add(entry)
    await db.flush()
    await add_audit(db, user, "labor_work_recorded", "LaborWorkEntry", entry.id)
    await db.commit()
    return {"id": str(entry.id), "worker_id": str(worker.id), "worker_name": worker.name, "work_date": entry.work_date.isoformat(), "description": entry.description, "quantity": str(entry.quantity), "unit": entry.unit, "rate": money(entry.rate), "amount": money(entry.quantity * entry.rate)}


@router.post("/api/v1/projects/{project_id}/labor/payments", status_code=201, dependencies=[Depends(require_csrf)])
async def create_labor_wage_payment(payload: LaborWagePaymentCreate, project: Project = Depends(require_project_access), user: User = Depends(require_permission("labor", "write")), db: AsyncSession = Depends(get_db)) -> dict:
    worker = await db.scalar(select(LaborWorker).where(LaborWorker.id == payload.worker_id, LaborWorker.project_id == project.id, LaborWorker.active.is_(True)).with_for_update())
    if not worker:
        raise HTTPException(status_code=404, detail="Active labor worker not found")
    earned = await db.scalar(select(func.coalesce(func.sum(LaborWorkEntry.quantity * LaborWorkEntry.rate), 0)).where(LaborWorkEntry.project_id == project.id, LaborWorkEntry.worker_id == worker.id)) or 0
    paid = await db.scalar(select(func.coalesce(func.sum(LaborWagePayment.amount), 0)).where(LaborWagePayment.project_id == project.id, LaborWagePayment.worker_id == worker.id)) or 0
    payable = Decimal(str(earned)) - Decimal(str(paid))
    if payload.amount > payable:
        raise HTTPException(status_code=409, detail="Payment exceeds this worker's unpaid recorded work")
    payment = LaborWagePayment(project_id=project.id, worker_id=worker.id, payment_date=payload.payment_date, amount=payload.amount, payment_mode=payload.payment_mode, reference=payload.reference, comment=payload.comment, recorded_by_id=user.id)
    db.add(payment)
    await db.flush()
    await add_audit(db, user, "labor_wage_payment_recorded", "LaborWagePayment", payment.id)
    await db.commit()
    return {"id": str(payment.id), "worker_id": str(worker.id), "worker_name": worker.name, "payment_date": payment.payment_date.isoformat(), "amount": money(payment.amount), "payment_mode": payment.payment_mode, "reference": payment.reference, "comment": payment.comment}
