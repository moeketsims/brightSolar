"""Reseed realistic sample data: a 600km install + a local repair, with activities."""

import asyncio
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

from sqlalchemy import delete

from app.db import Base, SessionLocal, engine
from app.auth import hash_password
from app.models import (
    Activity,
    ActivityStatus,
    Client,
    Expense,
    ExpenseCategory,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Payment,
    Project,
    ProjectEvent,
    ProjectEventKind,
    ProjectStatus,
    ServiceTemplate,
    ServiceType,
    Settings,
    TechRateType,
    Technician,
    TimeEntry,
    User,
    UserRole,
    Vehicle,
)
from app.costing import compute_breakdown


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
        # Clear in dependency-safe order
        for table in (Payment, Invoice, TimeEntry, Activity, ProjectEvent, Expense, Project, Client, User, Technician, Vehicle, ServiceTemplate, Settings):
            await s.execute(delete(table))

        settings_row = Settings(
            id=1,
            diesel_price_per_litre=Decimal("22.50"),
            default_lodging_per_night=Decimal("950"),
            default_per_diem=Decimal("350"),
            default_contingency_pct=Decimal("15"),
            default_margin_pct=Decimal("25"),
            vat_pct=Decimal("15"),
            business_name="Bright Solar Power",
            base_address="Johannesburg, Gauteng",
            business_phone="+27 11 555 0100",
            business_email="info@brightsolarpower.co.za",
            business_website="brightsolarpower.co.za",
            business_vat_number="4XX0XXXXXX",
            business_reg_number="2020/XXXXXX/07",
            bank_name="FNB",
            bank_account_name="Bright Solar Power (Pty) Ltd",
            bank_account_number="62XXXXXXXXX",
            bank_branch_code="250655",
            quote_validity_days=30,
            deposit_pct_default=Decimal("50"),
            quote_terms=None,  # use the default boilerplate in the template
        )
        s.add(settings_row)

        v1 = Vehicle(name="Hilux", registration="ABC 123 GP", fuel_consumption_l_per_100km=Decimal("11"), running_cost_per_km=Decimal("2.80"))
        v2 = Vehicle(name="Ranger", registration="DEF 456 GP", fuel_consumption_l_per_100km=Decimal("12"), running_cost_per_km=Decimal("3.00"))
        s.add_all([v1, v2])

        t1 = Technician(name="Sipho Dlamini", rate_type=TechRateType.HOURLY, hourly_rate=Decimal("280"), daily_rate=Decimal("2200"), phone="+27 82 111 0001")
        t2 = Technician(name="Pieter van Wyk", rate_type=TechRateType.HOURLY, hourly_rate=Decimal("320"), daily_rate=Decimal("2600"), phone="+27 82 111 0002")
        t3 = Technician(name="Lerato Nkosi (apprentice)", rate_type=TechRateType.HOURLY, hourly_rate=Decimal("180"), daily_rate=Decimal("1400"), phone="+27 82 111 0003")
        s.add_all([t1, t2, t3])
        await s.flush()

        # Default users — one per role
        owner_user = User(
            email="owner@brightsolarpower.co.za",
            name="Owner",
            password_hash=hash_password("owner123"),
            role=UserRole.OWNER,
        )
        foreman_user = User(
            email="foreman@brightsolarpower.co.za",
            name="Foreman",
            password_hash=hash_password("foreman123"),
            role=UserRole.FOREMAN,
        )
        tech_user = User(
            email="sipho@brightsolarpower.co.za",
            name="Sipho Dlamini",
            password_hash=hash_password("tech123"),
            role=UserRole.TECH,
            technician_id=t1.id,
        )
        accountant_user = User(
            email="accountant@brightsolarpower.co.za",
            name="Accountant",
            password_hash=hash_password("acct123"),
            role=UserRole.ACCOUNTANT,
        )
        s.add_all([owner_user, foreman_user, tech_user, accountant_user])

        c1 = Client(name="Kalahari Game Lodge", phone="+27 54 555 0101", address="Upington, Northern Cape")
        c2 = Client(name="Zinhle Ndlovu", phone="+27 83 555 0202", address="Rosebank, JHB")
        c3 = Client(name="Van der Merwe Farm (Bloemfontein)", phone="+27 51 555 0303", address="Bloemfontein, Free State")
        s.add_all([c1, c2, c3])
        await s.flush()

        p1 = Project(
            client_id=c1.id,
            title="20kW off-grid hybrid system — Upington",
            service_type=ServiceType.SOLAR_INSTALL,
            status=ProjectStatus.IN_PROGRESS,
            site_address="Kalahari Game Lodge, R360, Upington",
            description="Full off-grid: 20kW PV, 60kWh LFP battery bank, 15kW hybrid inverter. Remote site, long travel.",
            one_way_distance_km=Decimal("600"),
            return_trips=1,
            vehicle_id=v1.id,
            estimated_hours_on_site=Decimal("32"),
            estimated_travel_hours=Decimal("14"),
            overnight_nights=2,
            people_on_site=2,
            diesel_price_snapshot=settings_row.diesel_price_per_litre,
            lodging_rate_snapshot=settings_row.default_lodging_per_night,
            per_diem_snapshot=settings_row.default_per_diem,
            contingency_pct=Decimal("15"),
            margin_pct=Decimal("25"),
            vat_pct=Decimal("15"),
            materials=[
                {"name": "450W mono PV panel", "qty": 44, "unit_cost": "2200"},
                {"name": "15kW hybrid inverter", "qty": 1, "unit_cost": "48000"},
                {"name": "15kWh LFP battery module", "qty": 4, "unit_cost": "52000"},
                {"name": "DC cable 6mm² (per m)", "qty": 120, "unit_cost": "22"},
                {"name": "MC4 connector pair", "qty": 30, "unit_cost": "45"},
                {"name": "DC isolator", "qty": 4, "unit_cost": "650"},
                {"name": "Mounting rails + feet kit", "qty": 1, "unit_cost": "18500"},
            ],
            tech_assignments=[
                {"technician_id": t1.id, "hours": 32},
                {"technician_id": t2.id, "hours": 32},
            ],
        )

        p2 = Project(
            client_id=c2.id,
            title="Inverter fault callout",
            service_type=ServiceType.REPAIR,
            status=ProjectStatus.QUOTED,
            site_address="Rosebank, JHB",
            description="Hybrid inverter tripping under load, likely MCB fault.",
            one_way_distance_km=Decimal("18"),
            return_trips=1,
            vehicle_id=v2.id,
            estimated_hours_on_site=Decimal("3"),
            estimated_travel_hours=Decimal("1.5"),
            overnight_nights=0,
            people_on_site=1,
            diesel_price_snapshot=settings_row.diesel_price_per_litre,
            lodging_rate_snapshot=settings_row.default_lodging_per_night,
            per_diem_snapshot=settings_row.default_per_diem,
            contingency_pct=Decimal("10"),
            margin_pct=Decimal("30"),
            vat_pct=Decimal("15"),
            materials=[{"name": "63A AC MCB", "qty": 1, "unit_cost": "450"}],
            tech_assignments=[{"technician_id": t1.id, "hours": 3}],
        )
        # Project 3 — completed install, closed out 2 weeks ago. Has deltas worth learning from.
        p3 = Project(
            client_id=c3.id,
            title="10kW grid-tied solar — Van der Merwe Farm",
            service_type=ServiceType.SOLAR_INSTALL,
            status=ProjectStatus.COMPLETED,
            site_address="Bloemfontein, Free State",
            description="10kW roof-mounted PV with grid feedback. 2 days on site, 1 overnight.",
            one_way_distance_km=Decimal("400"),
            return_trips=1,
            vehicle_id=v1.id,
            estimated_hours_on_site=Decimal("16"),
            estimated_travel_hours=Decimal("9"),
            overnight_nights=1,
            people_on_site=2,
            diesel_price_snapshot=Decimal("21.80"),  # price from 2 weeks ago
            lodging_rate_snapshot=Decimal("950"),
            per_diem_snapshot=Decimal("350"),
            contingency_pct=Decimal("15"),
            margin_pct=Decimal("25"),
            vat_pct=Decimal("15"),
            materials=[
                {"name": "450W mono PV panel", "qty": 22, "unit_cost": "2200"},
                {"name": "10kW grid-tie inverter", "qty": 1, "unit_cost": "32000"},
                {"name": "DC cable 6mm² (per m)", "qty": 60, "unit_cost": "22"},
                {"name": "Mounting rails + feet kit", "qty": 1, "unit_cost": "12500"},
            ],
            tech_assignments=[
                {"technician_id": t1.id, "hours": 16},
                {"technician_id": t2.id, "hours": 16},
            ],
        )

        s.add_all([p1, p2, p3])
        await s.flush()

        for p in (p1, p2, p3):
            vehicle = v1 if p.vehicle_id == v1.id else v2
            bd = compute_breakdown(p, vehicle, {t1.id: t1, t2.id: t2, t3.id: t3})
            p.quoted_total_ex_vat = Decimal(str(bd["total_ex_vat"]))
            p.quoted_total_inc_vat = Decimal(str(bd["total_inc_vat"]))

        # Activities for Upington project: realistic multi-day workstream
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        tomorrow = today + timedelta(days=1)

        a1 = Activity(
            project_id=p1.id,
            title="Site survey & roof structural check",
            description="Confirm roof can take 44 panels; mark fixing points.",
            status=ActivityStatus.DONE,
            position=0,
            estimated_hours=Decimal("4"),
            scheduled_date=two_days_ago,
            due_date=two_days_ago,
            started_at=datetime.now(timezone.utc) - timedelta(days=2, hours=6),
            completed_at=datetime.now(timezone.utc) - timedelta(days=2, hours=2),
            assigned_tech_ids=[t1.id],
        )
        a2 = Activity(
            project_id=p1.id,
            title="Pack truck + drive Upington (600km)",
            description="Load panels, batteries, inverter, tools. Leave base 04:00.",
            status=ActivityStatus.DONE,
            position=1,
            estimated_hours=Decimal("8"),
            scheduled_date=yesterday,
            due_date=yesterday,
            started_at=datetime.now(timezone.utc) - timedelta(days=1, hours=10),
            completed_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2),
            assigned_tech_ids=[t1.id, t2.id],
        )
        a3 = Activity(
            project_id=p1.id,
            title="Mount 44 × 450W panels on north roof",
            description="Rail mounting, panel fitting, earthing. 2-man job.",
            status=ActivityStatus.IN_PROGRESS,
            position=2,
            estimated_hours=Decimal("12"),
            scheduled_date=today,
            due_date=today,
            started_at=datetime.now(timezone.utc) - timedelta(hours=3),
            assigned_tech_ids=[t1.id, t2.id],
        )
        a4 = Activity(
            project_id=p1.id,
            title="Install battery rack + inverter in plant room",
            description="Wall-mount inverter, bolt-down battery rack, DC + AC wiring.",
            status=ActivityStatus.SCHEDULED,
            position=3,
            estimated_hours=Decimal("10"),
            scheduled_date=tomorrow,
            due_date=tomorrow,
            assigned_tech_ids=[t1.id, t2.id],
        )
        a5 = Activity(
            project_id=p1.id,
            title="Commissioning + client handover training",
            description="Boot system, test loads, train lodge manager on monitoring app.",
            status=ActivityStatus.PENDING,
            position=4,
            estimated_hours=Decimal("4"),
            scheduled_date=tomorrow,
            due_date=tomorrow,
            assigned_tech_ids=[t2.id],
        )
        a6 = Activity(
            project_id=p1.id,
            title="Generate as-built documentation + CoC",
            description="Wiring diagram updates, PV GreenCard, CoC paperwork.",
            status=ActivityStatus.PENDING,
            position=5,
            estimated_hours=Decimal("2"),
            due_date=today + timedelta(days=3),
            assigned_tech_ids=[t1.id],
        )

        # Project 2 activities (local repair, simpler)
        a7 = Activity(
            project_id=p2.id,
            title="Diagnose inverter fault",
            description="Check logs, measure DC/AC, inspect MCB.",
            status=ActivityStatus.SCHEDULED,
            position=0,
            estimated_hours=Decimal("1"),
            scheduled_date=today,
            due_date=today,
            assigned_tech_ids=[t1.id],
        )
        a8 = Activity(
            project_id=p2.id,
            title="Replace 63A MCB",
            status=ActivityStatus.PENDING,
            position=1,
            estimated_hours=Decimal("1"),
            scheduled_date=today,
            assigned_tech_ids=[t1.id],
        )
        a9 = Activity(
            project_id=p2.id,
            title="Load test + client sign-off",
            status=ActivityStatus.PENDING,
            position=2,
            estimated_hours=Decimal("1"),
            scheduled_date=today,
            assigned_tech_ids=[t1.id],
        )

        # Activities for the completed Bloemfontein project
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
        a10 = Activity(
            project_id=p3.id,
            title="Site survey",
            status=ActivityStatus.DONE,
            position=0,
            estimated_hours=Decimal("3"),
            started_at=two_weeks_ago - timedelta(days=3),
            completed_at=two_weeks_ago - timedelta(days=3) + timedelta(hours=3),
            assigned_tech_ids=[t1.id],
        )
        a11 = Activity(
            project_id=p3.id,
            title="Pack + drive Bloemfontein",
            status=ActivityStatus.DONE,
            position=1,
            estimated_hours=Decimal("6"),
            started_at=two_weeks_ago - timedelta(hours=7),
            completed_at=two_weeks_ago - timedelta(hours=0.5),
            assigned_tech_ids=[t1.id, t2.id],
        )
        a12 = Activity(
            project_id=p3.id,
            title="Mount 22 panels + rails",
            status=ActivityStatus.DONE,
            position=2,
            estimated_hours=Decimal("8"),
            started_at=two_weeks_ago,
            completed_at=two_weeks_ago + timedelta(hours=11),  # overran by 3h
            assigned_tech_ids=[t1.id, t2.id],
        )
        a13 = Activity(
            project_id=p3.id,
            title="Install inverter + commissioning",
            status=ActivityStatus.DONE,
            position=3,
            estimated_hours=Decimal("5"),
            started_at=two_weeks_ago + timedelta(days=1),
            completed_at=two_weeks_ago + timedelta(days=1, hours=4),  # came in under by 1h
            assigned_tech_ids=[t1.id],
        )

        s.add_all([a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13])
        await s.flush()

        # Time entries on completed activities + the running one
        s.add_all([
            TimeEntry(
                activity_id=a1.id,
                technician_id=t1.id,
                started_at=datetime.now(timezone.utc) - timedelta(days=2, hours=6),
                ended_at=datetime.now(timezone.utc) - timedelta(days=2, hours=2),
                hours=Decimal("4.0"),
            ),
            TimeEntry(
                activity_id=a2.id,
                technician_id=t1.id,
                started_at=datetime.now(timezone.utc) - timedelta(days=1, hours=10),
                ended_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2),
                hours=Decimal("8.0"),
            ),
            TimeEntry(
                activity_id=a2.id,
                technician_id=t2.id,
                started_at=datetime.now(timezone.utc) - timedelta(days=1, hours=10),
                ended_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2),
                hours=Decimal("8.0"),
            ),
            # Running clock on a3 (mounting panels)
            TimeEntry(
                activity_id=a3.id,
                technician_id=t1.id,
                started_at=datetime.now(timezone.utc) - timedelta(hours=3),
                ended_at=None,
                hours=None,
            ),
            TimeEntry(
                activity_id=a3.id,
                technician_id=t2.id,
                started_at=datetime.now(timezone.utc) - timedelta(hours=3),
                ended_at=None,
                hours=None,
            ),
            # Bloemfontein project — realistic actuals against activities
            TimeEntry(activity_id=a10.id, technician_id=t1.id, started_at=two_weeks_ago - timedelta(days=3), ended_at=two_weeks_ago - timedelta(days=3) + timedelta(hours=3), hours=Decimal("3.0")),
            TimeEntry(activity_id=a11.id, technician_id=t1.id, started_at=two_weeks_ago - timedelta(hours=7), ended_at=two_weeks_ago - timedelta(hours=0.5), hours=Decimal("6.5")),
            TimeEntry(activity_id=a11.id, technician_id=t2.id, started_at=two_weeks_ago - timedelta(hours=7), ended_at=two_weeks_ago - timedelta(hours=0.5), hours=Decimal("6.5")),
            # Mount panels overran by 3 hrs per tech
            TimeEntry(activity_id=a12.id, technician_id=t1.id, started_at=two_weeks_ago, ended_at=two_weeks_ago + timedelta(hours=11), hours=Decimal("11.0")),
            TimeEntry(activity_id=a12.id, technician_id=t2.id, started_at=two_weeks_ago, ended_at=two_weeks_ago + timedelta(hours=11), hours=Decimal("11.0")),
            # Commissioning came in under
            TimeEntry(activity_id=a13.id, technician_id=t1.id, started_at=two_weeks_ago + timedelta(days=1), ended_at=two_weeks_ago + timedelta(days=1, hours=4), hours=Decimal("4.0")),
        ])

        # Expenses
        s.add_all([
            Expense(project_id=p1.id, category=ExpenseCategory.DIESEL, amount=Decimal("1380.00"), description="Engen, Kimberley — outbound fill-up", technician_id=t1.id, latitude=-28.739, longitude=24.756),
            Expense(project_id=p1.id, category=ExpenseCategory.MEALS, amount=Decimal("245.00"), description="Wimpy lunch (2 pax)", technician_id=t1.id),
            Expense(project_id=p1.id, category=ExpenseCategory.LODGING, amount=Decimal("1900.00"), description="Upington Protea Hotel — 1 night × 2 rooms", technician_id=t2.id),
            Expense(project_id=p1.id, category=ExpenseCategory.DIESEL, amount=Decimal("1420.00"), description="Top-up, Upington", technician_id=t1.id, latitude=-28.448, longitude=21.256),
            Expense(project_id=p1.id, category=ExpenseCategory.TOLLS, amount=Decimal("185.50"), description="N12 tolls outbound", technician_id=t1.id),
            # Bloemfontein project actuals — showing realistic drift from quote
            # Diesel: 800km × 11L/100km × R21.80 = 88L × R21.80 = R1918 expected.
            # Actual spent R2,240 — implies ~11.5 L/100km (vehicle uses more than 11 L under load).
            Expense(project_id=p3.id, category=ExpenseCategory.DIESEL, amount=Decimal("1120.00"), description="Fill-up outbound, Parys 1-Stop", technician_id=t1.id, incurred_at=two_weeks_ago - timedelta(hours=5)),
            Expense(project_id=p3.id, category=ExpenseCategory.DIESEL, amount=Decimal("1120.00"), description="Fill-up return, Kroonstad", technician_id=t1.id, incurred_at=two_weeks_ago + timedelta(days=1, hours=6)),
            # Lodging actually came in AT budget (R950 × 2 rooms × 1 night = R1900) — no drift here
            Expense(project_id=p3.id, category=ExpenseCategory.LODGING, amount=Decimal("1900.00"), description="Formule 1 Bloemfontein × 2 rooms", technician_id=t1.id, incurred_at=two_weeks_ago),
            # Per-diem overran — R420/person/night instead of R350
            Expense(project_id=p3.id, category=ExpenseCategory.MEALS, amount=Decimal("840.00"), description="Dinner + breakfast × 2 pax", technician_id=t1.id, incurred_at=two_weeks_ago),
            Expense(project_id=p3.id, category=ExpenseCategory.TOLLS, amount=Decimal("140.00"), description="N1 tolls", technician_id=t1.id, incurred_at=two_weeks_ago - timedelta(hours=2)),
            Expense(project_id=p3.id, category=ExpenseCategory.MATERIALS, amount=Decimal("85400.00"), description="Panels, inverter, rails, cable (as BOM)", technician_id=t1.id, incurred_at=two_weeks_ago - timedelta(days=1)),
            Expense(project_id=p3.id, category=ExpenseCategory.MATERIALS, amount=Decimal("2800.00"), description="Extra DB-box parts — BOM was light", technician_id=t1.id, incurred_at=two_weeks_ago + timedelta(hours=8)),
        ])

        # Activity / status events
        s.add_all([
            ProjectEvent(project_id=p1.id, kind=ProjectEventKind.CREATED, summary=f"Project created — quoted at R{p1.quoted_total_inc_vat:,.2f} inc VAT", quote_after=p1.quoted_total_inc_vat),
            ProjectEvent(project_id=p1.id, kind=ProjectEventKind.STATUS_CHANGED, summary="Status: quoted → accepted — client signed quote"),
            ProjectEvent(project_id=p1.id, kind=ProjectEventKind.SCOPE_CHANGED, summary="Activity completed: Site survey & roof structural check"),
            ProjectEvent(project_id=p1.id, kind=ProjectEventKind.SCOPE_CHANGED, summary="Activity completed: Pack truck + drive Upington (600km)"),
            ProjectEvent(project_id=p1.id, kind=ProjectEventKind.NOTE, summary="Crew arrived on site 06:15 — roof access easier than expected", note="Crew arrived on site 06:15 — roof access easier than expected, may finish one day early."),
            ProjectEvent(project_id=p1.id, kind=ProjectEventKind.SCOPE_CHANGED, summary="Sipho Dlamini started: Mount 44 × 450W panels on north roof"),
            ProjectEvent(project_id=p1.id, kind=ProjectEventKind.SCOPE_CHANGED, summary="Pieter van Wyk started: Mount 44 × 450W panels on north roof"),
            ProjectEvent(project_id=p2.id, kind=ProjectEventKind.CREATED, summary=f"Project created — quoted at R{p2.quoted_total_inc_vat:,.2f} inc VAT", quote_after=p2.quoted_total_inc_vat),
            ProjectEvent(project_id=p3.id, kind=ProjectEventKind.CREATED, summary=f"Project created — quoted at R{p3.quoted_total_inc_vat:,.2f} inc VAT", quote_after=p3.quoted_total_inc_vat),
            ProjectEvent(project_id=p3.id, kind=ProjectEventKind.STATUS_CHANGED, summary="Status: in_progress → completed — client signed off, awaiting final invoice"),
        ])

        # Service templates — the bottled knowledge for rapid quoting
        tpl_10kw = ServiceTemplate(
            name="10kW grid-tied solar install",
            service_type=ServiceType.SOLAR_INSTALL,
            description="Roof-mounted 10kW PV, grid-tied inverter, no batteries. Typical 2-day job, 1 tech + 1 apprentice.",
            default_people_on_site=2,
            default_estimated_hours_on_site=Decimal("16"),
            default_contingency_pct=Decimal("15"),
            default_margin_pct=Decimal("25"),
            materials=[
                {"name": "450W mono PV panel", "qty": 22, "unit_cost": "2200"},
                {"name": "10kW grid-tie inverter", "qty": 1, "unit_cost": "32000"},
                {"name": "DC cable 6mm² (per m)", "qty": 60, "unit_cost": "22"},
                {"name": "AC cable 16mm² (per m)", "qty": 20, "unit_cost": "65"},
                {"name": "MC4 connector pair", "qty": 15, "unit_cost": "45"},
                {"name": "DC isolator", "qty": 2, "unit_cost": "650"},
                {"name": "Mounting rails + feet kit", "qty": 1, "unit_cost": "12500"},
                {"name": "AC MCB + DB-box accessories", "qty": 1, "unit_cost": "1800"},
            ],
            activities=[
                {"title": "Site survey & roof structural check", "description": "Confirm roof integrity, mark fixing points.", "estimated_hours": "3", "position": 0},
                {"title": "Pack truck + travel to site", "description": "Load panels, inverter, rails, tools.", "estimated_hours": "4", "position": 1},
                {"title": "Mount 22 panels + rails", "description": "Rail mounting, panel fitting, earthing.", "estimated_hours": "8", "position": 2},
                {"title": "DC wiring + inverter install", "description": "String wiring, inverter wall-mount.", "estimated_hours": "4", "position": 3},
                {"title": "AC tie-in + commissioning", "description": "DB-box tie-in, grid sync, load test.", "estimated_hours": "3", "position": 4},
                {"title": "Client handover + CoC paperwork", "description": "Train client, issue CoC + PV GreenCard.", "estimated_hours": "2", "position": 5},
            ],
        )

        tpl_backup = ServiceTemplate(
            name="5kW home backup system",
            service_type=ServiceType.BACKUP_INSTALL,
            description="5kW hybrid inverter + lithium battery, wired to essential circuits. 1-day install.",
            default_people_on_site=2,
            default_estimated_hours_on_site=Decimal("9"),
            default_contingency_pct=Decimal("15"),
            default_margin_pct=Decimal("28"),
            materials=[
                {"name": "5kW hybrid inverter", "qty": 1, "unit_cost": "24000"},
                {"name": "5kWh LFP battery", "qty": 1, "unit_cost": "38000"},
                {"name": "Battery cable 35mm² (per m)", "qty": 6, "unit_cost": "180"},
                {"name": "AC MCB + essentials board", "qty": 1, "unit_cost": "2400"},
                {"name": "Labelling + terminations kit", "qty": 1, "unit_cost": "650"},
            ],
            activities=[
                {"title": "Site walk + load list", "description": "Identify essential circuits.", "estimated_hours": "1", "position": 0},
                {"title": "Mount inverter + battery", "description": "Wall-mount inverter, bolt battery.", "estimated_hours": "3", "position": 1},
                {"title": "Essentials DB wiring", "description": "Split essentials to backup DB.", "estimated_hours": "3", "position": 2},
                {"title": "Commissioning + UPS test", "description": "Confirm failover on grid drop.", "estimated_hours": "1.5", "position": 3},
                {"title": "Client training + CoC", "description": "App setup, warranty cards, CoC.", "estimated_hours": "0.5", "position": 4},
            ],
        )

        tpl_repair = ServiceTemplate(
            name="Inverter fault callout (repair)",
            service_type=ServiceType.REPAIR,
            description="Diagnose + fix inverter fault on site. Typical 3h on site, 1 tech.",
            default_people_on_site=1,
            default_estimated_hours_on_site=Decimal("3"),
            default_contingency_pct=Decimal("10"),
            default_margin_pct=Decimal("35"),
            materials=[
                {"name": "Replacement MCB", "qty": 1, "unit_cost": "450"},
                {"name": "Labelling + terminations", "qty": 1, "unit_cost": "200"},
            ],
            activities=[
                {"title": "Diagnose fault", "description": "Check logs, measurements, inspect.", "estimated_hours": "1", "position": 0},
                {"title": "Replace faulty part", "estimated_hours": "1", "position": 1},
                {"title": "Load test + client sign-off", "estimated_hours": "1", "position": 2},
            ],
        )

        s.add_all([tpl_10kw, tpl_backup, tpl_repair])

        await s.flush()

        # ---- Invoices & payments: realistic scenario on the Bloemfontein project ----
        # Deposit invoice — fully paid
        dep_subtotal = (Decimal(p3.quoted_total_inc_vat) * Decimal("0.5") / Decimal("1.15")).quantize(Decimal("0.01"))
        dep_vat = (dep_subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
        dep_total = (dep_subtotal + dep_vat).quantize(Decimal("0.01"))
        inv_dep = Invoice(
            project_id=p3.id,
            invoice_number=f"BSP-INV-{date.today().year}-0001",
            type=InvoiceType.DEPOSIT,
            status=InvoiceStatus.PAID,
            issued_at=date.today() - timedelta(days=30),
            due_at=date.today() - timedelta(days=15),
            subtotal_ex_vat=dep_subtotal,
            vat=dep_vat,
            total_inc_vat=dep_total,
            description="50% deposit on accepted quotation BSP-Q-0003",
            sent_at=datetime.now(timezone.utc) - timedelta(days=29),
        )

        # Final invoice — sent, now overdue (due 5 days ago, not yet paid)
        final_subtotal = (Decimal(p3.quoted_total_inc_vat) / Decimal("1.15") - dep_subtotal).quantize(Decimal("0.01"))
        final_vat = (final_subtotal * Decimal("0.15")).quantize(Decimal("0.01"))
        final_total = (final_subtotal + final_vat).quantize(Decimal("0.01"))
        inv_final = Invoice(
            project_id=p3.id,
            invoice_number=f"BSP-INV-{date.today().year}-0002",
            type=InvoiceType.FINAL,
            status=InvoiceStatus.SENT,
            issued_at=date.today() - timedelta(days=20),
            due_at=date.today() - timedelta(days=5),  # 5 days overdue
            subtotal_ex_vat=final_subtotal,
            vat=final_vat,
            total_inc_vat=final_total,
            description="Final invoice on commissioning",
            sent_at=datetime.now(timezone.utc) - timedelta(days=19),
        )

        s.add_all([inv_dep, inv_final])
        await s.flush()

        # Payment for the deposit
        s.add(Payment(
            invoice_id=inv_dep.id,
            received_at=date.today() - timedelta(days=26),
            amount=dep_total,
            method="eft",
            reference=inv_dep.invoice_number,
            note="Deposit EFT received",
        ))

        # Events
        s.add_all([
            ProjectEvent(project_id=p3.id, kind=ProjectEventKind.NOTE, summary=f"Invoice {inv_dep.invoice_number} drafted — R{dep_total:,.2f}"),
            ProjectEvent(project_id=p3.id, kind=ProjectEventKind.NOTE, summary=f"Payment R{dep_total:,.2f} received on {inv_dep.invoice_number} — invoice PAID"),
            ProjectEvent(project_id=p3.id, kind=ProjectEventKind.NOTE, summary=f"Invoice {inv_final.invoice_number} sent — R{final_total:,.2f}"),
        ])

        await s.commit()
        print(f"Seeded: settings, 3 templates, 2 vehicles, 3 techs, 3 clients, 3 projects, 13 activities, 10 time entries, 12 expenses, 13 events, 2 invoices (1 paid, 1 overdue), 1 payment")


if __name__ == "__main__":
    asyncio.run(seed())
