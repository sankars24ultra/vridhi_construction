import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.procurement import record_inventory_transaction
from app.models import InventoryItem, InventoryTransaction, Project, User
from app.schemas import InventoryTransactionCreate


def test_inventory_usage_rejects_exceeding_available_stock():
    project = Project(id=uuid4())
    user = User(id=uuid4())
    item = InventoryItem(id=uuid4(), sku="MAT-CEMENT", name="Cement", category="Concrete", unit_of_measure="bags")

    # Mock transactions: 20 received, 15 consumed => 5 available
    tx_receipt = InventoryTransaction(transaction_type="receipt", quantity=Decimal("20"))
    tx_issue = InventoryTransaction(transaction_type="issue", quantity=Decimal("15"))

    db = MagicMock()
    db.get = AsyncMock(return_value=item)
    db.scalar = AsyncMock(return_value=True)  # link exists
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[tx_receipt, tx_issue])
    db.scalars = AsyncMock(return_value=mock_scalars)

    # Trying to use 10 bags when only 5 are available
    payload = InventoryTransactionCreate(
        item_id=item.id,
        transaction_type="issue",
        quantity=Decimal("10"),
        transaction_date=date(2026, 10, 12),
        reference="2nd Floor Slab"
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(record_inventory_transaction(payload, project, user, db))

    assert error.value.status_code == 400
    assert "exceeds current available stock" in str(error.value.detail)


def test_inventory_receipt_succeeds_and_commits():
    project = Project(id=uuid4())
    user = User(id=uuid4())
    item = InventoryItem(id=uuid4(), sku="MAT-CEMENT", name="Cement", category="Concrete", unit_of_measure="bags")

    db = MagicMock()
    db.get = AsyncMock(return_value=item)
    db.scalar = AsyncMock(return_value=None)  # link does not exist yet -> will add link
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    payload = InventoryTransactionCreate(
        item_id=item.id,
        transaction_type="receipt",
        quantity=Decimal("50"),
        unit_cost=Decimal("380"),
        transaction_date=date(2026, 10, 12),
        reference="DC-10492",
        notes="Cement bags delivered to site"
    )

    with patch("app.api.routes.procurement.add_audit", new_callable=AsyncMock) as audit:
        result = asyncio.run(record_inventory_transaction(payload, project, user, db))

    assert result["transaction_type"] == "receipt"
    assert result["quantity"] == "50"
    db.commit.assert_awaited_once()
    audit.assert_awaited_once()
