import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.api.routes.procurement import list_purchase_orders
from app.models import Project


@pytest.mark.parametrize("size", [20, 50, 100, 200])
def test_purchase_order_pagination_and_search(size):
    db = MagicMock()
    db.scalars = AsyncMock(return_value=MagicMock(unique=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    db.scalar = AsyncMock(return_value=215)
    result = asyncio.run(list_purchase_orders(2, size, "steel", Project(id=uuid4()), db))
    query = db.scalars.call_args.args[0]
    count = db.scalar.call_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    count_sql = str(count.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert f"LIMIT {size} OFFSET {size}" in sql
    assert "order_date DESC" in sql and "created_at DESC" in sql
    assert "steel" in sql and "steel" in count_sql
    assert "EXISTS" in sql
    assert result == {"items": [], "page": 2, "page_size": size, "total": 215}


@pytest.mark.parametrize("status", ["Paid", "Partially paid", "Pending"])
def test_purchase_order_payment_status_filter(status):
    db = MagicMock()
    db.scalars = AsyncMock(return_value=MagicMock(unique=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    db.scalar = AsyncMock(return_value=0)

    asyncio.run(list_purchase_orders(1, 20, None, Project(id=uuid4()), db, payment_status=status))

    query = db.scalars.call_args.args[0]
    count = db.scalar.call_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    count_sql = str(count.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "purchase_order_payments" in sql
    assert "purchase_order_payments" in count_sql
    if status == "Paid":
        assert "purchase_order_lines" in sql and ">=" in sql
    elif status == "Partially paid":
        assert "purchase_order_lines" in sql and ">" in sql and "<" in sql
    else:
        assert "= 0" in sql
        assert "purchase_order_lines" not in sql