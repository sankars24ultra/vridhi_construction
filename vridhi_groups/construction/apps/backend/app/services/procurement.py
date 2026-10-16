import secrets

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InventoryItem


async def resolve_line_item(db: AsyncSession, line_input) -> InventoryItem:
    item = await db.get(InventoryItem, line_input.item_id) if line_input.item_id else None
    if item:
        return item
    if not line_input.item_name:
        raise HTTPException(status_code=422, detail="Select an existing item or provide item_name")
    item = await db.scalar(select(InventoryItem).where(InventoryItem.name.ilike(line_input.item_name.strip())))
    if item is None:
        sku = (line_input.sku or f"MAT-{secrets.token_hex(4)}").upper()
        item = InventoryItem(sku=sku, name=line_input.item_name.strip(), category=line_input.category, unit_of_measure=line_input.unit_of_measure)
        db.add(item)
        await db.flush()
    return item