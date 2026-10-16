import secrets
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.core.config import settings
from app.db import SessionLocal
from app.models import BillingEntry, Contract, CostCode, InventoryItem, Project, ProjectMembership, PurchaseOrder, PurchaseOrderLine, PurchaseOrderPayment, Timecard, User, Vendor
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
        await db.flush()
        vendors = [Vendor(name=name) for name in ["Lone Star Supply", "Summit Concrete Co.", "Metro Electric", "ProBuild Rentals", "Central Steelworks"]]
        db.add_all(vendors)
        await db.flush()
        samples = [
            ("Cedar Ridge Plaza", "Austin, Texas", "Active", 2450000, 3180000, "2025-03-12"),
            ("Northline Bridge", "Round Rock, Texas", "Active", 5680000, 7400000, "2025-02-18"),
            ("Juniper Residences", "Georgetown, Texas", "Active", 3920000, 5150000, "2025-04-02"),
            ("Riverfront Logistics Hub", "Chennai, India", "Planning", 18500000, 22800000, "2026-02-01"),
            ("Eastfield Public School", "Jaipur, India", "Planning", 9200000, 11500000, "2026-03-15"),
            ("Meadowbrook Health Clinic", "Kochi, India", "Planning", 12800000, 15600000, "2026-03-25"),
            ("Orchid Cold Storage", "Nashik, India", "Planning", 7600000, 9400000, "2026-04-10"),
            ("Suncrest Solar Park", "Bikaner, India", "Active", 34200000, 41800000, "2025-11-01"),
            ("Westgate Transit Terminal", "Surat, India", "Active", 27600000, 33500000, "2025-09-10"),
            ("Parkview Office Tower", "Hyderabad, India", "Active", 48900000, 59200000, "2025-08-01"),
            ("Lakeview Water Treatment Plant", "Mysuru, India", "Active", 21400000, 26300000, "2025-12-12"),
            ("Harborfront Apartments", "Visakhapatnam, India", "On Hold", 16400000, 20100000, "2025-06-20"),
            ("Old Town Market Hall", "Lucknow, India", "On Hold", 8700000, 10800000, "2025-07-01"),
            ("Central District Library", "Indore, India", "Completed", 6400000, 7800000, "2024-09-01"),
            ("Greenline Bus Depot", "Pune, India", "Completed", 11200000, 13700000, "2024-08-15"),
        ]
        projects: list[Project] = []
        for name, location, state, budget, contract_value, start in samples:
            project = Project(name=name, location=location, status=state, baseline_budget=Decimal(budget), currency="INR", start_date=date.fromisoformat(start), created_by_id=owner.id)
            project.memberships.append(ProjectMembership(user=owner))
            project.contracts.append(Contract(number=f"VC-{secrets.token_hex(4).upper()}", original_value=Decimal(contract_value), currency="INR"))
            projects.append(project)
        db.add_all(projects)
        items = [
            InventoryItem(sku="MAT-CEMENT", name="Cement", category="Concrete", unit_of_measure="bags"),
            InventoryItem(sku="MAT-BRICK", name="Bricks", category="Masonry", unit_of_measure="each"),
            InventoryItem(sku="MAT-PIPE", name="Pipes", category="Plumbing", unit_of_measure="length"),
            InventoryItem(sku="MAT-REBAR", name="Rebar #5", category="Steel products", unit_of_measure="kg"),
        ]
        codes = ["Concrete", "Masonry", "Electrical", "Sitework", "Plumbing"]
        db.add_all(items + [CostCode(code=code.upper().replace(" ", "-"), name=code) for code in codes])
        await db.flush()
        db.add_all([
            PurchaseOrder(number=f"PO-{secrets.randbelow(9000) + 1000}", project=projects[0], vendor=vendors[index % len(vendors)], order_date=date(2026, 10, day), currency="INR", approval_status="Approved", created_by_id=owner.id,
                          lines=[PurchaseOrderLine(item=items[item_index % len(items)], description=items[item_index % len(items)].name,
                                                   quantity=Decimal(quantity), unit_price=Decimal(unit_price))],
                          payments=[PurchaseOrderPayment(amount=Decimal(paid), payment_date=date(2026, 10, day), recorded_by_id=owner.id)] if paid else [])
            for index, (day, item_index, quantity, unit_price, paid) in enumerate([
                (5, 2, "10", "100", "1000"), (4, 0, "20", "320", "6400"), (1, 0, "100", "220", "20000"),
                (1, 1, "1000", "12", "0"),
            ])
        ])
        db.add_all([
            BillingEntry(project_id=projects[0].id, application_number="PB-001", description="Foundation and mobilization", submitted_date=date(2026, 9, 1), amount=Decimal("284000"), status="Submitted"),
            Timecard(project=projects[0], employee_name="Jordan Lee", cost_code="Concrete", work_date=date.today(), regular_hours=Decimal("8"), hourly_rate=Decimal("34"), status="Approved", created_by_id=owner.id),
        ])
        await db.commit()
