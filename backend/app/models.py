from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    Numeric,
    Date,
    DateTime,
    Integer,
    Enum as SAEnum,
    JSON,
    Boolean,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


# ---------- Enums ----------


class ProjectStatus(str, Enum):
    QUOTING = "quoting"
    QUOTED = "quoted"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INVOICED = "invoiced"
    PAID = "paid"
    LOST = "lost"


class ServiceType(str, Enum):
    SOLAR_INSTALL = "solar_install"
    BACKUP_INSTALL = "backup_install"
    INVERTER = "inverter"
    BATTERY = "battery"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    INSPECTION = "inspection"
    OTHER = "other"


class ExpenseCategory(str, Enum):
    DIESEL = "diesel"
    LODGING = "lodging"
    MEALS = "meals"
    TOLLS = "tolls"
    MATERIALS = "materials"
    LABOUR = "labour"
    EQUIPMENT_HIRE = "equipment_hire"
    OTHER = "other"


class TechRateType(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"


# ---------- Tables ----------


class Settings(Base):
    """Singleton row (id=1) holding global rates used by the costing engine."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    diesel_price_per_litre: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("22.50"))
    default_lodging_per_night: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("850"))
    default_per_diem: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("300"))
    default_contingency_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("15"))
    default_margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("25"))
    vat_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("15"))
    business_name: Mapped[str] = mapped_column(String(255), default="Bright Solar Power")
    base_address: Mapped[str | None] = mapped_column(Text)
    base_latitude: Mapped[float | None] = mapped_column()
    base_longitude: Mapped[float | None] = mapped_column()

    # Business details used on quote/invoice PDFs
    business_phone: Mapped[str | None] = mapped_column(String(50))
    business_email: Mapped[str | None] = mapped_column(String(255))
    business_website: Mapped[str | None] = mapped_column(String(255))
    business_vat_number: Mapped[str | None] = mapped_column(String(50))
    business_reg_number: Mapped[str | None] = mapped_column(String(50))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    bank_account_name: Mapped[str | None] = mapped_column(String(255))
    bank_account_number: Mapped[str | None] = mapped_column(String(50))
    bank_branch_code: Mapped[str | None] = mapped_column(String(20))
    quote_validity_days: Mapped[int] = mapped_column(Integer, default=30)
    deposit_pct_default: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("50"))
    quote_terms: Mapped[str | None] = mapped_column(Text)


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    rate_type: Mapped[TechRateType] = mapped_column(SAEnum(TechRateType, name="tech_rate_type"), default=TechRateType.HOURLY)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    phone: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    registration: Mapped[str | None] = mapped_column(String(50))
    fuel_consumption_l_per_100km: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10"))
    running_cost_per_km: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("2.50"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    projects: Mapped[list["Project"]] = relationship(back_populates="client")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(255))
    service_type: Mapped[ServiceType] = mapped_column(SAEnum(ServiceType, name="service_type"))
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus, name="project_status"), default=ProjectStatus.QUOTING)
    site_address: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)

    # Costing inputs (snapshot at quote time — survives Settings edits)
    one_way_distance_km: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    return_trips: Mapped[int] = mapped_column(Integer, default=1)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="SET NULL"))
    estimated_hours_on_site: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    estimated_travel_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    overnight_nights: Mapped[int] = mapped_column(Integer, default=0)
    people_on_site: Mapped[int] = mapped_column(Integer, default=1)

    # Rates snapshot (copied from Settings at quote creation for audit)
    diesel_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    lodging_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    per_diem_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    contingency_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=15)
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=25)
    vat_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=15)

    # Computed and stored at save for quick listing
    quoted_total_ex_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    quoted_total_inc_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    # Assigned on first PDF generation: "BSP-Q-0042"
    quote_number: Mapped[str | None] = mapped_column(String(50))

    # Client acceptance of the quote
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by_name: Mapped[str | None] = mapped_column(String(255))

    # Structured materials list + tech assignments stored as JSON (flexible, avoids over-schema)
    # [{name, qty, unit_cost}]
    materials: Mapped[list] = mapped_column(JSON, default=list)
    # [{technician_id, hours}] or [{technician_id, days}]
    tech_assignments: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client: Mapped[Client] = relationship(back_populates="projects")
    vehicle: Mapped[Vehicle | None] = relationship()
    expenses: Mapped[list["Expense"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    activities: Mapped[list["Activity"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Activity.position",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Invoice.issued_at",
    )


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    category: Mapped[ExpenseCategory] = mapped_column(SAEnum(ExpenseCategory, name="expense_category"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    receipt_path: Mapped[str | None] = mapped_column(String(512))
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("technicians.id", ondelete="SET NULL"))
    latitude: Mapped[float | None] = mapped_column()
    longitude: Mapped[float | None] = mapped_column()
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    incurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="expenses")
    technician: Mapped[Technician | None] = relationship()


class ActivityStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    SKIPPED = "skipped"


class Activity(Base):
    """A unit of work inside a project — owner, hours, status, schedule, blocker."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ActivityStatus] = mapped_column(SAEnum(ActivityStatus, name="activity_status"), default=ActivityStatus.PENDING)
    position: Mapped[int] = mapped_column(Integer, default=0)
    estimated_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    scheduled_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocker_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # Techs assigned to this activity (ids)
    assigned_tech_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[Project] = relationship(back_populates="activities")
    time_entries: Mapped[list["TimeEntry"]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="TimeEntry.started_at",
    )


class TimeEntry(Base):
    """A time interval a technician spent on an activity. Auto-created by start/stop."""

    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"))
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    activity: Mapped[Activity] = relationship(back_populates="time_entries")
    technician: Mapped[Technician] = relationship()


class OutboundMessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class OutboundMessage(Base):
    """Queue of outbound messages (WhatsApp, email). Worker picks up queued rows and
    dispatches them via the configured provider. No provider wired yet — plumbing
    only until Meta / Twilio / email SMTP creds are configured in env."""

    __tablename__ = "outbound_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(30), default="whatsapp")  # whatsapp, email, sms
    to_address: Mapped[str] = mapped_column(String(255))  # phone for WA, email for email
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    attachment_path: Mapped[str | None] = mapped_column(String(512))  # e.g. /uploads/xxx.pdf
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    status: Mapped[OutboundMessageStatus] = mapped_column(
        SAEnum(OutboundMessageStatus, name="outbound_message_status"),
        default=OutboundMessageStatus.QUEUED,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    error: Mapped[str | None] = mapped_column(Text)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MonitoringProvider(str, Enum):
    SUNSYNK = "sunsynk"
    SOLAREDGE = "solaredge"
    VICTRON = "victron"
    OTHER = "other"


class MonitoringSite(Base):
    """Client-side inverter/battery system we monitor remotely. One row per installed
    system. Polling worker fetches status from the provider's API (when credentials
    are configured) and raises alerts."""

    __tablename__ = "monitoring_sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    provider: Mapped[MonitoringProvider] = mapped_column(SAEnum(MonitoringProvider, name="monitoring_provider"))
    provider_site_id: Mapped[str] = mapped_column(String(255))
    system_label: Mapped[str] = mapped_column(String(255))
    last_status: Mapped[str | None] = mapped_column(String(50))  # ok, warning, fault, offline
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_payload: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped["Client"] = relationship()
    project: Mapped["Project | None"] = relationship()


class VariationOrder(Base):
    """A signed change-order against an already-accepted quote. Covers you legally
    when scope grows mid-project."""

    __tablename__ = "variation_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    vo_number: Mapped[str] = mapped_column(String(50), unique=True)
    scope_delta: Mapped[str] = mapped_column(Text)  # "Client wants extra outlet in rondavel #3"
    cost_delta_ex_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    vat_pct_snapshot: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=15)
    reason: Mapped[str | None] = mapped_column(Text)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship()


class Trip(Base):
    """SARS-compliant vehicle logbook entry. Every business trip with a vehicle."""

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    trip_date: Mapped[date] = mapped_column(Date)
    from_location: Mapped[str] = mapped_column(String(255))
    to_location: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(String(255))
    odo_start: Mapped[int | None] = mapped_column(Integer)
    odo_end: Mapped[int | None] = mapped_column(Integer)
    business_km: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("technicians.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vehicle: Mapped["Vehicle"] = relationship()
    project: Mapped["Project | None"] = relationship()
    technician: Mapped["Technician | None"] = relationship()


class UserRole(str, Enum):
    OWNER = "owner"
    FOREMAN = "foreman"
    TECH = "tech"
    ACCOUNTANT = "accountant"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), default=UserRole.TECH)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Optional link to a technician record (for field users)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("technicians.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    technician: Mapped["Technician | None"] = relationship()


class InvoiceType(str, Enum):
    DEPOSIT = "deposit"
    PROGRESS = "progress"
    FINAL = "final"
    RETENTION = "retention"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True)
    type: Mapped[InvoiceType] = mapped_column(SAEnum(InvoiceType, name="invoice_type"))
    status: Mapped[InvoiceStatus] = mapped_column(SAEnum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.DRAFT)
    issued_at: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    due_at: Mapped[date] = mapped_column(Date)
    subtotal_ex_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_inc_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    retention_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    retention_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="invoices")
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="Payment.received_at",
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    received_at: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    method: Mapped[str] = mapped_column(String(30), default="eft")
    reference: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="payments")


class ServiceTemplate(Base):
    """A reusable shape for common service types — BOM, activities, markups. Pick one when
    quoting a new project to pre-fill the wizard."""

    __tablename__ = "service_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    service_type: Mapped[ServiceType] = mapped_column(SAEnum(ServiceType, name="service_type"))
    description: Mapped[str | None] = mapped_column(Text)
    default_people_on_site: Mapped[int] = mapped_column(Integer, default=1)
    default_estimated_hours_on_site: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    default_contingency_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=15)
    default_margin_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=25)
    # [{name, qty, unit_cost}]
    materials: Mapped[list] = mapped_column(JSON, default=list)
    # [{title, description, estimated_hours, position}]
    activities: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProjectEventKind(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    NOTE = "note"
    SCOPE_CHANGED = "scope_changed"
    TECH_ADDED = "tech_added"
    TECH_REMOVED = "tech_removed"


class ProjectEvent(Base):
    """Audit log + free-text journal for a project. Every edit writes one of these."""

    __tablename__ = "project_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    kind: Mapped[ProjectEventKind] = mapped_column(SAEnum(ProjectEventKind, name="project_event_kind"))
    summary: Mapped[str] = mapped_column(String(500))
    details: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    quote_before: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    quote_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
