import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.routes.audit import ActivityCreate, activity_label, csv_cell, project_audit_log, record_activity
from app.security import require_permission


def test_activity_labels():
    assert activity_label("visit_inventory") == "Visited Inventory"
    assert activity_label("export_inventory") == "Exported report from Inventory (export requested)"
    assert csv_cell("=formula") == "'=formula"


@pytest.mark.parametrize("export", [0, 1])
def test_audit_project_scope_sorting_pagination_and_full_export(export):
    project = SimpleNamespace(id=uuid4(), name="Test site")
    event = SimpleNamespace(id=uuid4(), occurred_at=datetime.now(timezone.utc), action="visit_inventory", entity_type="Project", entity_id=project.id, details={"module": "Inventory"})
    database = SimpleNamespace(execute=AsyncMock(return_value=MagicMock(all=lambda: [(event, "test.user", "Test User")])), scalar=AsyncMock(return_value=42))
    result = asyncio.run(project_audit_log(project=project, page=2, page_size=10, search="", export=export, db=database))
    query = database.execute.call_args.args[0]
    assert project.id in query.compile().params.values()
    assert "audit_events.project_id =" in str(query)
    assert "audit_events.occurred_at DESC" in str(query)
    assert ("LIMIT" in str(query)) is (not bool(export))
    if export:
        assert "Visited Inventory" in result.body.decode()
        assert result.media_type == "text/csv"
    else:
        assert result["page_size"] == 10
        assert result["total"] == 42


def test_visit_requires_module_read_permission():
    user = SimpleNamespace(id=uuid4(), global_access=False, global_permissions=None)
    project = SimpleNamespace(id=uuid4())
    database = SimpleNamespace(scalar=AsyncMock(return_value=None), commit=AsyncMock())
    request = Request({"type": "http", "method": "POST", "path": f"/api/v1/projects/{project.id}/activities", "path_params": {"project_id": str(project.id)}, "headers": [], "query_string": b""})
    with pytest.raises(HTTPException) as error:
        asyncio.run(record_activity(ActivityCreate(module="inventory", activity="visit"), request, project, user, database))
    assert error.value.status_code == 403
    database.commit.assert_not_awaited()


def test_visit_records_authenticated_actor_and_project():
    user = SimpleNamespace(id=uuid4(), global_access=True, global_permissions={"inventory": {"access": "allow"}})
    project = SimpleNamespace(id=uuid4())
    database = SimpleNamespace(scalar=AsyncMock(return_value=None), commit=AsyncMock())
    request = Request({"type": "http", "method": "POST", "path": f"/api/v1/projects/{project.id}/activities", "path_params": {"project_id": str(project.id)}, "headers": [], "query_string": b""})
    with patch("app.api.routes.audit.add_audit", new_callable=AsyncMock) as audit:
        asyncio.run(record_activity(ActivityCreate(module="inventory", activity="visit"), request, project, user, database))
    assert audit.call_args.args[1] is user
    assert audit.call_args.args[2] == "visit_inventory"
    assert audit.call_args.kwargs["project_id"] == project.id


def test_audit_export_permission_is_separate_from_access():
    user = SimpleNamespace(id=uuid4(), global_access=False, global_permissions=None, audit_permissions={"access": "allow", "read": {"export_report": False}})
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/projects/id/audit-log", "headers": [], "query_string": b"page_size=10&export=1"})
    database = SimpleNamespace(scalar=AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as error:
        asyncio.run(require_permission("audit", "read")(request, user, database))
    assert error.value.status_code == 403