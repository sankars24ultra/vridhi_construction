from alembic import op
import sqlalchemy as sa


revision = "0018_project_audit"
down_revision = "0017_user_deletion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("audit_permissions", sa.JSON(), nullable=True))
    op.add_column("audit_events", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_audit_events_project", "audit_events", "projects", ["project_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"])
    op.execute("UPDATE audit_events SET project_id = entity_id WHERE entity_type = 'Project' AND entity_id IN (SELECT id FROM projects)")
    from app.models import Base

    for mapper in Base.registry.mappers:
        model = mapper.class_
        if model.__name__ != "AuditEvent" and hasattr(model, "project_id") and hasattr(model, "id"):
            table = model.__tablename__
            op.execute(sa.text(f'UPDATE audit_events AS audit SET project_id = record.project_id FROM "{table}" AS record WHERE audit.entity_type = :entity AND audit.entity_id = record.id AND audit.project_id IS NULL').bindparams(entity=model.__name__))


def downgrade() -> None:
    op.drop_index("ix_audit_events_project_id", table_name="audit_events")
    op.drop_constraint("fk_audit_events_project", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "project_id")
    op.drop_column("users", "audit_permissions")