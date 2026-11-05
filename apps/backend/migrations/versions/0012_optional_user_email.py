from alembic import op


revision = "0012_optional_user_email"
down_revision = "0011_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "email", nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", nullable=False)