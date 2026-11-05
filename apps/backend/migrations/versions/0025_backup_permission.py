"""Dedicated Backup permission (create and save full-system backups). Restore stays Global-only."""
from alembic import op
import sqlalchemy as sa

revision = "0025_backup_permission"
down_revision = "0024_project_archive"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("backup_permissions", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("users", "backup_permissions")
