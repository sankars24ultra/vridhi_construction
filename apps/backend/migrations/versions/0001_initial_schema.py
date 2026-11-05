"""Create the initial local application schema.

Revision ID: 0001_initial_schema
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('cost_codes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('inventory_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('sku', sa.String(length=60), nullable=False),
    sa.Column('name', sa.String(length=180), nullable=False),
    sa.Column('category', sa.String(length=80), nullable=False),
    sa.Column('unit_of_measure', sa.String(length=32), nullable=False),
    sa.Column('classification', sa.String(length=24), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sku')
    )
    op.create_index(op.f('ix_inventory_items_name'), 'inventory_items', ['name'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('role', sa.String(length=40), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_table('vendors',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=40), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('auth_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auth_sessions_token_hash'), 'auth_sessions', ['token_hash'], unique=True)
    op.create_index(op.f('ix_auth_sessions_user_id'), 'auth_sessions', ['user_id'], unique=False)
    op.create_table('idempotency_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=False),
    sa.Column('key', sa.String(length=160), nullable=False),
    sa.Column('request_hash', sa.String(length=64), nullable=False),
    sa.Column('response_body', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('actor_id', 'key')
    )
    op.create_index(op.f('ix_idempotency_records_actor_id'), 'idempotency_records', ['actor_id'], unique=False)
    op.create_table('projects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('baseline_budget', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('estimated_end_date', sa.Date(), nullable=True),
    sa.Column('created_by_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)
    op.create_table('audit_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=80), nullable=False),
    sa.Column('entity_type', sa.String(length=80), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=True),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('billing_entries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('application_number', sa.String(length=32), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('submitted_date', sa.Date(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_billing_entries_project_id'), 'billing_entries', ['project_id'], unique=False)
    op.create_table('contracts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('number', sa.String(length=32), nullable=False),
    sa.Column('original_value', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('number')
    )
    op.create_index(op.f('ix_contracts_project_id'), 'contracts', ['project_id'], unique=False)
    op.create_table('project_documents',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('uploaded_by_id', sa.Uuid(), nullable=False),
    sa.Column('storage_name', sa.String(length=80), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('content_type', sa.String(length=120), nullable=False),
    sa.Column('byte_size', sa.BigInteger(), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('comment', sa.Text(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_name')
    )
    op.create_index(op.f('ix_project_documents_project_id'), 'project_documents', ['project_id'], unique=False)
    op.create_table('project_inventory_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'item_id')
    )
    op.create_index(op.f('ix_project_inventory_items_item_id'), 'project_inventory_items', ['item_id'], unique=False)
    op.create_index(op.f('ix_project_inventory_items_project_id'), 'project_inventory_items', ['project_id'], unique=False)
    op.create_table('project_memberships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'user_id')
    )
    op.create_index(op.f('ix_project_memberships_project_id'), 'project_memberships', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_memberships_user_id'), 'project_memberships', ['user_id'], unique=False)
    op.create_table('project_status_history',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('previous_status', sa.String(length=24), nullable=True),
    sa.Column('new_status', sa.String(length=24), nullable=False),
    sa.Column('comment', sa.Text(), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_status_history_project_id'), 'project_status_history', ['project_id'], unique=False)
    op.create_table('purchase_orders',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('number', sa.String(length=32), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('vendor_id', sa.Uuid(), nullable=False),
    sa.Column('order_date', sa.Date(), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('approval_status', sa.String(length=24), nullable=False),
    sa.Column('created_by_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('number')
    )
    op.create_index(op.f('ix_purchase_orders_order_date'), 'purchase_orders', ['order_date'], unique=False)
    op.create_index(op.f('ix_purchase_orders_project_id'), 'purchase_orders', ['project_id'], unique=False)
    op.create_index(op.f('ix_purchase_orders_vendor_id'), 'purchase_orders', ['vendor_id'], unique=False)
    op.create_table('timecards',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('employee_name', sa.String(length=160), nullable=False),
    sa.Column('cost_code', sa.String(length=100), nullable=False),
    sa.Column('work_date', sa.Date(), nullable=False),
    sa.Column('regular_hours', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('hourly_rate', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('created_by_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timecards_project_id'), 'timecards', ['project_id'], unique=False)
    op.create_index(op.f('ix_timecards_work_date'), 'timecards', ['work_date'], unique=False)
    op.create_table('purchase_order_lines',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('purchase_order_id', sa.Uuid(), nullable=False),
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('cost_code_id', sa.Uuid(), nullable=True),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['cost_code_id'], ['cost_codes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_order_lines_item_id'), 'purchase_order_lines', ['item_id'], unique=False)
    op.create_index(op.f('ix_purchase_order_lines_purchase_order_id'), 'purchase_order_lines', ['purchase_order_id'], unique=False)
    op.create_table('purchase_order_payments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('purchase_order_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('payment_date', sa.Date(), nullable=False),
    sa.Column('reference', sa.String(length=100), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('recorded_by_id', sa.Uuid(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['recorded_by_id'], ['users.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_purchase_order_payments_payment_date'), 'purchase_order_payments', ['payment_date'], unique=False)
    op.create_index(op.f('ix_purchase_order_payments_purchase_order_id'), 'purchase_order_payments', ['purchase_order_id'], unique=False)
    op.create_table('inventory_transactions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('item_id', sa.Uuid(), nullable=False),
    sa.Column('purchase_order_line_id', sa.Uuid(), nullable=True),
    sa.Column('transaction_type', sa.String(length=24), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_cost', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['purchase_order_line_id'], ['purchase_order_lines.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('purchase_order_line_id', name='inventory_transactions_purchase_order_line_id_key')
    )
    op.create_index(op.f('ix_inventory_transactions_item_id'), 'inventory_transactions', ['item_id'], unique=False)
    op.create_index(op.f('ix_inventory_transactions_project_id'), 'inventory_transactions', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_inventory_transactions_project_id'), table_name='inventory_transactions')
    op.drop_index(op.f('ix_inventory_transactions_item_id'), table_name='inventory_transactions')
    op.drop_table('inventory_transactions')
    op.drop_index(op.f('ix_purchase_order_payments_purchase_order_id'), table_name='purchase_order_payments')
    op.drop_index(op.f('ix_purchase_order_payments_payment_date'), table_name='purchase_order_payments')
    op.drop_table('purchase_order_payments')
    op.drop_index(op.f('ix_purchase_order_lines_purchase_order_id'), table_name='purchase_order_lines')
    op.drop_index(op.f('ix_purchase_order_lines_item_id'), table_name='purchase_order_lines')
    op.drop_table('purchase_order_lines')
    op.drop_index(op.f('ix_timecards_work_date'), table_name='timecards')
    op.drop_index(op.f('ix_timecards_project_id'), table_name='timecards')
    op.drop_table('timecards')
    op.drop_index(op.f('ix_purchase_orders_vendor_id'), table_name='purchase_orders')
    op.drop_index(op.f('ix_purchase_orders_project_id'), table_name='purchase_orders')
    op.drop_index(op.f('ix_purchase_orders_order_date'), table_name='purchase_orders')
    op.drop_table('purchase_orders')
    op.drop_index(op.f('ix_project_status_history_project_id'), table_name='project_status_history')
    op.drop_table('project_status_history')
    op.drop_index(op.f('ix_project_memberships_user_id'), table_name='project_memberships')
    op.drop_index(op.f('ix_project_memberships_project_id'), table_name='project_memberships')
    op.drop_table('project_memberships')
    op.drop_index(op.f('ix_project_inventory_items_project_id'), table_name='project_inventory_items')
    op.drop_index(op.f('ix_project_inventory_items_item_id'), table_name='project_inventory_items')
    op.drop_table('project_inventory_items')
    op.drop_index(op.f('ix_project_documents_project_id'), table_name='project_documents')
    op.drop_table('project_documents')
    op.drop_index(op.f('ix_contracts_project_id'), table_name='contracts')
    op.drop_table('contracts')
    op.drop_index(op.f('ix_billing_entries_project_id'), table_name='billing_entries')
    op.drop_table('billing_entries')
    op.drop_table('audit_events')
    op.drop_index(op.f('ix_projects_status'), table_name='projects')
    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_table('projects')
    op.drop_index(op.f('ix_idempotency_records_actor_id'), table_name='idempotency_records')
    op.drop_table('idempotency_records')
    op.drop_index(op.f('ix_auth_sessions_user_id'), table_name='auth_sessions')
    op.drop_index(op.f('ix_auth_sessions_token_hash'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_table('vendors')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_inventory_items_name'), table_name='inventory_items')
    op.drop_table('inventory_items')
    op.drop_table('cost_codes')
