from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuditEvent, LaborProgressClaim, LaborWorkEntry, PROJECT_STATUS_TRANSITIONS, Project, PurchaseOrder, PurchaseOrderLine, User


def money(value: Decimal | int | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.01")))


def user_dto(user: User) -> dict:
    return {"id": str(user.id), "username": user.username, "email": user.email, "phone": user.phone, "name": user.name, "global_access": user.global_access, "global_permissions": user.global_permissions, "users_permissions": user.users_permissions, "audit_permissions": user.audit_permissions, "active": user.active}


def project_dto(project: Project) -> dict:
    return {
        "id": str(project.id), "name": project.name, "location": project.location, "status": project.status,
        "eligible_statuses": list(PROJECT_STATUS_TRANSITIONS.get(project.status, ())),
        "baseline_budget": money(project.baseline_budget), "currency": project.currency,
        "start_date": project.start_date.isoformat(), "estimated_end_date": project.estimated_end_date.isoformat() if project.estimated_end_date else None,
        "version": project.version,
    }


def order_totals(order: PurchaseOrder) -> tuple[Decimal, Decimal, Decimal]:
    total = sum((line.quantity * line.unit_price for line in order.lines), Decimal("0"))
    paid = sum((payment.amount for payment in order.payments), Decimal("0"))
    return total, paid, max(Decimal("0"), total - paid)


def payment_status(total: Decimal, paid: Decimal, balance: Decimal) -> str:
    if paid <= 0:
        return "Pending"
    if balance > 0 or paid < total:
        return "Partially paid"
    return "Paid"


def dashboard_cost_summary(labor_cost: Decimal, orders: list[PurchaseOrder], direct_work: list[LaborWorkEntry] | None = None, contract_claims: list[LaborProgressClaim] | None = None) -> dict:
    material_cost = sum((order_totals(order)[0] for order in orders), Decimal("0"))
    monthly_costs: dict[str, Decimal] = {}
    for order in orders:
        month = order.order_date.strftime("%Y-%m")
        monthly_costs[month] = monthly_costs.get(month, Decimal("0")) + order_totals(order)[0]
    for entry in direct_work or []:
        month = entry.work_date.strftime("%Y-%m")
        monthly_costs[month] = monthly_costs.get(month, Decimal("0")) + entry.quantity * entry.rate
    for claim in contract_claims or []:
        month = claim.period_end.strftime("%Y-%m")
        monthly_costs[month] = monthly_costs.get(month, Decimal("0")) + claim.amount
    actual_cost = labor_cost + material_cost
    return {
        "actual_cost": actual_cost,
        "labor_cost": labor_cost,
        "material_cost": material_cost,
        "monthly_costs": [{"month": month, "amount": amount} for month, amount in sorted(monthly_costs.items())],
    }


def order_dto(order: PurchaseOrder, detail: bool = False) -> dict:
    total, paid, balance = order_totals(order)
    items = [line.item.name for line in order.lines]
    dto = {
        "id": str(order.id), "number": order.number, "order_date": order.order_date.isoformat(),
        "vendor": {"id": str(order.vendor.id), "name": order.vendor.name}, "item_names": items,
        "currency": order.currency, "total": money(total), "paid_to_date": money(paid), "balance": money(balance),
        "payment_status": payment_status(total, paid, balance),
        "approval_status": order.approval_status, "version": order.version,
        "can_edit": balance > 0, "can_add_payment": balance > 0, "can_view_history": True,
        "image": ({"filename": order.image_filename, "available": True,
                   "url": f"/api/v1/projects/{order.project_id}/purchase-orders/{order.id}/image"}
                  if order.image_storage_name else None),
    }
    if detail:
        dto["lines"] = [{
            "id": str(line.id), "item": {"id": str(line.item.id), "sku": line.item.sku, "name": line.item.name,
                                          "category": line.item.category, "unit_of_measure": line.item.unit_of_measure,
                                          "classification": line.item.classification},
            "description": line.description, "quantity": str(line.quantity), "unit_price": money(line.unit_price),
            "line_total": money(line.quantity * line.unit_price), "accepted_quantity": "0", "open_quantity": str(line.quantity),
            "cost_code": None,
        } for line in order.lines]
        dto["created_at"] = order.created_at.isoformat() if order.created_at else None
        dto["updated_at"] = order.updated_at.isoformat() if order.updated_at else None
    return dto


def purchase_order_query():
    return select(PurchaseOrder).options(
        selectinload(PurchaseOrder.vendor),
        selectinload(PurchaseOrder.lines).selectinload(PurchaseOrderLine.item),
        selectinload(PurchaseOrder.payments),
    )


async def add_audit(db: AsyncSession, user: User, action: str, entity: str, entity_id: UUID, details: dict | None = None, project_id: UUID | None = None) -> None:
    if project_id is None and entity != "User":
        from app import models

        model = getattr(models, entity, None)
        if entity == "Project":
            project_id = entity_id
        elif model is not None and hasattr(model, "project_id"):
            project_id = await db.scalar(select(model.project_id).where(model.id == entity_id))
    db.add(AuditEvent(actor_id=user.id, action=action, entity_type=entity, entity_id=entity_id, project_id=project_id, details=details))