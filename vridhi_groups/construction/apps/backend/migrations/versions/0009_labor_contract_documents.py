from alembic import op
import sqlalchemy as sa


revision = "0009_labor_contract_documents"
down_revision = "0008_labor_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labor_contract_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("storage_name", sa.String(80), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("comment", sa.String(500), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contract_id"], ["labor_contracts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_name"),
    )
    op.create_index("ix_labor_contract_documents_project_id", "labor_contract_documents", ["project_id"])
    op.create_index("ix_labor_contract_documents_contract_id", "labor_contract_documents", ["contract_id"])


def downgrade() -> None:
    op.drop_index("ix_labor_contract_documents_contract_id", table_name="labor_contract_documents")
    op.drop_index("ix_labor_contract_documents_project_id", table_name="labor_contract_documents")
    op.drop_table("labor_contract_documents")
