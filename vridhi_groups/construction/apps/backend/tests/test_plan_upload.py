import asyncio
from io import BytesIO
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.datastructures import FormData, Headers, UploadFile

from app.api.routes.projects import upload_project_document
from app.models import Contract, Project, ProjectValueHistory, User


@pytest.mark.parametrize("status", ["Planning", "Active", "On Hold", "Completed", "Cancelled"])
def test_plan_upload_status_and_storage(tmp_path, status):
    request = MagicMock()
    request.form = AsyncMock(return_value=FormData({"plan_document": UploadFile(BytesIO(b"%PDF-test"), filename="plan.pdf", headers=Headers({"content-type": "application/pdf"})), "plan_comment": "Revised plan", "current_value": "0", "new_estimate": "100"}))
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    with patch("app.api.routes.projects.settings") as settings, patch("app.api.routes.projects.add_audit", new_callable=AsyncMock):
        settings.upload_directory = tmp_path
        settings.upload_max_bytes = 10 * 1024 * 1024
        if status in {"Completed", "Cancelled"}:
            with pytest.raises(HTTPException) as error:
                asyncio.run(upload_project_document(request, Project(id=uuid4(), status=status), User(id=uuid4()), db))
            assert error.value.status_code == 409
            db.add.assert_not_called()
        else:
            result = asyncio.run(upload_project_document(request, Project(id=uuid4(), status=status), User(id=uuid4()), db))
            assert result["filename"] == "plan.pdf"
            assert result["comment"] == "Revised plan"
            history = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], ProjectValueHistory)]
            assert len(history) == 1
            assert history[0].previous_value == Decimal("0")
            assert history[0].new_value == Decimal("100")
            assert next(tmp_path.iterdir()).read_bytes() == b"%PDF-test"
            db.commit.assert_awaited_once()


def test_failed_plan_upload_removes_file(tmp_path):
    request = MagicMock()
    request.form = AsyncMock(return_value=FormData({"plan_document": UploadFile(BytesIO(b"%PDF-test"), filename="plan.pdf"), "current_value": "0", "new_estimate": "100"}))
    db = MagicMock()
    db.flush = AsyncMock(side_effect=RuntimeError("Database failure"))
    db.rollback = AsyncMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    with patch("app.api.routes.projects.settings") as settings:
        settings.upload_directory = tmp_path
        settings.upload_max_bytes = 10 * 1024 * 1024
        with pytest.raises(RuntimeError):
            asyncio.run(upload_project_document(request, Project(id=uuid4(), status="Active"), User(id=uuid4()), db))
        assert not list(tmp_path.iterdir())
        db.rollback.assert_awaited_once()


@pytest.mark.parametrize("estimate", ["", "-1", "NaN", "Infinity", "10.001"])
def test_invalid_estimate_rejected_before_storage(tmp_path, estimate):
    request = MagicMock()
    request.form = AsyncMock(return_value=FormData({"current_value": "0", "new_estimate": estimate}))
    db = MagicMock()
    with pytest.raises(HTTPException) as error:
        asyncio.run(upload_project_document(request, Project(id=uuid4(), status="Active"), User(id=uuid4()), db))
    assert error.value.status_code == 422
    db.add.assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("expected,estimate", [("100", "125"), ("100", "100"), ("90", "125")])
def test_existing_project_estimate_and_stale_value(tmp_path, expected, estimate):
    request = MagicMock()
    request.form = AsyncMock(return_value=FormData({"plan_document": UploadFile(BytesIO(b"%PDF-test"), filename="plan.pdf"), "current_value": expected, "new_estimate": estimate}))
    contract = Contract(original_value=Decimal("100"), version=1)
    db = MagicMock()
    db.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[contract])))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    with patch("app.api.routes.projects.settings") as settings, patch("app.api.routes.projects.add_audit", new_callable=AsyncMock):
        settings.upload_directory = tmp_path
        settings.upload_max_bytes = 10 * 1024 * 1024
        if expected != "100":
            with pytest.raises(HTTPException) as error:
                asyncio.run(upload_project_document(request, Project(id=uuid4(), status="Active"), User(id=uuid4()), db))
            assert error.value.status_code == 409
            assert contract.original_value == Decimal("100")
            assert not list(tmp_path.iterdir())
        else:
            asyncio.run(upload_project_document(request, Project(id=uuid4(), status="Active"), User(id=uuid4()), db))
            assert contract.original_value == Decimal(estimate)
            history = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], ProjectValueHistory)]
            assert len(history) == 1
            assert history[0].previous_value == Decimal(expected)
            assert history[0].new_value == Decimal(estimate)
            db.commit.assert_awaited_once()