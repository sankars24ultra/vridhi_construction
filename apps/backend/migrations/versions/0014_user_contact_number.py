from alembic import op
import sqlalchemy as sa


revision = "0014_user_phone"
down_revision = "0013_member_perms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(40), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")