import argparse
import asyncio
import json
from uuid import UUID

from sqlalchemy import func, select, text

from app.db import engine
from app.models import BillingEntry, Contract, InventoryTransaction, Project, ProjectDocument, ProjectStatusHistory, ProjectValueHistory, PurchaseOrder, PurchaseOrderLine, PurchaseOrderPayment, Timecard


async def verify(project_id: UUID | None) -> None:
    models = [Project, Contract, PurchaseOrder, PurchaseOrderLine, PurchaseOrderPayment,
              InventoryTransaction, Timecard, BillingEntry, ProjectDocument, ProjectStatusHistory, ProjectValueHistory]
    async with engine.connect() as connection:
        await connection.execute(text("SET TRANSACTION READ ONLY"))
        database = await connection.scalar(text("SELECT current_database()"))
        print(json.dumps({"database": database, "storage": "PostgreSQL", "read_only": True}))
        for model in models:
            query = select(func.count()).select_from(model)
            if project_id:
                if model is Project:
                    query = query.where(Project.id == project_id)
                elif hasattr(model, "project_id"):
                    query = query.where(model.project_id == project_id)
                else:
                    query = query.join(PurchaseOrder, PurchaseOrder.id == model.purchase_order_id).where(PurchaseOrder.project_id == project_id)
            count = await connection.scalar(query)
            print(json.dumps({"table": model.__tablename__, "rows": count}))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read-only PostgreSQL transaction verification")
    parser.add_argument("--project-id", type=UUID)
    asyncio.run(verify(parser.parse_args().project_id))