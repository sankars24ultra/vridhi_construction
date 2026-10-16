from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    version: Mapped[int] = mapped_column(default=1, nullable=False)


class ProjectStatus(StrEnum):
    PLANNING = "Planning"
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


PROJECT_STATUS_TRANSITIONS = {
    "Planning": ("Active", "On Hold", "Cancelled"),
    "Active": ("On Hold", "Completed", "Cancelled"),
    "On Hold": ("Active", "Completed", "Cancelled"),
    "Completed": (),
    "Cancelled": ("Planning",),
}


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(40), default="User")
    global_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=func.false())
    global_permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    users_permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    audit_permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    memberships: Mapped[list["ProjectMembership"]] = relationship(back_populates="user")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("actor_id", "key"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    key: Mapped[str] = mapped_column(String(160))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_body: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    location: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(24), default=ProjectStatus.PLANNING.value, index=True)
    baseline_budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    start_date: Mapped[date] = mapped_column(Date)
    estimated_end_date: Mapped[date | None] = mapped_column(Date)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    memberships: Mapped[list["ProjectMembership"]] = relationship(back_populates="project")
    contracts: Mapped[list["Contract"]] = relationship(back_populates="project")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="project")
    inventory_items: Mapped[list["ProjectInventoryItem"]] = relationship(back_populates="project")
    status_events: Mapped[list["ProjectStatusHistory"]] = relationship(back_populates="project")
    timecards: Mapped[list["Timecard"]] = relationship(back_populates="project")


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    project: Mapped[Project] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class RBACRole(Base, TimestampMixin):
    __tablename__ = "rbac_roles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(240), default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    permissions: Mapped[list["RBACRolePermission"]] = relationship(back_populates="role", cascade="all, delete-orphan")


class RBACPermission(Base):
    __tablename__ = "rbac_permissions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    resource: Mapped[str] = mapped_column(String(40), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(240), default="")


class RBACRolePermission(Base):
    __tablename__ = "rbac_role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("rbac_roles.id", ondelete="CASCADE"), index=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey("rbac_permissions.id", ondelete="CASCADE"), index=True)
    can_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_write: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[RBACRole] = relationship(back_populates="permissions")
    permission: Mapped[RBACPermission] = relationship()


class ProjectStatusHistory(Base):
    __tablename__ = "project_status_history"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(24))
    new_status: Mapped[str] = mapped_column(String(24))
    comment: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    project: Mapped[Project] = relationship(back_populates="status_events")


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    storage_name: Mapped[str] = mapped_column(String(80), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[str] = mapped_column(String(32), default="initial_approval")
    comment: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectValueHistory(Base):
    __tablename__ = "project_value_history"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("project_documents.id", ondelete="RESTRICT"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    previous_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    new_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="vendor")


class CostCode(Base, TimestampMixin):
    __tablename__ = "cost_codes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    category: Mapped[str] = mapped_column(String(80), default="Materials")
    unit_of_measure: Mapped[str] = mapped_column(String(32), default="unit")
    classification: Mapped[str] = mapped_column(String(24), default="stock")
    project_links: Mapped[list["ProjectInventoryItem"]] = relationship(back_populates="item")
    transactions: Mapped[list["InventoryTransaction"]] = relationship(back_populates="item")


class ProjectInventoryItem(Base, TimestampMixin):
    __tablename__ = "project_inventory_items"
    __table_args__ = (UniqueConstraint("project_id", "item_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    project: Mapped[Project] = relationship(back_populates="inventory_items")
    item: Mapped[InventoryItem] = relationship(back_populates="project_links")


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    vendor_id: Mapped[UUID] = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"), index=True)
    order_date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    approval_status: Mapped[str] = mapped_column(String(24), default="Draft")
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    image_storage_name: Mapped[str | None] = mapped_column(String(80))
    image_filename: Mapped[str | None] = mapped_column(String(255))
    image_content_type: Mapped[str | None] = mapped_column(String(40))
    image_byte_size: Mapped[int | None] = mapped_column(BigInteger)
    project: Mapped[Project] = relationship(back_populates="purchase_orders")
    vendor: Mapped[Vendor] = relationship(back_populates="purchase_orders")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(back_populates="purchase_order", cascade="all, delete-orphan")
    payments: Mapped[list["PurchaseOrderPayment"]] = relationship(back_populates="purchase_order")


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    purchase_order_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    cost_code_id: Mapped[UUID | None] = mapped_column(ForeignKey("cost_codes.id", ondelete="RESTRICT"))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    item: Mapped[InventoryItem] = relationship()


class PurchaseOrderPayment(Base):
    __tablename__ = "purchase_order_payments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    purchase_order_id: Mapped[UUID] = mapped_column(ForeignKey("purchase_orders.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    reference: Mapped[str | None] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(Text)
    payment_mode: Mapped[str] = mapped_column(String(24), default="Other", server_default="Other")
    recorded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="payments")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    purchase_order_line_id: Mapped[UUID | None] = mapped_column(ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"))
    transaction_type: Mapped[str] = mapped_column(String(24))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(500))
    recorded_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    item: Mapped[InventoryItem] = relationship(back_populates="transactions")
    recorded_by: Mapped["User | None"] = relationship()
    purchase_order_line: Mapped["PurchaseOrderLine | None"] = relationship()


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    original_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    project: Mapped[Project] = relationship(back_populates="contracts")


class Timecard(Base, TimestampMixin):
    __tablename__ = "timecards"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    employee_name: Mapped[str] = mapped_column(String(160))
    cost_code: Mapped[str] = mapped_column(String(100))
    work_date: Mapped[date] = mapped_column(Date, index=True)
    regular_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(24), default="Pending")
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    project: Mapped[Project] = relationship(back_populates="timecards")


class LaborWorker(Base, TimestampMixin):
    __tablename__ = "labor_workers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    trade: Mapped[str] = mapped_column(String(100), default="General labor")
    phone: Mapped[str | None] = mapped_column(String(30))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    project: Mapped[Project] = relationship()


class LaborWorkEntry(Base):
    __tablename__ = "labor_work_entries"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    worker_id: Mapped[UUID] = mapped_column(ForeignKey("labor_workers.id", ondelete="RESTRICT"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit: Mapped[str] = mapped_column(String(12), default="day")
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    recorded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    worker: Mapped[LaborWorker] = relationship()


class LaborWagePayment(Base):
    __tablename__ = "labor_wage_payments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    worker_id: Mapped[UUID] = mapped_column(ForeignKey("labor_workers.id", ondelete="RESTRICT"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    payment_mode: Mapped[str] = mapped_column(String(24), default="Cash")
    reference: Mapped[str | None] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(String(500))
    recorded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    worker: Mapped[LaborWorker] = relationship()


class LaborContract(Base, TimestampMixin):
    __tablename__ = "labor_contracts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    contract_number: Mapped[str] = mapped_column(String(40), unique=True)
    subcontractor_name: Mapped[str] = mapped_column(String(160))
    scope: Mapped[str] = mapped_column(String(500))
    pricing_type: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    contract_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    unit: Mapped[str | None] = mapped_column(String(24))
    unit_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    baseline_document_id: Mapped[UUID | None] = mapped_column(ForeignKey("project_documents.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(24), default="Active")
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    project: Mapped[Project] = relationship()
    baseline_document: Mapped[ProjectDocument | None] = relationship()
    documents: Mapped[list["LaborContractDocument"]] = relationship(back_populates="contract")


class LaborContractDocument(Base):
    __tablename__ = "labor_contract_documents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    contract_id: Mapped[UUID] = mapped_column(ForeignKey("labor_contracts.id", ondelete="RESTRICT"), index=True)
    uploaded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    storage_name: Mapped[str] = mapped_column(String(80), unique=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    comment: Mapped[str] = mapped_column(String(500), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    contract: Mapped[LaborContract] = relationship(back_populates="documents")


class LaborContractAddendum(Base):
    __tablename__ = "labor_contract_addenda"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    contract_id: Mapped[UUID] = mapped_column(ForeignKey("labor_contracts.id", ondelete="RESTRICT"), index=True)
    plan_document_id: Mapped[UUID] = mapped_column(ForeignKey("project_documents.id", ondelete="RESTRICT"))
    reason: Mapped[str] = mapped_column(String(500))
    previous_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    revised_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(24), default="Pending approval")
    submitted_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decided_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decision_comment: Mapped[str | None] = mapped_column(String(500))
    document_storage_name: Mapped[str | None] = mapped_column(String(80), unique=True)
    document_filename: Mapped[str | None] = mapped_column(String(255))
    document_content_type: Mapped[str | None] = mapped_column(String(120))
    document_byte_size: Mapped[int | None] = mapped_column(BigInteger)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contract: Mapped[LaborContract] = relationship()
    plan_document: Mapped[ProjectDocument] = relationship()


class LaborProgressClaim(Base):
    __tablename__ = "labor_progress_claims"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    contract_id: Mapped[UUID] = mapped_column(ForeignKey("labor_contracts.id", ondelete="RESTRICT"), index=True)
    claim_number: Mapped[str] = mapped_column(String(40), unique=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    work_description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(24), default="Pending certification")
    submitted_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decided_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decision_comment: Mapped[str | None] = mapped_column(String(500))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contract: Mapped[LaborContract] = relationship()


class LaborContractPayment(Base):
    __tablename__ = "labor_contract_payments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("labor_progress_claims.id", ondelete="RESTRICT"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    payment_mode: Mapped[str] = mapped_column(String(24), default="Bank transfer")
    reference: Mapped[str | None] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(String(500))
    recorded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    claim: Mapped[LaborProgressClaim] = relationship()


class BillingEntry(Base, TimestampMixin):
    __tablename__ = "billing_entries"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    application_number: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)
    submitted_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(24), default="Draft")


class CashReceipt(Base):
    __tablename__ = "cash_receipts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), index=True)
    billing_entry_id: Mapped[UUID | None] = mapped_column(ForeignKey("billing_entries.id", ondelete="RESTRICT"), index=True)
    received_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    payment_method: Mapped[str] = mapped_column(String(24), default="Other")
    reference: Mapped[str | None] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(Text)
    recorded_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[UUID | None] = mapped_column(Uuid)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())