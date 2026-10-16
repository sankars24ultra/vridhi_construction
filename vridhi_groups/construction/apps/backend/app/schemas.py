from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class Page(BaseModel):
    items: list
    page: int
    page_size: int
    total: int


class UserRead(ORMModel):
    id: UUID
    username: str
    email: str | None
    name: str


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40, pattern=r"^[+0-9(). -]*$")
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=6, max_length=128)
    project_ids: list[UUID] = Field(default_factory=list)
    project_permissions: dict[UUID, "ProjectPermissions"] = Field(default_factory=dict)
    global_access: bool = False
    global_permissions: "ProjectPermissions | None" = None
    users_permissions: "ProjectModulePermissions | None" = None
    audit_permissions: "ProjectModulePermissions | None" = None


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40, pattern=r"^[+0-9(). -]*$")
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    password: str | None = Field(default=None, min_length=6, max_length=128)
    project_ids: list[UUID] = Field(default_factory=list)
    project_permissions: dict[UUID, "ProjectPermissions"] = Field(default_factory=dict)
    global_access: bool = False
    global_permissions: "ProjectPermissions | None" = None
    users_permissions: "ProjectModulePermissions | None" = None
    audit_permissions: "ProjectModulePermissions | None" = None


class ProjectWritePermissions(BaseModel):
    mode: Literal["all", "partial"] = "all"
    actions: dict[str, bool] = Field(default_factory=dict)


class ProjectModulePermissions(BaseModel):
    access: Literal["allow", "block"]
    read: dict[str, bool] = Field(default_factory=lambda: {"export_report": True})
    write: ProjectWritePermissions = Field(default_factory=ProjectWritePermissions)


class ProjectPermissions(BaseModel):
    overview: ProjectModulePermissions
    procurement: ProjectModulePermissions
    inventory: ProjectModulePermissions
    cashflow: ProjectModulePermissions
    labor: ProjectModulePermissions
    users: ProjectModulePermissions


class SessionRead(BaseModel):
    user: UserRead
    expires_at: datetime
    csrf_token: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    location: str = Field(min_length=2, max_length=200)
    baseline_budget: Decimal = Field(ge=0)
    contract_value: Decimal = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    start_date: date


class ProjectCreateForm(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    location: str = Field(min_length=2, max_length=200)
    baseline_budget: Decimal = Field(ge=0)
    contract_value: Decimal = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    start_date: date
    plan_comment: str | None = Field(default=None, max_length=500)


class ProjectRead(ORMModel):
    id: UUID
    name: str
    location: str
    status: str
    baseline_budget: Decimal
    currency: str
    start_date: date
    version: int


class VendorRead(ORMModel):
    id: UUID
    name: str
    active: bool


class ItemRead(ORMModel):
    id: UUID
    sku: str
    name: str
    category: str
    unit_of_measure: str
    classification: str


class POLineInput(BaseModel):
    item_id: UUID | None = None
    item_name: str | None = Field(default=None, max_length=180)
    sku: str | None = Field(default=None, max_length=60)
    category: str = "Material"
    unit_of_measure: str = "unit"
    description: str = Field(min_length=1, max_length=400)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    vendor_id: UUID | None = None
    vendor_name: str | None = Field(default=None, min_length=1, max_length=160)
    order_date: date
    lines: list[POLineInput] = Field(min_length=1)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    payment_mode: Literal["Gpay", "Bank transfer", "Cash", "Other"] = "Cash"
    payment_comment: str | None = Field(default=None, max_length=500)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_date: date
    payment_mode: Literal["Gpay", "Bank transfer", "Cash", "Other"] = "Other"
    reference: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=500)


class TimecardCreate(BaseModel):
    employee_name: str = Field(min_length=2, max_length=160)
    cost_code: str = Field(min_length=1, max_length=100)
    work_date: date
    regular_hours: Decimal = Field(gt=0, le=24)
    hourly_rate: Decimal = Field(ge=0)


class LaborWorkerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    trade: str = Field(default="General labor", min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=30)


class LaborWorkerUpdate(LaborWorkerCreate):
    expected_version: int = Field(ge=1)


class LaborWorkEntryCreate(BaseModel):
    worker_id: UUID
    work_date: date
    description: str = Field(min_length=2, max_length=240)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    unit: Literal["day", "hour", "piece"] = "day"
    rate: Decimal = Field(ge=0, max_digits=18, decimal_places=2)


class LaborWagePaymentCreate(BaseModel):
    worker_id: UUID
    payment_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_mode: Literal["Cash", "Bank transfer", "Gpay", "Cheque", "Other"] = "Cash"
    reference: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=500)


class RBACGrantInput(BaseModel):
    can_read: bool
    can_write: bool


class RBACPermissionMatrixUpdate(BaseModel):
    matrix: dict[str, dict[str, RBACGrantInput]]


class LaborContractCreate(BaseModel):
    subcontractor_name: str = Field(min_length=2, max_length=160)
    scope: str = Field(min_length=2, max_length=500)
    pricing_type: Literal["unit_rate", "lump_sum"]
    contract_value: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    unit: str | None = Field(default=None, min_length=1, max_length=24)
    unit_rate: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    baseline_document_id: UUID | None = None

    @model_validator(mode="after")
    def validate_pricing(self):
        if self.pricing_type == "unit_rate" and (not self.unit or self.unit_rate is None):
            raise ValueError("Unit-rate contracts require a unit and unit rate")
        if self.pricing_type == "lump_sum" and (self.unit or self.unit_rate is not None):
            raise ValueError("Lump-sum contracts cannot specify a unit rate")
        return self


class LaborContractAddendumCreate(BaseModel):
    plan_document_id: UUID
    reason: str = Field(min_length=2, max_length=500)
    revised_value: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class LaborDecisionCreate(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=500)


class LaborProgressClaimCreate(BaseModel):
    period_start: date
    period_end: date
    work_description: str = Field(min_length=2, max_length=500)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("Claim period end must be on or after its start")
        return self


class LaborContractPaymentCreate(BaseModel):
    payment_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_mode: Literal["Cash", "Bank transfer", "Gpay", "Cheque", "Other"] = "Bank transfer"
    reference: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=500)


class BillingCreate(BaseModel):
    description: str = Field(min_length=2, max_length=400)
    submitted_date: date
    amount: Decimal = Field(gt=0)


class CashReceiptCreate(BaseModel):
    billing_entry_id: UUID | None = None
    received_date: date
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_method: Literal["Bank transfer", "Cheque", "Cash", "Gpay", "Other"] = "Other"
    reference: str | None = Field(default=None, max_length=100)
    comment: str | None = Field(default=None, max_length=500)


class InventoryTransactionCreate(BaseModel):
    item_id: UUID
    transaction_type: Literal["receipt", "issue"]
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    transaction_date: date = Field(default_factory=date.today)
    purchase_order_line_id: UUID | None = None
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
