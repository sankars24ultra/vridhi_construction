from sqlalchemy import func, select

from app.core.config import settings
from app.db import SessionLocal
from app.models import User
from argon2 import extract_parameters

RBAC_RESOURCES = {
    "overview": ("Overview", "Project overview and financial summaries"),
    "procurement": ("Procurement", "Purchase orders and vendor payments"),
    "inventory": ("Inventory", "Site stock and inventory movements"),
    "cashflow": ("Cashflow", "Client billing and receipts"),
    "users": ("Users", "User directory and role permissions"),
    "labor": ("Labor and Wages", "Subcontract labor and individual worker records"),
}
async def seed_local_data() -> None:
    async with SessionLocal() as db:
        if await db.scalar(select(func.count(User.id))):
            return
        global_profile = {
            resource: {"access": "allow", "read": {"export_report": True}, "write": {"mode": "all", "actions": {}}}
            for resource in RBAC_RESOURCES
        }
        extract_parameters(settings.initial_password_hash)
        owner = User(username="administrator", email=None, name="Administrator", role="User", global_access=True, global_permissions=global_profile, password_hash=settings.initial_password_hash)
        db.add(owner)
        await db.commit()
