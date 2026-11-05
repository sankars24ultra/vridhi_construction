from alembic import op
from sqlalchemy import BigInteger, Column, String


revision = "0004_purchase_order_image"
down_revision = "0003_payment_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_orders", Column("image_storage_name", String(80), nullable=True))
    op.add_column("purchase_orders", Column("image_filename", String(255), nullable=True))
    op.add_column("purchase_orders", Column("image_content_type", String(40), nullable=True))
    op.add_column("purchase_orders", Column("image_byte_size", BigInteger, nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "image_byte_size")
    op.drop_column("purchase_orders", "image_content_type")
    op.drop_column("purchase_orders", "image_filename")
    op.drop_column("purchase_orders", "image_storage_name")