from alembic import op
import sqlalchemy as sa


revision = "0013_member_perms"
down_revision = "0012_optional_user_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_memberships", sa.Column("permissions", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_memberships", "permissions")