"use client";

import { useEffect, useState } from "react";
import {
  api,
  type Settings,
  type Technician,
  type Vehicle,
} from "@/lib/api";
import TemplatesPanel from "./templates-panel";

export default function SettingsPage() {
  const [s, setS] = useState<Settings | null>(null);
  const [techs, setTechs] = useState<Technician[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  async function reload() {
    const [ss, tt, vv] = await Promise.all([
      api.settings(),
      api.listTechnicians(),
      api.listVehicles(),
    ]);
    setS(ss);
    setTechs(tt);
    setVehicles(vv);
  }

  useEffect(() => {
    reload();
  }, []);

  async function saveSettings(e: React.FormEvent) {
    e.preventDefault();
    if (!s) return;
    await api.updateSettings(s);
    setMsg("Saved");
    setTimeout(() => setMsg(null), 1500);
  }

  async function addTech(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await api.createTechnician({
      name: String(fd.get("name")),
      rate_type: String(fd.get("rate_type")) as "hourly" | "daily",
      hourly_rate: String(fd.get("hourly_rate") || "0"),
      daily_rate: String(fd.get("daily_rate") || "0"),
      phone: String(fd.get("phone") || ""),
    });
    (e.currentTarget as HTMLFormElement).reset();
    await reload();
  }

  async function addVehicle(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await api.createVehicle({
      name: String(fd.get("name")),
      registration: String(fd.get("registration") || ""),
      fuel_consumption_l_per_100km: String(fd.get("fuel") || "10"),
      running_cost_per_km: String(fd.get("run_cost") || "2.5"),
    });
    (e.currentTarget as HTMLFormElement).reset();
    await reload();
  }

  if (!s) return <div>Loading…</div>;

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h2 className="text-3xl font-semibold">Settings</h2>
        <p className="text-[var(--muted)] text-sm">
          Default rates used by the costing engine. Change these and future quotes use the new numbers
          — existing quotes keep their snapshot so history stays honest.
        </p>
      </div>

      <form onSubmit={saveSettings} className="card p-5 space-y-4">
        <div className="flex justify-between items-baseline">
          <h3 className="font-semibold">Global rates</h3>
          {msg && <span className="text-xs text-[var(--good)]">{msg}</span>}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <Field label="Diesel price (R per litre)">
            <input
              type="number"
              step="0.01"
              value={s.diesel_price_per_litre}
              onChange={(e) => setS({ ...s, diesel_price_per_litre: e.target.value })}
            />
          </Field>
          <Field label="Lodging per night (R)">
            <input
              type="number"
              step="1"
              value={s.default_lodging_per_night}
              onChange={(e) => setS({ ...s, default_lodging_per_night: e.target.value })}
            />
          </Field>
          <Field label="Per diem per day (R)">
            <input
              type="number"
              step="1"
              value={s.default_per_diem}
              onChange={(e) => setS({ ...s, default_per_diem: e.target.value })}
            />
          </Field>
          <Field label="Default contingency %">
            <input
              type="number"
              step="0.5"
              value={s.default_contingency_pct}
              onChange={(e) => setS({ ...s, default_contingency_pct: e.target.value })}
            />
          </Field>
          <Field label="Default target margin %">
            <input
              type="number"
              step="0.5"
              value={s.default_margin_pct}
              onChange={(e) => setS({ ...s, default_margin_pct: e.target.value })}
            />
          </Field>
          <Field label="VAT %">
            <input
              type="number"
              step="0.5"
              value={s.vat_pct}
              onChange={(e) => setS({ ...s, vat_pct: e.target.value })}
            />
          </Field>
        </div>

        <button className="bg-[var(--brand)] text-black font-medium px-4 py-2 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white">
          Save rates
        </button>
      </form>

      <form onSubmit={saveSettings} className="card p-5 space-y-4">
        <div>
          <h3 className="font-semibold">Business & banking details</h3>
          <p className="text-xs text-[var(--muted)] mt-1">
            Used on quote and invoice PDFs. Fill these in so clients see your proper details.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Business name">
            <input value={s.business_name} onChange={(e) => setS({ ...s, business_name: e.target.value })} />
          </Field>
          <Field label="Base address">
            <input value={s.base_address || ""} onChange={(e) => setS({ ...s, base_address: e.target.value })} />
          </Field>
          <Field label="Phone">
            <input value={s.business_phone || ""} onChange={(e) => setS({ ...s, business_phone: e.target.value })} />
          </Field>
          <Field label="Email">
            <input type="email" value={s.business_email || ""} onChange={(e) => setS({ ...s, business_email: e.target.value })} />
          </Field>
          <Field label="Website">
            <input value={s.business_website || ""} onChange={(e) => setS({ ...s, business_website: e.target.value })} />
          </Field>
          <Field label="Company reg number">
            <input value={s.business_reg_number || ""} onChange={(e) => setS({ ...s, business_reg_number: e.target.value })} />
          </Field>
          <Field label="VAT number">
            <input value={s.business_vat_number || ""} onChange={(e) => setS({ ...s, business_vat_number: e.target.value })} />
          </Field>
        </div>

        <div>
          <h4 className="text-sm font-semibold mt-2">Banking (for client deposit payments)</h4>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Bank">
            <input value={s.bank_name || ""} onChange={(e) => setS({ ...s, bank_name: e.target.value })} />
          </Field>
          <Field label="Account name">
            <input value={s.bank_account_name || ""} onChange={(e) => setS({ ...s, bank_account_name: e.target.value })} />
          </Field>
          <Field label="Account number">
            <input value={s.bank_account_number || ""} onChange={(e) => setS({ ...s, bank_account_number: e.target.value })} />
          </Field>
          <Field label="Branch code">
            <input value={s.bank_branch_code || ""} onChange={(e) => setS({ ...s, bank_branch_code: e.target.value })} />
          </Field>
        </div>

        <div>
          <h4 className="text-sm font-semibold mt-2">Quote defaults</h4>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <Field label="Quote validity (days)">
            <input type="number" min={1} value={s.quote_validity_days} onChange={(e) => setS({ ...s, quote_validity_days: Number(e.target.value) })} />
          </Field>
          <Field label="Deposit % on acceptance">
            <input type="number" min={0} max={100} step={0.5} value={s.deposit_pct_default} onChange={(e) => setS({ ...s, deposit_pct_default: e.target.value })} />
          </Field>
        </div>
        <Field label="Quote T&Cs (leave blank for the default boilerplate)">
          <textarea
            rows={4}
            placeholder="· Validity...\n· Deposit...\n· Warranty..."
            value={s.quote_terms || ""}
            onChange={(e) => setS({ ...s, quote_terms: e.target.value })}
          />
        </Field>

        <button className="bg-[var(--brand)] text-black font-medium px-4 py-2 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white">
          Save business details
        </button>
      </form>

      <div className="card p-5 space-y-4">
        <h3 className="font-semibold">Technicians</h3>
        <div className="space-y-1">
          {techs.map((t) => (
            <div key={t.id} className="flex justify-between items-center py-1.5 border-b border-[var(--border)] last:border-b-0">
              <div>
                <p className="text-sm">{t.name}</p>
                <p className="text-xs text-[var(--muted)]">{t.phone || "—"}</p>
              </div>
              <p className="text-sm">
                R{t.hourly_rate}/h · R{t.daily_rate}/day
              </p>
            </div>
          ))}
        </div>
        <form onSubmit={addTech} className="grid grid-cols-2 md:grid-cols-6 gap-2">
          <input name="name" placeholder="Name" required />
          <select name="rate_type" defaultValue="hourly">
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
          </select>
          <input name="hourly_rate" type="number" step="0.01" placeholder="R/hr" />
          <input name="daily_rate" type="number" step="0.01" placeholder="R/day" />
          <input name="phone" placeholder="Phone" />
          <button className="bg-[var(--brand)] text-black font-medium rounded-lg text-sm">+ Add tech</button>
        </form>
      </div>

      <TemplatesPanel />

      <div className="card p-5 space-y-4">
        <h3 className="font-semibold">Vehicles</h3>
        <div className="space-y-1">
          {vehicles.map((v) => (
            <div key={v.id} className="flex justify-between items-center py-1.5 border-b border-[var(--border)] last:border-b-0">
              <div>
                <p className="text-sm">{v.name}</p>
                <p className="text-xs text-[var(--muted)]">{v.registration || "—"}</p>
              </div>
              <p className="text-sm">
                {v.fuel_consumption_l_per_100km} L/100km · R{v.running_cost_per_km}/km
              </p>
            </div>
          ))}
        </div>
        <form onSubmit={addVehicle} className="grid grid-cols-2 md:grid-cols-5 gap-2">
          <input name="name" placeholder="Name (e.g. Hilux)" required />
          <input name="registration" placeholder="Reg" />
          <input name="fuel" type="number" step="0.1" placeholder="L/100km" />
          <input name="run_cost" type="number" step="0.01" placeholder="R/km wear" />
          <button className="bg-[var(--brand)] text-black font-medium rounded-lg text-sm">+ Add vehicle</button>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
