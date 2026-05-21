"use client";

import { useEffect, useMemo, useState } from "react";
import {
  api,
  formatZAR,
  formatZARPrecise,
  type Client,
  type CostBreakdown,
  type MaterialLine,
  type ProjectInputs,
  type ServiceTemplate,
  type ServiceType,
  type TechAssignment,
  type TemplateActivity,
  type Technician,
  type Vehicle,
} from "@/lib/api";

const services: { value: ServiceType; label: string }[] = [
  { value: "solar_install", label: "Solar install" },
  { value: "backup_install", label: "Backup install" },
  { value: "inverter", label: "Inverter work" },
  { value: "battery", label: "Battery work" },
  { value: "maintenance", label: "Maintenance" },
  { value: "repair", label: "Repair / callout" },
  { value: "inspection", label: "Inspection" },
  { value: "other", label: "Other" },
];

export function emptyInputs(): ProjectInputs {
  return {
    client_id: 0,
    title: "",
    service_type: "backup_install",
    site_address: "",
    description: "",
    one_way_distance_km: 0,
    return_trips: 1,
    vehicle_id: null,
    estimated_hours_on_site: 0,
    estimated_travel_hours: 0,
    overnight_nights: 0,
    people_on_site: 1,
    contingency_pct: null,
    margin_pct: null,
    materials: [],
    tech_assignments: [],
    initial_activities: [],
    from_template_id: null,
  };
}

export function ProjectForm({
  initial,
  submitLabel = "Save",
  onSubmit,
  busy,
  err,
  locked,
  showTemplatePicker,
}: {
  initial: ProjectInputs;
  submitLabel?: string;
  onSubmit: (inputs: ProjectInputs) => void | Promise<void>;
  busy?: boolean;
  err?: string | null;
  locked?: boolean;
  showTemplatePicker?: boolean;
}) {
  const [clients, setClients] = useState<Client[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [techs, setTechs] = useState<Technician[]>([]);
  const [templates, setTemplates] = useState<ServiceTemplate[]>([]);
  const [inputs, setInputs] = useState<ProjectInputs>(initial);
  const [breakdown, setBreakdown] = useState<CostBreakdown | null>(null);

  useEffect(() => {
    Promise.all([
      api.listClients(),
      api.listVehicles(),
      api.listTechnicians(),
      api.listTemplates(),
    ]).then(([c, v, t, tpl]) => {
      setClients(c);
      setVehicles(v);
      setTechs(t);
      setTemplates(tpl);
    });
  }, []);

  function applyTemplate(id: number) {
    const tpl = templates.find((t) => t.id === id);
    if (!tpl) return;
    setInputs((s) => ({
      ...s,
      from_template_id: tpl.id,
      service_type: tpl.service_type,
      description: s.description || tpl.description || "",
      people_on_site: tpl.default_people_on_site,
      estimated_hours_on_site: Number(tpl.default_estimated_hours_on_site),
      contingency_pct: Number(tpl.default_contingency_pct),
      margin_pct: Number(tpl.default_margin_pct),
      materials: tpl.materials,
      initial_activities: tpl.activities.map((a, i) => ({
        title: a.title,
        description: a.description ?? null,
        estimated_hours: a.estimated_hours,
        position: i,
      })),
    }));
  }

  useEffect(() => {
    if (!inputs.client_id || !inputs.title) {
      setBreakdown(null);
      return;
    }
    const t = setTimeout(() => {
      api
        .previewProject(inputs)
        .then(setBreakdown)
        .catch(() => setBreakdown(null));
    }, 250);
    return () => clearTimeout(t);
  }, [inputs]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!inputs.client_id || !inputs.title) return;
    onSubmit(inputs);
  }

  function updateMaterial(i: number, field: keyof MaterialLine, value: string | number) {
    setInputs((s) => {
      const m = [...s.materials];
      m[i] = { ...m[i], [field]: value };
      return { ...s, materials: m };
    });
  }

  function addMaterial() {
    setInputs((s) => ({ ...s, materials: [...s.materials, { name: "", qty: 1, unit_cost: 0 }] }));
  }

  function removeMaterial(i: number) {
    setInputs((s) => ({ ...s, materials: s.materials.filter((_, idx) => idx !== i) }));
  }

  function updateAssignment(i: number, field: keyof TechAssignment, value: number) {
    setInputs((s) => {
      const a = [...s.tech_assignments];
      a[i] = { ...a[i], [field]: value };
      return { ...s, tech_assignments: a };
    });
  }

  function addAssignment() {
    const first = techs.find((t) => !inputs.tech_assignments.some((a) => a.technician_id === t.id));
    if (!first) return;
    setInputs((s) => ({
      ...s,
      tech_assignments: [...s.tech_assignments, { technician_id: first.id, hours: 0, days: 0 }],
    }));
  }

  function removeAssignment(i: number) {
    setInputs((s) => ({ ...s, tech_assignments: s.tech_assignments.filter((_, idx) => idx !== i) }));
  }

  function updateInitialActivity(i: number, field: keyof TemplateActivity, value: string | number) {
    setInputs((s) => {
      const acts = [...(s.initial_activities || [])];
      acts[i] = { ...acts[i], [field]: value };
      return { ...s, initial_activities: acts };
    });
  }

  function addInitialActivity() {
    setInputs((s) => ({
      ...s,
      initial_activities: [
        ...(s.initial_activities || []),
        { title: "", estimated_hours: 0, position: (s.initial_activities || []).length, description: null },
      ],
    }));
  }

  function removeInitialActivity(i: number) {
    setInputs((s) => ({
      ...s,
      initial_activities: (s.initial_activities || []).filter((_, idx) => idx !== i),
    }));
  }

  const materialsTotal = useMemo(
    () =>
      inputs.materials.reduce(
        (sum, m) => sum + Number(m.qty || 0) * Number(m.unit_cost || 0),
        0
      ),
    [inputs.materials]
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-6">
      <form onSubmit={handleSubmit} className="space-y-5">
        {err && <div className="card p-3 text-[var(--bad)] text-sm">{err}</div>}
        {locked && (
          <div className="card p-3 text-amber-300 text-sm bg-amber-500/5 border-amber-500/30">
            Project is closed — reopen (change status) to edit fields.
          </div>
        )}

        <fieldset disabled={locked} className="space-y-5">

        {showTemplatePicker && templates.length > 0 && (
          <Section title="Start from a template (optional)">
            <p className="text-xs text-[var(--muted)]">
              Templates pre-fill the service shape (activities, BOM, markups) so you don't start from scratch. You can still edit everything before saving.
            </p>
            <div className="flex flex-wrap gap-2">
              {templates.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => applyTemplate(t.id)}
                  className={`text-sm px-3 py-2 rounded-lg border transition text-left ${
                    inputs.from_template_id === t.id
                      ? "border-[var(--brand)] bg-[var(--brand)]/10"
                      : "border-[var(--border)] hover:border-[var(--brand)]/60"
                  }`}
                >
                  <p className="font-medium">{t.name}</p>
                  <p className="text-[11px] text-[var(--muted)]">
                    {t.activities.length} activities · {t.materials.length} materials · {t.default_estimated_hours_on_site}h on site
                  </p>
                </button>
              ))}
            </div>
          </Section>
        )}

        <Section title="1. Client & scope">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Client">
              <select
                required
                value={inputs.client_id}
                onChange={(e) => setInputs({ ...inputs, client_id: Number(e.target.value) })}
              >
                <option value={0} disabled>Pick a client…</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Service type">
              <select
                value={inputs.service_type}
                onChange={(e) => setInputs({ ...inputs, service_type: e.target.value as ServiceType })}
              >
                {services.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Project title">
            <input
              required
              placeholder="e.g. 20kW off-grid hybrid system — Upington"
              value={inputs.title}
              onChange={(e) => setInputs({ ...inputs, title: e.target.value })}
            />
          </Field>
          <Field label="Site address">
            <input
              placeholder="Street / farm / GPS"
              value={inputs.site_address || ""}
              onChange={(e) => setInputs({ ...inputs, site_address: e.target.value })}
            />
          </Field>
          <Field label="Scope overview (free text)">
            <textarea
              rows={2}
              placeholder="Panels, battery, inverter spec, access notes…"
              value={inputs.description || ""}
              onChange={(e) => setInputs({ ...inputs, description: e.target.value })}
            />
          </Field>
        </Section>

        <Section title="2. Travel & vehicle — where diesel goes">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Field label="One-way distance (km)">
              <input
                type="number"
                min={0}
                step={1}
                value={inputs.one_way_distance_km}
                onChange={(e) => setInputs({ ...inputs, one_way_distance_km: Number(e.target.value) })}
              />
            </Field>
            <Field label="Return trips">
              <input
                type="number"
                min={1}
                value={inputs.return_trips}
                onChange={(e) => setInputs({ ...inputs, return_trips: Number(e.target.value) })}
              />
            </Field>
            <Field label="Vehicle">
              <select
                value={inputs.vehicle_id || 0}
                onChange={(e) => setInputs({ ...inputs, vehicle_id: Number(e.target.value) || null })}
              >
                <option value={0}>None</option>
                {vehicles.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.fuel_consumption_l_per_100km} L/100km)
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Travel hours (one way)">
              <input
                type="number"
                min={0}
                step={0.5}
                value={inputs.estimated_travel_hours}
                onChange={(e) => setInputs({ ...inputs, estimated_travel_hours: Number(e.target.value) })}
              />
            </Field>
          </div>
          <p className="text-xs text-[var(--muted)]">
            Total km driven = one-way × return trips × 2.
          </p>
        </Section>

        <Section title="3. Time on site & overnight">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Field label="Est. hours on site">
              <input
                type="number"
                min={0}
                step={0.5}
                value={inputs.estimated_hours_on_site}
                onChange={(e) => setInputs({ ...inputs, estimated_hours_on_site: Number(e.target.value) })}
              />
            </Field>
            <Field label="People on site">
              <input
                type="number"
                min={1}
                value={inputs.people_on_site}
                onChange={(e) => setInputs({ ...inputs, people_on_site: Number(e.target.value) })}
              />
            </Field>
            <Field label="Overnight nights">
              <input
                type="number"
                min={0}
                value={inputs.overnight_nights}
                onChange={(e) => setInputs({ ...inputs, overnight_nights: Number(e.target.value) })}
              />
            </Field>
          </div>
        </Section>

        {showTemplatePicker && (
          <Section title="4. Initial activities (will be created when you save)" right={
            <button type="button" onClick={addInitialActivity} className="text-xs text-[var(--brand)]">+ Add</button>
          }>
            {(inputs.initial_activities || []).length === 0 && (
              <p className="text-xs text-[var(--muted)]">
                No activities yet. Pick a template above, or add them manually. You can also add more after the project is created.
              </p>
            )}
            <div className="space-y-2">
              {(inputs.initial_activities || []).map((a, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  <input
                    className="col-span-8"
                    placeholder="Activity title (e.g. Mount panels)"
                    value={a.title}
                    onChange={(e) => updateInitialActivity(i, "title", e.target.value)}
                  />
                  <input
                    type="number"
                    min={0}
                    step={0.5}
                    className="col-span-3"
                    placeholder="est. hours"
                    value={Number(a.estimated_hours) || 0}
                    onChange={(e) => updateInitialActivity(i, "estimated_hours", Number(e.target.value))}
                  />
                  <button
                    type="button"
                    onClick={() => removeInitialActivity(i)}
                    className="col-span-1 text-[var(--bad)] text-xs"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </Section>
        )}

        <Section title={`${showTemplatePicker ? "5" : "4"}. Labour — who's on this job (for quoting)`} right={
          <button type="button" onClick={addAssignment} className="text-xs text-[var(--brand)]">+ Add tech</button>
        }>
          {inputs.tech_assignments.length === 0 && (
            <p className="text-xs text-[var(--muted)]">No techs assigned yet.</p>
          )}
          <div className="space-y-2">
            {inputs.tech_assignments.map((a, i) => {
              const tech = techs.find((t) => t.id === a.technician_id);
              return (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-6">
                    <select
                      value={a.technician_id}
                      onChange={(e) => updateAssignment(i, "technician_id", Number(e.target.value))}
                    >
                      {techs.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name} · {t.rate_type === "hourly" ? `R${t.hourly_rate}/h` : `R${t.daily_rate}/day`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-span-3">
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      placeholder="hours"
                      value={Number(a.hours) || 0}
                      onChange={(e) => updateAssignment(i, "hours", Number(e.target.value))}
                      disabled={tech?.rate_type === "daily"}
                    />
                  </div>
                  <div className="col-span-2">
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      placeholder="days"
                      value={Number(a.days) || 0}
                      onChange={(e) => updateAssignment(i, "days", Number(e.target.value))}
                      disabled={tech?.rate_type === "hourly"}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => removeAssignment(i)}
                    className="col-span-1 text-[var(--bad)] text-xs"
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        </Section>

        <Section title={`${showTemplatePicker ? "6" : "5"}. Materials / BOM`} right={
          <span className="text-xs text-[var(--muted)]">
            Subtotal: <span className="text-white font-medium">{formatZAR(materialsTotal)}</span>
          </span>
        }>
          {inputs.materials.length === 0 && (
            <p className="text-xs text-[var(--muted)]">No materials yet.</p>
          )}
          <div className="space-y-2">
            {inputs.materials.map((m, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-center">
                <input
                  className="col-span-6"
                  placeholder="Item"
                  value={m.name}
                  onChange={(e) => updateMaterial(i, "name", e.target.value)}
                />
                <input
                  className="col-span-2"
                  type="number"
                  min={0}
                  placeholder="qty"
                  value={Number(m.qty)}
                  onChange={(e) => updateMaterial(i, "qty", e.target.value)}
                />
                <input
                  className="col-span-3"
                  type="number"
                  min={0}
                  step={0.01}
                  placeholder="unit cost (R)"
                  value={Number(m.unit_cost)}
                  onChange={(e) => updateMaterial(i, "unit_cost", e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => removeMaterial(i)}
                  className="col-span-1 text-[var(--bad)] text-xs"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <button type="button" onClick={addMaterial} className="text-xs text-[var(--brand)] mt-2">
            + Add material
          </button>
        </Section>

        <Section title={`${showTemplatePicker ? "7" : "6"}. Markups`}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Contingency %">
              <input
                type="number"
                min={0}
                step={0.5}
                placeholder="uses default if blank"
                value={inputs.contingency_pct ?? ""}
                onChange={(e) => setInputs({ ...inputs, contingency_pct: e.target.value === "" ? null : Number(e.target.value) })}
              />
            </Field>
            <Field label="Target margin %">
              <input
                type="number"
                min={0}
                step={0.5}
                placeholder="uses default if blank"
                value={inputs.margin_pct ?? ""}
                onChange={(e) => setInputs({ ...inputs, margin_pct: e.target.value === "" ? null : Number(e.target.value) })}
              />
            </Field>
          </div>
        </Section>

        </fieldset>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={busy || locked || !inputs.client_id || !inputs.title}
            className="bg-[var(--brand)] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white disabled:opacity-50"
          >
            {busy ? "Saving…" : submitLabel}
          </button>
        </div>
      </form>

      <aside className="lg:sticky lg:top-6 lg:self-start">
        <LiveQuote breakdown={breakdown} />
      </aside>
    </div>
  );
}

function Section({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm">{title}</h3>
        {right}
      </div>
      {children}
    </section>
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

function LiveQuote({ breakdown }: { breakdown: CostBreakdown | null }) {
  if (!breakdown) {
    return (
      <div className="card p-5">
        <p className="text-[var(--muted)] text-sm">
          Fill in client + title to preview the quote.
        </p>
      </div>
    );
  }
  return (
    <div className="card p-5 space-y-4">
      <div>
        <h3 className="font-semibold">Live quote breakdown</h3>
        <p className="text-xs text-[var(--muted)]">Every number, no hidden totals.</p>
      </div>

      <div className="space-y-2">
        {breakdown.lines.length === 0 && (
          <p className="text-xs text-[var(--muted)]">No cost lines yet — add travel, labour, or materials.</p>
        )}
        {breakdown.lines.map((l) => (
          <div key={l.key} className="flex justify-between items-start text-sm">
            <div className="min-w-0 pr-3">
              <p className="text-white">{l.label}</p>
              <p className="text-[11px] text-[var(--muted)]">{l.detail}</p>
            </div>
            <p className="font-semibold whitespace-nowrap">{formatZARPrecise(l.amount)}</p>
          </div>
        ))}
      </div>

      <div className="border-t border-[var(--border)] pt-3 space-y-1.5 text-sm">
        <div className="flex justify-between"><span>Subtotal (cost)</span><span className="font-semibold">{formatZARPrecise(breakdown.subtotal)}</span></div>
        <div className="flex justify-between text-xs text-[var(--muted)]"><span>+ Contingency</span><span>{formatZARPrecise(breakdown.contingency)}</span></div>
        <div className="flex justify-between text-xs text-[var(--muted)]"><span>+ Margin</span><span>{formatZARPrecise(breakdown.margin)}</span></div>
        <div className="flex justify-between pt-1"><span>Total (ex VAT)</span><span className="font-bold">{formatZARPrecise(breakdown.total_ex_vat)}</span></div>
        <div className="flex justify-between text-xs text-[var(--muted)]"><span>+ VAT (15%)</span><span>{formatZARPrecise(breakdown.vat)}</span></div>
        <div className="pt-2 border-t border-[var(--border)] flex justify-between items-center">
          <span className="text-xs uppercase tracking-wide text-[var(--muted)]">Quote to client</span>
          <span className="text-2xl font-bold text-[var(--brand)]">
            {formatZARPrecise(breakdown.total_inc_vat)}
          </span>
        </div>
      </div>
    </div>
  );
}
