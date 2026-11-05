from alembic import op
import sqlalchemy as sa


revision = "0010_labor_addendum_documents"
down_revision = "0009_labor_contract_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("labor_contract_addenda", sa.Column("document_storage_name", sa.String(80), nullable=True))
    op.add_column("labor_contract_addenda", sa.Column("document_filename", sa.String(255), nullable=True))
    op.add_column("labor_contract_addenda", sa.Column("document_content_type", sa.String(120), nullable=True))
    op.add_column("labor_contract_addenda", sa.Column("document_byte_size", sa.BigInteger(), nullable=True))
    op.create_unique_constraint("uq_labor_contract_addenda_document_storage_name", "labor_contract_addenda", ["document_storage_name"])


def downgrade() -> None:
    op.drop_constraint("uq_labor_contract_addenda_document_storage_name", "labor_contract_addenda", type_="unique")
    op.drop_column("labor_contract_addenda", "document_byte_size")
    op.drop_column("labor_contract_addenda", "document_content_type")
    op.drop_column("labor_contract_addenda", "document_filename")
    op.drop_column("labor_contract_addenda", "document_storage_name")
