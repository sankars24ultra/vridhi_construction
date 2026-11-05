"""Retain projects in a separate read-only archive."""
from alembic import op
import sqlalchemy as sa

revision = "0024_project_archive"
down_revision = "0023_company_audit_permission"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("archived_by_id", sa.Uuid(), nullable=True))
    op.add_column("projects", sa.Column("archive_reason", sa.String(500), nullable=True))
    op.create_foreign_key("fk_projects_archived_by", "projects", "users", ["archived_by_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_projects_archived_at", "projects", ["archived_at"])


def downgrade():
    op.drop_index("ix_projects_archived_at", table_name="projects")
    op.drop_constraint("fk_projects_archived_by", "projects", type_="foreignkey")
    op.drop_column("projects", "archive_reason")
    op.drop_column("projects", "archived_by_id")
    op.drop_column("projects", "archived_at")
