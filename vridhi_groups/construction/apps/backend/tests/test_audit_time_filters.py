import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.audit import project_audit_log


@pytest.mark.parametrize("export", [0, 1])
def test_time_range_filters_list_count_and_export(export):
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    end = datetime(2026, 10, 15, tzinfo=timezone.utc)
    database = SimpleNamespace(execute=AsyncMock(return_value=MagicMock(all=lambda: [])), scalar=AsyncMock(return_value=0))
    asyncio.run(project_audit_log(project=SimpleNamespace(id=uuid4(), name="Test"), page=1, page_size=10, search="", export=export, db=database, start_time=start, end_time=end))
    queries = [database.execute.call_args.args[0]]
    if not export:
        queries.append(database.scalar.call_args.args[0])
    for query in queries:
        assert "audit_events.occurred_at >=" in str(query)
        assert "audit_events.occurred_at <=" in str(query)
        assert start in query.compile().params.values()
        assert end in query.compile().params.values()


@pytest.mark.parametrize("start,end", [(datetime(2026, 10, 15), None), (datetime(2026, 10, 15, tzinfo=timezone.utc), datetime(2026, 10, 1, tzinfo=timezone.utc))])
def test_invalid_time_range_rejected_before_query(start, end):
    database = MagicMock()
    with pytest.raises(HTTPException) as error:
        asyncio.run(project_audit_log(project=SimpleNamespace(id=uuid4()), page=1, page_size=10, search="", export=0, db=database, start_time=start, end_time=end))
    assert error.value.status_code == 422
    database.execute.assert_not_called()