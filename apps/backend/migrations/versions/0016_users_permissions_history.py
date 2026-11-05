from alembic import op
import sqlalchemy as sa


revision = "0016_users_history"
down_revision = "0015_global_perms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("users_permissions", sa.JSON(), nullable=True))
    op.add_column("audit_events", sa.Column("details", sa.JSON(), nullable=True))
    op.create_index("ix_audit_events_entity_history", "audit_events", ["entity_type", "entity_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity_history", table_name="audit_events")
    op.drop_column("audit_events", "details")
    op.drop_column("users", "users_permissions")