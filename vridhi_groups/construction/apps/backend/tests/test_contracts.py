from decimal import Decimal
import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.projects import update_project_status
from app.services.common import dashboard_cost_summary, money, order_totals, payment_status, project_dto
from app.models import Project, PurchaseOrder, User


def test_money_formats_to_two_decimal_places() -> None:
    assert money(Decimal("12")) == "12.00"
    assert money(Decimal("12.345")) == "12.34"


def test_purchase_order_totals_derive_paid_and_balance() -> None:
    order = PurchaseOrder()
    order.lines = []
    order.payments = []
    assert order_totals(order) == (Decimal("0"), Decimal("0"), Decimal("0"))


@pytest.mark.parametrize(
    ("total", "paid", "balance", "expected"),
    [
        (Decimal("100"), Decimal("0"), Decimal("100"), "Pending"),
        (Decimal("100"), Decimal("40"), Decimal("60"), "Partially paid"),
        (Decimal("100"), Decimal("100"), Decimal("0"), "Paid"),
        (Decimal("0"), Decimal("0"), Decimal("0"), "Pending"),
    ],
)
def test_purchase_order_payment_status(total, paid, balance, expected):
    assert payment_status(total, paid, balance) == expected


def test_dashboard_actual_cost_combines_labor_and_ordered_value_once() -> None:
    order = SimpleNamespace(
        order_date=date(2026, 4, 3),
        lines=[SimpleNamespace(quantity=Decimal("3"), unit_price=Decimal("100"))],
        payments=[SimpleNamespace(amount=Decimal("125"))],
    )
    card = SimpleNamespace(work_date=date(2026, 4, 8), regular_hours=Decimal("4"), hourly_rate=Decimal("25"))

    summary = dashboard_cost_summary(Decimal("100"), [order], [card])

    assert summary["actual_cost"] == Decimal("400")
    assert summary["labor_cost"] == Decimal("100")
    assert summary["material_cost"] == Decimal("300")
    assert summary["monthly_costs"] == [{"month": "2026-04", "amount": Decimal("400")}]


TRANSITIONS = {
    "Planning": ["Active", "On Hold", "Cancelled"],
    "Active": ["On Hold", "Completed", "Cancelled"],
    "On Hold": ["Active", "Completed", "Cancelled"],
    "Completed": [],
    "Cancelled": ["Planning"],
}


@pytest.mark.parametrize("current,target", [(current, target) for current in TRANSITIONS for target in TRANSITIONS])
def test_project_status_transitions(current: str, target: str) -> None:
    project = Project(id=uuid4(), name="Status test", location="Test", status=current,
                      baseline_budget=Decimal("0"), currency="INR", start_date=date(2026, 10, 10), version=1)
    assert project_dto(project)["eligible_statuses"] == TRANSITIONS[current]
    db = MagicMock()
    db.commit = AsyncMock()
    user = User(id=uuid4())
    payload = {"status": target, "comment": "Status test", "hold_reason": "Waiting", "confirm_complete": True}
    with patch("app.api.routes.projects.add_audit", new_callable=AsyncMock):
        if target in TRANSITIONS[current]:
            result = asyncio.run(update_project_status(project.id, payload, 1, project, user, db))
            assert result["status"] == target
            assert result["eligible_statuses"] == TRANSITIONS[target]
            assert project.version == 2
            db.commit.assert_awaited_once()
        else:
            with pytest.raises(HTTPException) as error:
                asyncio.run(update_project_status(project.id, payload, 1, project, user, db))
            assert error.value.status_code == 422
            assert project.status == current
            assert project.version == 1
            db.add.assert_not_called()
            db.commit.assert_not_awaited()
