import asyncio
import io
import pytest
from fastapi import HTTPException
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from starlette.datastructures import Headers, UploadFile

from app.api.routes.procurement import create_purchase_order
from app.models import InventoryItem, Project, ProjectInventoryItem, User, Vendor
from app.schemas import PurchaseOrderCreate


class MultipartRequest:
    def __init__(self, payload, image):
        self.headers = Headers({"content-type": "multipart/form-data; boundary=test"})
        self.payload = payload
        self.image = image

    async def form(self, **kwargs):
        return {"payload": self.payload, "image": self.image}

    async def json(self):
        raise AssertionError("multipart request should not parse JSON")


@pytest.mark.parametrize("paid", ["0", "4", "10"])
def test_create_order_eagerly_reloads_response_after_commit(paid):
    vendor = Vendor(id=uuid4(), active=True)
    item = InventoryItem(id=uuid4())
    loaded_order = MagicMock()
    db = MagicMock()
    db.get = AsyncMock(return_value=vendor)
    db.scalar = AsyncMock(side_effect=[None, loaded_order])
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    payload = PurchaseOrderCreate(vendor_id=vendor.id, order_date=date(2026, 10, 11),
                                 lines=[{"item_id": item.id, "description": "Material", "quantity": "1", "unit_price": "10"}], paid_amount=paid, payment_mode="Gpay", payment_comment="REF-123")
    with patch("app.api.routes.procurement.resolve_line_item", new_callable=AsyncMock, return_value=item), patch("app.api.routes.procurement.add_audit", new_callable=AsyncMock), patch("app.api.routes.procurement.order_dto", return_value={"total": "10.00"}) as dto:
        result = asyncio.run(create_purchase_order(payload, Project(id=uuid4(), currency="INR"), User(id=uuid4()), db))
    assert result == {"total": "10.00"}
    db.commit.assert_awaited_once()
    db.refresh.assert_not_awaited()
    dto.assert_called_once_with(loaded_order, detail=True)
    query = db.scalar.call_args.args[0]
    assert query.get_execution_options()["populate_existing"] is True
    assert len(query._with_options) == 3
    saved_order = db.add.call_args.args[0]
    project_links = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], ProjectInventoryItem)]
    assert len(project_links) == 1
    assert project_links[0].item_id == item.id
    assert project_links[0].project_id == db.add.call_args_list[-1].args[0].project_id
    assert len(saved_order.payments) == (0 if paid == "0" else 1)
    if paid != "0":
        assert str(saved_order.payments[0].amount) == paid
        assert saved_order.payments[0].payment_mode == "Gpay"
        assert saved_order.payments[0].comment == "REF-123"


def test_initial_payment_cannot_exceed_total():
    db = MagicMock()
    payload = PurchaseOrderCreate(vendor_id=uuid4(), order_date=date(2026, 10, 11), lines=[{"item_id": uuid4(), "description": "Material", "quantity": "1", "unit_price": "10"}], paid_amount="11")
    with pytest.raises(HTTPException) as error:
        asyncio.run(create_purchase_order(payload, Project(id=uuid4()), User(id=uuid4()), db))
    assert error.value.status_code == 422
    db.add.assert_not_called()


def test_create_order_stores_optional_image(tmp_path):
    vendor = Vendor(id=uuid4(), active=True)
    item = InventoryItem(id=uuid4())
    loaded_order = MagicMock()
    db = MagicMock()
    db.get = AsyncMock(return_value=vendor)
    db.scalar = AsyncMock(side_effect=[None, loaded_order])
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    payload = PurchaseOrderCreate(vendor_id=vendor.id, order_date=date(2026, 10, 11),
                                  lines=[{"item_id": item.id, "description": "Material", "quantity": "1", "unit_price": "10"}])
    image = UploadFile(filename="receipt.png", file=io.BytesIO(b"\x89PNG\r\n\x1a\nimage"), headers=Headers({"content-type": "image/png"}))
    with patch("app.api.routes.procurement.settings.upload_directory", tmp_path), patch("app.api.routes.procurement.resolve_line_item", new_callable=AsyncMock, return_value=item), patch("app.api.routes.procurement.add_audit", new_callable=AsyncMock), patch("app.api.routes.procurement.order_dto", return_value={"total": "10.00"}):
        asyncio.run(create_purchase_order(MultipartRequest(payload.model_dump_json(), image), Project(id=uuid4(), currency="INR"), User(id=uuid4()), db))

    saved_order = db.add.call_args_list[-1].args[0]
    image_path = tmp_path / saved_order.image_storage_name
    assert image_path.is_file()
    assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert saved_order.image_filename == "receipt.png"
    assert saved_order.image_content_type == "image/png"


def test_create_order_rejects_image_content_with_wrong_signature():
    image = UploadFile(filename="receipt.png", file=io.BytesIO(b"not an image"), headers=Headers({"content-type": "image/png"}))
    payload = PurchaseOrderCreate(vendor_id=uuid4(), order_date=date(2026, 10, 11),
                                  lines=[{"item_id": uuid4(), "description": "Material", "quantity": "1", "unit_price": "10"}])
    request = MultipartRequest(payload.model_dump_json(), image)
    with pytest.raises(HTTPException) as error:
        asyncio.run(create_purchase_order(request, Project(id=uuid4()), User(id=uuid4()), MagicMock()))
    assert error.value.status_code == 415