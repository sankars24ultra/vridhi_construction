import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.operations import create_cash_receipt
from app.models import Project, User
from app.schemas import CashReceiptCreate


def test_cash_receipt_rejects_amount_over_application_balance():
    project = Project(id=uuid4())
    user = User(id=uuid4())
    application = SimpleNamespace(id=uuid4(), project_id=project.id, amount=Decimal("100"))
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=[application, Decimal("80")])
    db.commit = AsyncMock()
    payload = CashReceiptCreate(billing_entry_id=application.id, received_date=date(2026, 10, 12), amount="21")

    with pytest.raises(HTTPException) as error:
        asyncio.run(create_cash_receipt(payload, project, user, db))

    assert error.value.status_code == 409
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


def test_cash_receipt_records_valid_amount_and_audit():
    project = Project(id=uuid4())
    user = User(id=uuid4())
    application = SimpleNamespace(id=uuid4(), project_id=project.id, amount=Decimal("100"))
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=[application, Decimal("50")])
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    payload = CashReceiptCreate(billing_entry_id=application.id, received_date=date(2026, 10, 12), amount="50", payment_method="Bank transfer", reference="TX-1")

    with patch("app.api.routes.operations.add_audit", new_callable=AsyncMock) as audit:
        result = asyncio.run(create_cash_receipt(payload, project, user, db))

    receipt = db.add.call_args.args[0]
    assert result["amount"] == "50.00"
    assert receipt.project_id == project.id
    assert receipt.billing_entry_id == application.id
    assert receipt.payment_method == "Bank transfer"
    db.commit.assert_awaited_once()
    audit.assert_awaited_once()