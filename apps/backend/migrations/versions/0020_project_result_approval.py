"""Immutable approvals of automatically calculated project results."""
from alembic import op
import sqlalchemy as sa

revision = "0020_project_result_approval"
down_revision = "0019_company_cashbook"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_result_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("approved_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_project_result_approvals_project_id", "project_result_approvals", ["project_id"])


def downgrade() -> None:
    op.drop_table("project_result_approvals")
