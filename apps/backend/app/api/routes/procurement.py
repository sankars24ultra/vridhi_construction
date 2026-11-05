import hashlib
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_db
from app.models import IdempotencyRecord, InventoryItem, InventoryTransaction, Project, ProjectInventoryItem, PurchaseOrder, PurchaseOrderLine, PurchaseOrderPayment, User, Vendor
from app.schemas import InventoryTransactionCreate, PaymentCreate, PurchaseOrderCreate
from app.security import current_user, require_csrf, require_permission, require_project_access
from app.services.common import add_audit, money, order_dto, order_totals, purchase_order_query
from app.services.procurement import resolve_line_item

router = APIRouter()


@router.get("/api/v1/projects/{project_id}/purchase-orders", dependencies=[Depends(require_permission("procurement", "read"))])
async def list_purchase_orders(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), search: str | None = None, project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db), payment_status: str | None = None) -> dict:
    filters = [PurchaseOrder.project_id == project.id]
    if payment_status in {"Paid", "Partially paid", "Pending"}:
        ordered_total = select(func.coalesce(func.sum(PurchaseOrderLine.quantity * PurchaseOrderLine.unit_price), 0)).where(PurchaseOrderLine.purchase_order_id == PurchaseOrder.id).scalar_subquery()
        paid_total = select(func.coalesce(func.sum(PurchaseOrderPayment.amount), 0)).where(PurchaseOrderPayment.purchase_order_id == PurchaseOrder.id).scalar_subquery()
        if payment_status == "Paid":
            filters.extend([paid_total > 0, paid_total >= ordered_total])
        elif payment_status == "Partially paid":
            filters.extend([paid_total > 0, paid_total < ordered_total])
        else:
            filters.append(paid_total == 0)
    if search and search.strip():
        term = search.strip()
        filters.append(or_(PurchaseOrder.number.icontains(term, autoescape=True),
                           PurchaseOrder.vendor.has(Vendor.name.icontains(term, autoescape=True)),
                           PurchaseOrder.lines.any(PurchaseOrderLine.item.has(InventoryItem.name.icontains(term, autoescape=True)))))
    query = purchase_order_query().where(*filters).order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc())
    orders = list((await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).unique().all())
    total = await db.scalar(select(func.count(PurchaseOrder.id)).where(*filters)) or 0
    return {"items": [order_dto(order) for order in orders], "page": page, "page_size": page_size, "total": total}


@router.get("/api/v1/projects/{project_id}/procurement-summary", dependencies=[Depends(require_permission("procurement", "read"))])
async def procurement_summary(project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    orders = list((await db.scalars(purchase_order_query().where(PurchaseOrder.project_id == project.id))).unique().all())
    total, paid, balance = (sum((order_totals(order)[i] for order in orders), Decimal("0")) for i in range(3))
    return {"order_count": len(orders), "currency": project.currency, "total_ordered": money(total), "total_paid": money(paid), "outstanding_balance": money(balance), "as_of": datetime.now(timezone.utc).isoformat()}


@router.post("/api/v1/projects/{project_id}/purchase-orders", status_code=201, dependencies=[Depends(require_csrf), Depends(require_permission("procurement", "write"))])
async def create_purchase_order(request: Request, project: Project = Depends(require_project_access), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    image = None
    if isinstance(request, PurchaseOrderCreate):
        payload = request
    elif request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form(max_files=1, max_fields=1, max_part_size=settings.upload_max_bytes)
        payload_value = form.get("payload")
        image = form.get("image")
        if not isinstance(payload_value, str):
            raise HTTPException(status_code=422, detail="Purchase order details are required")
        try:
            payload = PurchaseOrderCreate.model_validate_json(payload_value)
        except Exception as error:
            raise HTTPException(status_code=422, detail="Invalid purchase order details") from error
        if image is not None and (not hasattr(image, "filename") or not image.filename):
            image = None
    else:
        try:
            payload = PurchaseOrderCreate.model_validate(await request.json())
        except Exception as error:
            raise HTTPException(status_code=422, detail="Invalid purchase order details") from error

    image_content = None
    image_suffix = None
    image_content_type = None
    image_filename = None
    if image is not None:
        image_filename = Path(image.filename).name
        image_suffix = Path(image_filename).suffix.lower()
        image_types = {".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
                       ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
                       ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
                       ".webp": ("image/webp", b"RIFF")}
        if image_suffix not in image_types or image.content_type not in {image_types[image_suffix][0], "application/octet-stream", None}:
            raise HTTPException(status_code=415, detail="Choose a PNG, JPG, or WEBP image with a matching file type")
        image_content = await image.read(settings.upload_max_bytes + 1)
        if not image_content:
            raise HTTPException(status_code=422, detail="Purchase order image is empty")
        if len(image_content) > settings.upload_max_bytes:
            raise HTTPException(status_code=413, detail="Purchase order image exceeds the 10 MB upload limit")
        signature = image_types[image_suffix][1]
        if not image_content.startswith(signature) or (image_suffix == ".webp" and image_content[8:12] != b"WEBP"):
            raise HTTPException(status_code=415, detail="Uploaded content does not match its image type")
        image_content_type = image_types[image_suffix][0]

    total_price = sum((line.quantity * line.unit_price for line in payload.lines), Decimal("0")).quantize(Decimal("0.01"))
    if payload.paid_amount > total_price:
        raise HTTPException(status_code=422, detail="Paid amount cannot exceed the total purchase price")
    vendor = await db.get(Vendor, payload.vendor_id) if payload.vendor_id else None
    if vendor is None and payload.vendor_name and payload.vendor_name.strip():
        vendor = await db.scalar(select(Vendor).where(func.lower(Vendor.name) == payload.vendor_name.strip().lower()))
        if vendor is None:
            vendor = Vendor(name=payload.vendor_name.strip(), active=True)
            db.add(vendor)
            await db.flush()
    if not vendor or not vendor.active:
        raise HTTPException(status_code=422, detail="Select an active vendor")
    order = PurchaseOrder(number=f"PO-{secrets.randbelow(900000) + 100000}", project_id=project.id, vendor_id=vendor.id,
                         order_date=payload.order_date, currency=project.currency, approval_status="Approved", created_by_id=user.id, payments=[])
    image_path = None
    if image_content is not None:
        order.image_storage_name = f"{secrets.token_hex(24)}{image_suffix}"
        order.image_filename = image_filename
        order.image_content_type = image_content_type
        order.image_byte_size = len(image_content)
        image_path = settings.upload_directory / order.image_storage_name
    for line_input in payload.lines:
        item = await resolve_line_item(db, line_input)
        order.lines.append(PurchaseOrderLine(item=item, description=line_input.description, quantity=line_input.quantity, unit_price=line_input.unit_price))
        link = await db.scalar(select(ProjectInventoryItem).where(ProjectInventoryItem.project_id == project.id, ProjectInventoryItem.item_id == item.id))
        if not link:
            db.add(ProjectInventoryItem(project_id=project.id, item_id=item.id))
    db.add(order)
    if payload.paid_amount > 0:
        order.payments.append(PurchaseOrderPayment(amount=payload.paid_amount, payment_date=payload.order_date,
                              payment_mode=payload.payment_mode, comment=payload.payment_comment, recorded_by_id=user.id))
    await db.flush()
    await add_audit(db, user, "purchase_order_created", "PurchaseOrder", order.id)
    try:
        if image_path:
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(image_content)
        await db.commit()
    except Exception:
        await db.rollback()
        if image_path:
            image_path.unlink(missing_ok=True)
        raise
    order = await db.scalar(purchase_order_query().where(PurchaseOrder.id == order.id).execution_options(populate_existing=True))
    return order_dto(order, detail=True)


@router.get("/api/v1/projects/{project_id}/purchase-orders/{po_id}/image", dependencies=[Depends(require_permission("procurement", "read"))])
async def purchase_order_image(project_id: UUID, po_id: UUID, project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> FileResponse:
    order = await db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == po_id, PurchaseOrder.project_id == project.id))
    if not order or not order.image_storage_name or not order.image_content_type or not order.image_filename:
        raise HTTPException(status_code=404, detail="Purchase order image not found")
    directory = settings.upload_directory.resolve()
    path = (directory / order.image_storage_name).resolve()
    if path.parent != directory or not path.is_file():
        raise HTTPException(status_code=404, detail="Purchase order image unavailable")
    return FileResponse(path, media_type=order.image_content_type, filename=order.image_filename, content_disposition_type="inline")


@router.get("/api/v1/projects/{project_id}/purchase-orders/{po_id}", dependencies=[Depends(require_permission("procurement", "read"))])
async def purchase_order_detail(project_id: UUID, po_id: UUID, project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    order = await db.scalar(purchase_order_query().where(PurchaseOrder.id == po_id, PurchaseOrder.project_id == project.id))
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return order_dto(order, detail=True)


@router.patch("/api/v1/projects/{project_id}/purchase-orders/{po_id}", dependencies=[Depends(require_csrf), Depends(require_permission("procurement", "write"))])
async def update_purchase_order(project_id: UUID, po_id: UUID, payload: PurchaseOrderCreate, expected_version: int = Query(...), project: Project = Depends(require_project_access), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if payload.paid_amount > 0:
        raise HTTPException(status_code=422, detail="Record additional payments through Add payment")
    order = await db.scalar(purchase_order_query().where(PurchaseOrder.id == po_id, PurchaseOrder.project_id == project.id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if order.version != expected_version:
        raise HTTPException(status_code=409, detail="Purchase order changed. Refresh and try again.")
    vendor = await db.get(Vendor, payload.vendor_id) if payload.vendor_id else None
    if vendor is None and payload.vendor_name and payload.vendor_name.strip():
        vendor = await db.scalar(select(Vendor).where(func.lower(Vendor.name) == payload.vendor_name.strip().lower()))
        if vendor is None:
            vendor = Vendor(name=payload.vendor_name.strip(), active=True)
            db.add(vendor)
            await db.flush()
    if not vendor or not vendor.active:
        raise HTTPException(status_code=422, detail="Enter an active vendor name")
    order.vendor = vendor
    total, paid, balance = order_totals(order)
    if balance == 0:
        raise HTTPException(status_code=409, detail="Fully paid purchase orders cannot be edited")
    next_total = sum((line.quantity * line.unit_price for line in payload.lines), Decimal("0"))
    if next_total < paid:
        raise HTTPException(status_code=409, detail="Purchase order total cannot be lower than paid-to-date")
    order.vendor = vendor
    order.order_date = payload.order_date
    order.lines.clear()
    for line_input in payload.lines:
        item = await resolve_line_item(db, line_input)
        order.lines.append(PurchaseOrderLine(item=item, description=line_input.description, quantity=line_input.quantity, unit_price=line_input.unit_price))
        if not await db.scalar(select(ProjectInventoryItem.id).where(ProjectInventoryItem.project_id == project.id, ProjectInventoryItem.item_id == item.id)):
            db.add(ProjectInventoryItem(project_id=project.id, item_id=item.id))
    order.version += 1
    await add_audit(db, user, "purchase_order_updated", "PurchaseOrder", order.id)
    await db.commit()
    return order_dto(order, detail=True)


@router.post("/api/v1/projects/{project_id}/purchase-orders/{po_id}/payments", status_code=201, dependencies=[Depends(require_csrf), Depends(require_permission("procurement", "write"))])
async def add_payment(project_id: UUID, po_id: UUID, payload: PaymentCreate, idempotency_key: str = Header(..., alias="Idempotency-Key"), project: Project = Depends(require_project_access), user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    if len(idempotency_key) > 160:
        raise HTTPException(status_code=422, detail="Idempotency-Key is too long")
    request_hash = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    previous_request = await db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.actor_id == user.id, IdempotencyRecord.key == idempotency_key).with_for_update())
    if previous_request:
        if previous_request.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency-Key was already used with a different request")
        return previous_request.response_body
    order = await db.scalar(purchase_order_query().where(PurchaseOrder.id == po_id, PurchaseOrder.project_id == project.id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    total, paid, balance = order_totals(order)
    if payload.amount > balance:
        raise HTTPException(status_code=409, detail="Payment exceeds outstanding balance")
    payment = PurchaseOrderPayment(purchase_order_id=order.id, amount=payload.amount, payment_date=payload.payment_date,
                                   payment_mode=payload.payment_mode, reference=payload.reference, comment=payload.comment, recorded_by_id=user.id)
    order.payments.append(payment)
    order.version += 1
    await add_audit(db, user, "purchase_order_payment_recorded", "PurchaseOrder", order.id)
    await db.flush()
    result = {"payment": {"id": str(payment.id), "amount": money(payment.amount), "payment_date": payment.payment_date.isoformat(), "payment_mode": payment.payment_mode, "reference": payment.reference, "comment": payment.comment, "recorded_at": payment.recorded_at.isoformat(), "recorded_by": {"id": str(user.id), "name": user.name}, "receipt": None}, "purchase_order": order_dto(order)}
    db.add(IdempotencyRecord(actor_id=user.id, key=idempotency_key, request_hash=request_hash, response_body=result))
    await db.commit()
    return result


@router.get("/api/v1/projects/{project_id}/purchase-orders/{po_id}/payments", dependencies=[Depends(require_permission("procurement", "read"))])
async def list_payments(project_id: UUID, po_id: UUID, page: int = 1, page_size: int = Query(25, ge=1, le=100), project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    order = await db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == po_id, PurchaseOrder.project_id == project.id))
    if not order:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    query = select(PurchaseOrderPayment, User).join(User, User.id == PurchaseOrderPayment.recorded_by_id).where(PurchaseOrderPayment.purchase_order_id == po_id).order_by(PurchaseOrderPayment.payment_date.desc(), PurchaseOrderPayment.recorded_at.desc(), PurchaseOrderPayment.id.desc())
    rows = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).all()
    total = await db.scalar(select(func.count(PurchaseOrderPayment.id)).where(PurchaseOrderPayment.purchase_order_id == po_id)) or 0
    return {"items": [{"id": str(payment.id), "amount": money(payment.amount), "payment_date": payment.payment_date.isoformat(), "payment_mode": payment.payment_mode, "reference": payment.reference, "comment": payment.comment, "recorded_at": payment.recorded_at.isoformat(), "recorded_by": {"id": str(actor.id), "name": actor.name}, "reversal_of_id": None, "receipt": None} for payment, actor in rows], "page": page, "page_size": page_size, "total": total}


@router.get("/api/v1/vendors", dependencies=[Depends(require_permission("procurement", "read"))])
async def list_vendors(search: str | None = None, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)) -> dict:
    query = select(Vendor).where(Vendor.active.is_(True)).order_by(Vendor.name)
    if search:
        query = query.where(Vendor.name.ilike(f"%{search.strip()}%"))
    items = list((await db.scalars(query.limit(100))).all())
    return {"items": [{"id": str(item.id), "name": item.name, "active": item.active} for item in items], "page": 1, "page_size": 100, "total": len(items)}


@router.get("/api/v1/inventory-items")
async def list_inventory_items(search: str | None = None, db: AsyncSession = Depends(get_db), user: User = Depends(current_user)) -> dict:
    query = select(InventoryItem).order_by(InventoryItem.name)
    if search:
        query = query.where(InventoryItem.name.ilike(f"%{search.strip()}%"))
    items = list((await db.scalars(query.limit(100))).all())
    return {"items": [{"id": str(item.id), "sku": item.sku, "name": item.name, "category": item.category, "unit_of_measure": item.unit_of_measure, "classification": item.classification} for item in items], "page": 1, "page_size": 100, "total": len(items)}


@router.get("/api/v1/cost-codes", dependencies=[Depends(require_permission("procurement", "read"))])
async def list_cost_codes(db: AsyncSession = Depends(get_db), user: User = Depends(current_user)) -> dict:
    from app.models import CostCode
    items = list((await db.scalars(select(CostCode).where(CostCode.active.is_(True)).order_by(CostCode.name))).all())
    return {"items": [{"id": str(item.id), "code": item.code, "name": item.name, "category": "Project"} for item in items], "page": 1, "page_size": len(items) or 1, "total": len(items)}


@router.get("/api/v1/projects/{project_id}/inventory", dependencies=[Depends(require_permission("inventory", "read"))])
async def project_inventory(project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    links = list((await db.scalars(select(ProjectInventoryItem).where(ProjectInventoryItem.project_id == project.id).order_by(ProjectInventoryItem.created_at.desc(), ProjectInventoryItem.id.desc()))).all())
    items: list[dict] = []
    for link in links:
        item = await db.get(InventoryItem, link.item_id)
        if not item:
            continue
        order_lines = list((await db.scalars(
            select(PurchaseOrderLine)
            .join(PurchaseOrder)
            .where(PurchaseOrder.project_id == project.id, PurchaseOrderLine.item_id == item.id)
        )).all())
        po_ids = list({line.purchase_order_id for line in order_lines})
        vendor_names: list[str] = []
        if po_ids:
            pos = list((await db.scalars(
                select(PurchaseOrder)
                .where(PurchaseOrder.id.in_(po_ids))
            )).all())
            vendor_ids = list({po.vendor_id for po in pos if po.vendor_id})
            if vendor_ids:
                vendors = list((await db.scalars(
                    select(Vendor)
                    .where(Vendor.id.in_(vendor_ids))
                )).all())
                vendor_names = sorted(list({v.name for v in vendors if v.name}))

        transactions = list((await db.scalars(select(InventoryTransaction).where(InventoryTransaction.project_id == project.id, InventoryTransaction.item_id == item.id))).all())
        ordered = sum((line.quantity for line in order_lines), Decimal("0"))
        received = sum((entry.quantity for entry in transactions if entry.transaction_type == "receipt"), Decimal("0"))
        consumed = sum((entry.quantity for entry in transactions if entry.transaction_type in {"issue", "allocation"}), Decimal("0"))
        available = max(Decimal("0"), received - consumed)
        
        # Calculate approximate unit cost from orders or receipt transactions
        unit_cost = Decimal("0")
        if order_lines and ordered > 0:
            unit_cost = sum((l.quantity * l.unit_price for l in order_lines), Decimal("0")) / ordered
        else:
            receipts = [t for t in transactions if t.transaction_type == "receipt" and t.unit_cost > 0]
            if receipts:
                unit_cost = sum((t.quantity * t.unit_cost for t in receipts), Decimal("0")) / sum((t.quantity for t in receipts), Decimal("1"))

        items.append({
            "item": {
                "id": str(item.id),
                "sku": item.sku,
                "name": item.name,
                "category": item.category,
                "unit_of_measure": item.unit_of_measure,
                "classification": item.classification
            },
            "vendor_name": ", ".join(vendor_names) if vendor_names else "—",
            "vendor_names": vendor_names,
            "ordered_quantity": str(ordered),
            "open_order_quantity": str(max(Decimal("0"), ordered - received)),
            "received_quantity": str(received),
            "consumed_quantity": str(consumed),
            "available_quantity": str(available),
            "unit_cost": money(unit_cost),
            "valuation": money(available * unit_cost),
            "location_id": None,
            "as_of": datetime.now(timezone.utc).isoformat()
        })
    return {"items": items, "page": 1, "page_size": len(items) or 1, "total": len(items)}


@router.get("/api/v1/projects/{project_id}/inventory-summary", dependencies=[Depends(require_permission("inventory", "read"))])
async def inventory_summary(project: Project = Depends(require_project_access), db: AsyncSession = Depends(get_db)) -> dict:
    stock = await project_inventory(project, db)
    rows = stock["items"]
    total_val = sum((Decimal(item["valuation"]) for item in rows), Decimal("0"))
    low_stock = sum(1 for item in rows if 0 < Decimal(item["available_quantity"]) <= Decimal("15"))
    out_of_stock = sum(1 for item in rows if Decimal(item["available_quantity"]) == 0 and Decimal(item["received_quantity"]) > 0)
    return {
        "catalog_item_count": len(rows),
        "stocked_item_count": sum(1 for item in rows if Decimal(item["available_quantity"]) > 0),
        "total_received_units": str(sum((Decimal(item["received_quantity"]) for item in rows), Decimal("0"))),
        "total_consumed_units": str(sum((Decimal(item["consumed_quantity"]) for item in rows), Decimal("0"))),
        "total_available_units": str(sum((Decimal(item["available_quantity"]) for item in rows), Decimal("0"))),
        "low_stock_count": low_stock,
        "out_of_stock_count": out_of_stock,
        "valuation_amount": money(total_val),
        "currency": project.currency,
        "as_of": datetime.now(timezone.utc).isoformat()
    }


@router.post("/api/v1/projects/{project_id}/inventory/transactions", status_code=201, dependencies=[Depends(require_csrf), Depends(require_permission("inventory", "write"))])
async def record_inventory_transaction(
    payload: InventoryTransactionCreate,
    project: Project = Depends(require_project_access),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    item = await db.get(InventoryItem, payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Ensure item link exists in the project
    link = await db.scalar(select(ProjectInventoryItem).where(
        ProjectInventoryItem.project_id == project.id,
        ProjectInventoryItem.item_id == item.id
    ))
    if not link:
        db.add(ProjectInventoryItem(project_id=project.id, item_id=item.id))

    # For issues/consumption, validate available stock
    if payload.transaction_type in ("issue", "allocation"):
        transactions = list((await db.scalars(
            select(InventoryTransaction).where(
                InventoryTransaction.project_id == project.id,
                InventoryTransaction.item_id == item.id
            )
        )).all())
        received = sum((t.quantity for t in transactions if t.transaction_type == "receipt"), Decimal("0"))
        consumed = sum((t.quantity for t in transactions if t.transaction_type in ("issue", "allocation")), Decimal("0"))
        available = max(Decimal("0"), received - consumed)
        if payload.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Usage quantity ({payload.quantity} {item.unit_of_measure}) exceeds current available stock ({available} {item.unit_of_measure})"
            )

    occurred_dt = datetime.combine(payload.transaction_date, datetime.min.time(), tzinfo=timezone.utc)
    tx = InventoryTransaction(
        project_id=project.id,
        item_id=payload.item_id,
        purchase_order_line_id=payload.purchase_order_line_id,
        transaction_type=payload.transaction_type,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        reference=payload.reference,
        notes=payload.notes,
        recorded_by_id=user.id,
        occurred_at=occurred_dt
    )
    db.add(tx)
    await db.flush()
    await add_audit(db, user, f"inventory_{payload.transaction_type}_recorded", "InventoryTransaction", tx.id)
    await db.commit()
    return {
        "id": str(tx.id),
        "item_id": str(tx.item_id),
        "transaction_type": tx.transaction_type,
        "quantity": str(tx.quantity),
        "unit_cost": str(tx.unit_cost),
        "reference": tx.reference,
        "notes": tx.notes,
        "occurred_at": tx.occurred_at.isoformat()
    }


@router.get("/api/v1/projects/{project_id}/inventory/transactions", dependencies=[Depends(require_permission("inventory", "read"))])
async def list_inventory_transactions(
    item_id: UUID | None = None,
    project: Project = Depends(require_project_access),
    db: AsyncSession = Depends(get_db)
) -> dict:
    query = select(InventoryTransaction).where(InventoryTransaction.project_id == project.id)
    if item_id:
        query = query.where(InventoryTransaction.item_id == item_id)
    query = query.order_by(InventoryTransaction.occurred_at.desc(), InventoryTransaction.id.desc())
    txs = list((await db.scalars(query)).all())

    items = {item.id: item for item in (await db.scalars(select(InventoryItem).where(InventoryItem.id.in_([t.item_id for t in txs])))).all()} if txs else {}
    users = {user.id: user for user in (await db.scalars(select(User).where(User.id.in_([t.recorded_by_id for t in txs if t.recorded_by_id])))).all()} if txs else {}
    po_lines = {line.id: line for line in (await db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.id.in_([t.purchase_order_line_id for t in txs if t.purchase_order_line_id])))).all()} if txs else {}
    pos = {po.id: po for po in (await db.scalars(select(PurchaseOrder).where(PurchaseOrder.id.in_([l.purchase_order_id for l in po_lines.values()])))).all()} if po_lines else {}

    result = []
    for t in txs:
        itm = items.get(t.item_id)
        po_line = po_lines.get(t.purchase_order_line_id)
        po = pos.get(po_line.purchase_order_id) if po_line else None
        result.append({
            "id": str(t.id),
            "item_id": str(t.item_id),
            "item_name": itm.name if itm else "Unknown",
            "sku": itm.sku if itm else "",
            "unit_of_measure": itm.unit_of_measure if itm else "",
            "category": itm.category if itm else "",
            "transaction_type": t.transaction_type,
            "quantity": str(t.quantity),
            "unit_cost": str(t.unit_cost),
            "reference": t.reference,
            "notes": t.notes,
            "po_number": po.number if po else None,
            "recorded_by": users[t.recorded_by_id].name if t.recorded_by_id in users else "System",
            "occurred_at": t.occurred_at.isoformat()
        })
    return {"items": result, "total": len(result)}
