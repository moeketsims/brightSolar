from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    ActivityStatus,
    ExpenseCategory,
    InvoiceStatus,
    InvoiceType,
    ProjectEventKind,
    ProjectStatus,
    ServiceType,
    TechRateType,
)


# ---------- Settings ----------


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    diesel_price_per_litre: Decimal
    default_lodging_per_night: Decimal
    default_per_diem: Decimal
    default_contingency_pct: Decimal
    default_margin_pct: Decimal
    vat_pct: Decimal
    business_name: str
    base_address: str | None
    base_latitude: float | None
    base_longitude: float | None
    business_phone: str | None
    business_email: str | None
    business_website: str | None
    business_vat_number: str | None
    business_reg_number: str | None
    bank_name: str | None
    bank_account_name: str | None
    bank_account_number: str | None
    bank_branch_code: str | None
    quote_validity_days: int
    deposit_pct_default: Decimal
    quote_terms: str | None


class SettingsUpdate(BaseModel):
    diesel_price_per_litre: Decimal | None = None
    default_lodging_per_night: Decimal | None = None
    default_per_diem: Decimal | None = None
    default_contingency_pct: Decimal | None = None
    default_margin_pct: Decimal | None = None
    vat_pct: Decimal | None = None
    business_name: str | None = None
    base_address: str | None = None
    base_latitude: float | None = None
    base_longitude: float | None = None
    business_phone: str | None = None
    business_email: str | None = None
    business_website: str | None = None
    business_vat_number: str | None = None
    business_reg_number: str | None = None
    bank_name: str | None = None
    bank_account_name: str | None = None
    bank_account_number: str | None = None
    bank_branch_code: str | None = None
    quote_validity_days: int | None = None
    deposit_pct_default: Decimal | None = None
    quote_terms: str | None = None


# ---------- Technician ----------


class TechnicianBase(BaseModel):
    name: str
    rate_type: TechRateType = TechRateType.HOURLY
    hourly_rate: Decimal = Decimal("0")
    daily_rate: Decimal = Decimal("0")
    phone: str | None = None
    active: bool = True


class TechnicianCreate(TechnicianBase):
    pass


class TechnicianOut(TechnicianBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Vehicle ----------


class VehicleBase(BaseModel):
    name: str
    registration: str | None = None
    fuel_consumption_l_per_100km: Decimal = Decimal("10")
    running_cost_per_km: Decimal = Decimal("2.50")
    active: bool = True


class VehicleCreate(VehicleBase):
    pass


class VehicleOut(VehicleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Client ----------


class ClientBase(BaseModel):
    name: str
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    notes: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


# ---------- Project ----------


class MaterialLine(BaseModel):
    name: str
    qty: Decimal = Decimal("1")
    unit_cost: Decimal = Decimal("0")


class TechAssignment(BaseModel):
    technician_id: int
    hours: Decimal = Decimal("0")
    days: Decimal = Decimal("0")


class ActivityBase(BaseModel):
    title: str
    description: str | None = None
    status: ActivityStatus = ActivityStatus.PENDING
    estimated_hours: Decimal = Decimal("0")
    scheduled_date: date | None = None
    due_date: date | None = None
    blocker_reason: str | None = None
    notes: str | None = None
    assigned_tech_ids: list[int] = []
    position: int = 0


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: ActivityStatus | None = None
    estimated_hours: Decimal | None = None
    scheduled_date: date | None = None
    due_date: date | None = None
    blocker_reason: str | None = None
    notes: str | None = None
    assigned_tech_ids: list[int] | None = None
    position: int | None = None


class TimeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activity_id: int
    technician_id: int
    technician_name: str | None = None
    started_at: datetime
    ended_at: datetime | None
    hours: Decimal | None
    note: str | None


class ActivityOut(ActivityBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    started_at: datetime | None
    completed_at: datetime | None
    actual_hours: Decimal  # computed from time_entries
    time_entries: list[TimeEntryOut] = []
    created_at: datetime
    updated_at: datetime


class ActivityStartIn(BaseModel):
    technician_id: int
    note: str | None = None


class ActivityStopIn(BaseModel):
    technician_id: int
    note: str | None = None


class TemplateActivity(BaseModel):
    title: str
    description: str | None = None
    estimated_hours: Decimal = Decimal("0")
    position: int = 0


class ServiceTemplateBase(BaseModel):
    name: str
    service_type: ServiceType
    description: str | None = None
    default_people_on_site: int = 1
    default_estimated_hours_on_site: Decimal = Decimal("0")
    default_contingency_pct: Decimal = Decimal("15")
    default_margin_pct: Decimal = Decimal("25")
    materials: list[MaterialLine] = []
    activities: list[TemplateActivity] = []


class ServiceTemplateCreate(ServiceTemplateBase):
    pass


class ServiceTemplateUpdate(BaseModel):
    name: str | None = None
    service_type: ServiceType | None = None
    description: str | None = None
    default_people_on_site: int | None = None
    default_estimated_hours_on_site: Decimal | None = None
    default_contingency_pct: Decimal | None = None
    default_margin_pct: Decimal | None = None
    materials: list[MaterialLine] | None = None
    activities: list[TemplateActivity] | None = None


class ServiceTemplateOut(ServiceTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ProjectInputs(BaseModel):
    """Fields that feed the costing engine."""

    client_id: int
    title: str
    service_type: ServiceType
    site_address: str | None = None
    description: str | None = None
    one_way_distance_km: Decimal = Decimal("0")
    return_trips: int = 1
    vehicle_id: int | None = None
    estimated_hours_on_site: Decimal = Decimal("0")
    estimated_travel_hours: Decimal = Decimal("0")
    overnight_nights: int = 0
    people_on_site: int = 1
    contingency_pct: Decimal | None = None
    margin_pct: Decimal | None = None
    materials: list[MaterialLine] = []
    tech_assignments: list[TechAssignment] = []
    initial_activities: list[TemplateActivity] = []
    from_template_id: int | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    service_type: ServiceType | None = None
    status: ProjectStatus | None = None
    site_address: str | None = None
    description: str | None = None
    one_way_distance_km: Decimal | None = None
    return_trips: int | None = None
    vehicle_id: int | None = None
    estimated_hours_on_site: Decimal | None = None
    estimated_travel_hours: Decimal | None = None
    overnight_nights: int | None = None
    people_on_site: int | None = None
    contingency_pct: Decimal | None = None
    margin_pct: Decimal | None = None
    materials: list[MaterialLine] | None = None
    tech_assignments: list[TechAssignment] | None = None


class CostLine(BaseModel):
    key: str
    label: str
    detail: str
    amount: float


class CostBreakdown(BaseModel):
    lines: list[CostLine]
    subtotal: float
    contingency: float
    margin: float
    total_ex_vat: float
    vat: float
    total_inc_vat: float


class ActualTotals(BaseModel):
    total: Decimal
    by_category: dict[str, Decimal]


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_id: int
    client_name: str
    title: str
    service_type: ServiceType
    status: ProjectStatus
    site_address: str | None
    quoted_total_ex_vat: Decimal
    quoted_total_inc_vat: Decimal
    actual_total: Decimal
    margin_ex_vat: Decimal
    margin_pct_realised: float
    created_at: datetime


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    category: ExpenseCategory
    amount: Decimal
    description: str | None
    receipt_path: str | None
    technician_id: int | None
    latitude: float | None
    longitude: float | None
    incurred_at: datetime
    created_at: datetime


class ProjectDetail(BaseModel):
    id: int
    client: ClientOut
    title: str
    service_type: ServiceType
    status: ProjectStatus
    site_address: str | None
    description: str | None
    quote_number: str | None = None
    accepted_at: datetime | None = None
    accepted_by_name: str | None = None
    one_way_distance_km: Decimal
    return_trips: int
    vehicle: VehicleOut | None
    estimated_hours_on_site: Decimal
    estimated_travel_hours: Decimal
    overnight_nights: int
    people_on_site: int
    contingency_pct: Decimal
    margin_pct: Decimal
    vat_pct: Decimal
    diesel_price_snapshot: Decimal
    lodging_rate_snapshot: Decimal
    per_diem_snapshot: Decimal
    materials: list[MaterialLine]
    tech_assignments: list[TechAssignment]
    activities: list[ActivityOut]
    quoted: CostBreakdown
    actuals: ActualTotals
    expenses: list[ExpenseOut]
    events: list["ProjectEventOut"]
    created_at: datetime
    updated_at: datetime


class ProjectEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    kind: ProjectEventKind
    summary: str
    details: str | None
    note: str | None
    quote_before: Decimal | None
    quote_after: Decimal | None
    created_at: datetime


class ProjectNoteIn(BaseModel):
    note: str


class AcceptQuoteIn(BaseModel):
    accepted_by_name: str


# ---------- Expense ----------


class ExpenseCreate(BaseModel):
    project_id: int
    category: ExpenseCategory
    amount: Decimal
    description: str | None = None
    technician_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None


# ---------- Dashboard ----------


class DashboardProjectCard(BaseModel):
    id: int
    client_name: str
    title: str
    status: ProjectStatus
    quoted_inc_vat: Decimal
    quoted_ex_vat: Decimal
    actual_total: Decimal
    # Share of quoted (ex-VAT cost + margin) already consumed by actuals (0..1+)
    burn_ratio: float
    status_colour: str  # green / amber / red


class ReconciliationLine(BaseModel):
    key: str
    label: str
    quoted: Decimal
    actual: Decimal
    delta: Decimal
    pct_of_quoted: float  # 0.0–∞; 1.0 = spot on


class ActivityAccuracy(BaseModel):
    activity_id: int
    title: str
    estimated_hours: Decimal
    actual_hours: Decimal
    delta_hours: Decimal
    status: str


class LearningSuggestion(BaseModel):
    id: str  # stable key used by apply endpoint
    summary: str  # e.g. "Lodging rate looks high — seen R1,100/night, default is R950"
    field: str  # Settings field name, e.g. "default_lodging_per_night"
    target: str  # "settings" or "vehicle:{id}"
    suggested_value: Decimal
    current_value: Decimal


class ReconciliationOut(BaseModel):
    project_id: int
    ready: bool  # True when project is in closed status
    quoted_total_ex_vat: Decimal
    actual_total: Decimal
    margin_quoted: Decimal
    margin_realised: Decimal
    margin_delta: Decimal
    total_hours_estimated: Decimal
    total_hours_actual: Decimal
    lines: list[ReconciliationLine]
    activity_accuracy: list[ActivityAccuracy]
    suggestions: list[LearningSuggestion]


class ApplySuggestionIn(BaseModel):
    suggestion_id: str  # echoed back from a previous reconciliation call
    field: str
    target: str
    value: Decimal


class PaymentBase(BaseModel):
    received_at: date | None = None
    amount: Decimal
    method: str = "eft"
    reference: str | None = None
    note: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentOut(PaymentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    received_at: date
    created_at: datetime


class InvoiceCreate(BaseModel):
    type: InvoiceType
    subtotal_ex_vat: Decimal | None = None  # if not given, computed from type
    due_at: date | None = None
    retention_pct: Decimal = Decimal("0")
    description: str | None = None
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    status: InvoiceStatus | None = None
    due_at: date | None = None
    description: str | None = None
    notes: str | None = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    invoice_number: str
    type: InvoiceType
    status: InvoiceStatus
    issued_at: date
    due_at: date
    subtotal_ex_vat: Decimal
    vat: Decimal
    total_inc_vat: Decimal
    retention_pct: Decimal
    retention_amount: Decimal
    description: str | None
    notes: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
    paid_total: Decimal = Decimal("0")
    outstanding: Decimal = Decimal("0")
    is_overdue: bool = False
    days_overdue: int = 0
    payments: list[PaymentOut] = []


class InvoiceWithProject(InvoiceOut):
    project_title: str
    client_name: str


class AgedDebtors(BaseModel):
    bucket_0_30: Decimal
    bucket_31_60: Decimal
    bucket_61_90: Decimal
    bucket_90_plus: Decimal
    total_outstanding: Decimal
    overdue_count: int


class DashboardOut(BaseModel):
    active_projects: int
    quoted_pipeline: Decimal
    expenses_this_month: Decimal
    projects_over_budget: int
    activities_in_progress: int
    activities_overdue: int
    activities_blocked: int
    debtors: AgedDebtors
    cards: list[DashboardProjectCard]


class TodayActivity(BaseModel):
    activity: ActivityOut
    project_id: int
    project_title: str
    client_name: str


class TodayTechColumn(BaseModel):
    technician_id: int | None
    technician_name: str
    scheduled_hours: Decimal
    activities: list[TodayActivity]
    overload: bool


class TodayBoard(BaseModel):
    date: date
    columns: list[TodayTechColumn]
    total_activities: int
