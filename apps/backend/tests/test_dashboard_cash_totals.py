import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.routes.projects import dashboard


@pytest.mark.parametrize("invoiced,received", [(Decimal("487000.25"), Decimal("354000.75")), (None, None)])
def test_dashboard_uses_project_billing_and_receipt_totals(invoiced, received):
    project = SimpleNamespace(id=uuid4(), currency="INR", baseline_budget=Decimal("1000000"))
    database = SimpleNamespace(
        scalars=AsyncMock(return_value=MagicMock(all=lambda: [])),
        scalar=AsyncMock(side_effect=[Decimal("0"), Decimal("0"), invoiced, received]),
    )

    result = asyncio.run(dashboard(project=project, _=SimpleNamespace(), db=database))

    assert result["invoiced_amount"] == str((invoiced or Decimal("0")).quantize(Decimal("0.01")))
    assert result["cash_received"] == str((received or Decimal("0")).quantize(Decimal("0.01")))
    billing_query = database.scalar.call_args_list[2].args[0]
    receipt_query = database.scalar.call_args_list[3].args[0]
    assert "sum(billing_entries.amount)" in str(billing_query)
    assert "sum(cash_receipts.amount)" in str(receipt_query)
    assert project.id in billing_query.compile().params.values()
    assert project.id in receipt_query.compile().params.values()