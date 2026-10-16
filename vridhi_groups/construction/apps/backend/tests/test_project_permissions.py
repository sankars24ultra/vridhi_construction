from app.security import project_write_action


def test_write_action_mapping_covers_requested_module_actions():
    assert project_write_action("overview", "PATCH", "/api/v1/projects/id/status") == "update_status"
    assert project_write_action("overview", "POST", "/api/v1/projects/id/documents") == "upload_plan_document"
    assert project_write_action("procurement", "POST", "/api/v1/projects/id/purchase-orders") == "new_purchase_order"
    assert project_write_action("procurement", "PATCH", "/api/v1/projects/id/purchase-orders/po") == "new_purchase_order"
    assert project_write_action("procurement", "POST", "/api/v1/projects/id/purchase-orders/po/payments") == "add_payment"
    assert project_write_action("inventory", "POST", "/api/v1/projects/id/inventory/transactions", {"transaction_type": "receipt"}) == "receive_stock"
    assert project_write_action("inventory", "POST", "/api/v1/projects/id/inventory/transactions", {"transaction_type": "issue"}) == "use_stock"
    assert project_write_action("cashflow", "POST", "/api/v1/projects/id/cash-receipts") == "record_receipt"
    assert project_write_action("labor", "POST", "/api/v1/projects/id/labor/workers") == "add_worker"
    assert project_write_action("labor", "PUT", "/api/v1/projects/id/labor/workers/worker") == "edit_worker"
    assert project_write_action("users", "POST", "/api/v1/users") == "add_user"


def test_write_action_mapping_fails_closed_for_unlisted_action():
    assert project_write_action("overview", "POST", "/api/v1/projects/id/unlisted-action") is None