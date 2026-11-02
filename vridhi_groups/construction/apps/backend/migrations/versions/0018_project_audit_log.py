from alembic import op
import sqlalchemy as sa


revision = "0018_project_audit"
down_revision = "0017_user_deletion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("audit_permissions", sa.JSON(), nullable=True))
    op.add_column("audit_events", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_audit_events_project", "audit_events", "projects", ["project_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"])
    op.execute("UPDATE audit_events SET project_id = entity_id WHERE entity_type = 'Project' AND entity_id IN (SELECT id FROM projects)")
    # Freeze entities at this revision; later modules may introduce tables not created yet.
    project_records = (
        ("BillingEntry", "billing_entries"), ("CashReceipt", "cash_receipts"),
        ("Contract", "contracts"), ("InventoryTransaction", "inventory_transactions"),
        ("LaborContract", "labor_contracts"), ("LaborContractAddendum", "labor_contract_addenda"),
        ("LaborContractDocument", "labor_contract_documents"), ("LaborContractPayment", "labor_contract_payments"),
        ("LaborProgressClaim", "labor_progress_claims"), ("LaborWagePayment", "labor_wage_payments"),
        ("LaborWorkEntry", "labor_work_entries"), ("LaborWorker", "labor_workers"),
        ("ProjectDocument", "project_documents"), ("ProjectInventoryItem", "project_inventory_items"),
        ("ProjectMembership", "project_memberships"), ("ProjectStatusHistory", "project_status_history"),
        ("ProjectValueHistory", "project_value_history"), ("PurchaseOrder", "purchase_orders"),
        ("Timecard", "timecards"),
    )
    for entity, table in project_records:
        op.execute(sa.text(f'UPDATE audit_events AS audit SET project_id = record.project_id FROM "{table}" AS record WHERE audit.entity_type = :entity AND audit.entity_id = record.id AND audit.project_id IS NULL').bindparams(entity=entity))


def downgrade() -> None:
    op.drop_index("ix_audit_events_project_id", table_name="audit_events")
    op.drop_constraint("fk_audit_events_project", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "project_id")
    op.drop_column("users", "audit_permissions")