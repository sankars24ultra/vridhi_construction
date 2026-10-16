from alembic import op
import sqlalchemy as sa


revision = "0017_user_deletion"
down_revision = "0016_users_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "deleted_at")