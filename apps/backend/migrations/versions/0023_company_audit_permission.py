"""Dedicated Company Audit Log permission; existing Company Cashbook users keep their access."""
from alembic import op
import sqlalchemy as sa

revision = "0023_company_audit_permission"
down_revision = "0022_cashbook_type_direction"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("company_audit_permissions", sa.JSON(), nullable=True))
    op.execute(sa.text(
        "UPDATE users SET company_audit_permissions = CAST('{\"access\": \"allow\", \"read\": {\"export_report\": false}, \"write\": {\"mode\": \"partial\", \"actions\": {}}}' AS JSON) "
        "WHERE cashbook_permissions IS NOT NULL AND cashbook_permissions->>'access' = 'allow'"
    ))


def downgrade():
    op.drop_column("users", "company_audit_permissions")
