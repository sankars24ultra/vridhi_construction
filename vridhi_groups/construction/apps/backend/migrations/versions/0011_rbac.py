from alembic import op
import sqlalchemy as sa
from uuid import uuid4


revision = "0011_rbac"
down_revision = "0010_labor_addendum_documents"
branch_labels = None
depends_on = None

RESOURCES = [
    ("overview", "Overview", "Project overview and financial summaries"),
    ("procurement", "Procurement", "Purchase orders and vendor payments"),
    ("inventory", "Inventory", "Site stock and inventory movements"),
    ("cashflow", "Cashflow", "Client billing and receipts"),
    ("users", "Users", "User directory and role permissions"),
    ("labor", "Labor and Wages", "Subcontract labor and individual worker records"),
]
ROLES = {
    "Owner": {resource: (True, True) for resource, _, _ in RESOURCES},
    "Admin": {resource: (True, True) for resource, _, _ in RESOURCES},
    "Supervisor": {"overview": (False, False), "procurement": (True, True), "inventory": (True, False), "cashflow": (False, False), "users": (False, False), "labor": (True, True)},
    "User1": {"overview": (False, False), "procurement": (True, True), "inventory": (True, False), "cashflow": (False, False), "users": (False, False), "labor": (True, True)},
    "Cashier": {"overview": (False, False), "procurement": (False, False), "inventory": (False, False), "cashflow": (True, True), "users": (False, False), "labor": (True, True)},
    "Managing Director": {"overview": (True, False), "procurement": (False, False), "inventory": (False, False), "cashflow": (False, False), "users": (False, False), "labor": (False, False)},
}


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())
    if "rbac_roles" not in existing_tables:
        op.create_table(
            "rbac_roles",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(40), nullable=False),
            sa.Column("description", sa.String(240), nullable=False, server_default=""),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    if "rbac_permissions" not in existing_tables:
        op.create_table(
            "rbac_permissions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("resource", sa.String(40), nullable=False),
            sa.Column("label", sa.String(80), nullable=False),
            sa.Column("description", sa.String(240), nullable=False, server_default=""),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("resource"),
        )
    if "rbac_role_permissions" not in existing_tables:
        op.create_table(
            "rbac_role_permissions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("role_id", sa.Uuid(), nullable=False),
            sa.Column("permission_id", sa.Uuid(), nullable=False),
            sa.Column("can_read", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("can_write", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.ForeignKeyConstraint(["role_id"], ["rbac_roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["permission_id"], ["rbac_permissions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("role_id", "permission_id"),
        )

    indexes = {
        table_name: {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}
        for table_name in ("rbac_roles", "rbac_role_permissions")
    }
    if "ix_rbac_roles_name" not in indexes["rbac_roles"]:
        op.create_index("ix_rbac_roles_name", "rbac_roles", ["name"])
    if "ix_rbac_role_permissions_role_id" not in indexes["rbac_role_permissions"]:
        op.create_index("ix_rbac_role_permissions_role_id", "rbac_role_permissions", ["role_id"])
    if "ix_rbac_role_permissions_permission_id" not in indexes["rbac_role_permissions"]:
        op.create_index("ix_rbac_role_permissions_permission_id", "rbac_role_permissions", ["permission_id"])

    role_ids = dict(bind.execute(sa.text("SELECT name, id FROM rbac_roles")).all())
    for role_name in ROLES:
        if role_name not in role_ids:
            role_id = uuid4()
            bind.execute(
                sa.text("INSERT INTO rbac_roles (id, name, description, is_system, version) VALUES (:id, :name, :description, :is_system, :version)"),
                {"id": role_id, "name": role_name, "description": f"Default {role_name} access profile", "is_system": True, "version": 1},
            )
            role_ids[role_name] = role_id

    permission_ids = dict(bind.execute(sa.text("SELECT resource, id FROM rbac_permissions")).all())
    for resource, label, description in RESOURCES:
        if resource not in permission_ids:
            permission_id = uuid4()
            bind.execute(
                sa.text("INSERT INTO rbac_permissions (id, resource, label, description) VALUES (:id, :resource, :label, :description)"),
                {"id": permission_id, "resource": resource, "label": label, "description": description},
            )
            permission_ids[resource] = permission_id

    existing_grants = set(bind.execute(sa.text("SELECT role_id, permission_id FROM rbac_role_permissions")).all())
    for role_name, grants in ROLES.items():
        for resource, _, _ in RESOURCES:
            pair = (role_ids[role_name], permission_ids[resource])
            if pair in existing_grants:
                continue
            can_read, can_write = grants.get(resource, (False, False))
            bind.execute(
                sa.text("INSERT INTO rbac_role_permissions (id, role_id, permission_id, can_read, can_write) VALUES (:id, :role_id, :permission_id, :can_read, :can_write)"),
                {"id": uuid4(), "role_id": pair[0], "permission_id": pair[1], "can_read": can_read, "can_write": can_write},
            )


def downgrade() -> None:
    op.drop_index("ix_rbac_role_permissions_permission_id", table_name="rbac_role_permissions")
    op.drop_index("ix_rbac_role_permissions_role_id", table_name="rbac_role_permissions")
    op.drop_table("rbac_role_permissions")
    op.drop_table("rbac_permissions")
    op.drop_index("ix_rbac_roles_name", table_name="rbac_roles")
    op.drop_table("rbac_roles")
