"""Separate Projects Dashboard access and New Project permission."""
from alembic import op
import sqlalchemy as sa

revision = "0026_dashboard_permission"
down_revision = "0025_backup_permission"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("dashboard_permissions", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("users", "dashboard_permissions")
