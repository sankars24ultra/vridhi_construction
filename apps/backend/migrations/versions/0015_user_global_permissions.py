from alembic import op
import sqlalchemy as sa


revision = "0015_global_perms"
down_revision = "0014_user_phone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("global_access", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("global_permissions", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "global_permissions")
    op.drop_column("users", "global_access")