"use client";

import { useEffect, useState } from "react";
import { api, type Trip, type Vehicle, type ProjectSummary, type Technician } from "@/lib/api";

export default function TripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [techs, setTechs] = useState<Technician[]>([]);
  const [vehicleFilter, setVehicleFilter] = useState<number | "all">("all");
  const [adding, setAdding] = useState(false);

  async function reload() {
    const params: { vehicle_id?: number } = {};
    if (vehicleFilter !== "all") params.vehicle_id = vehicleFilter;
    setTrips(await api.listTrips(params));
  }

  useEffect(() => {
    Promise.all([api.listVehicles(), api.listProjects(), api.listTechnicians()]).then(([v, p, t]) => {
      setVehicles(v);
      setProjects(p);
      setTechs(t);
    });
  }, []);
  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleFilter]);

  async function handleAdd(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const body: any = {
      vehicle_id: Number(fd.get("vehicle_id")),
      trip_date: String(fd.get("trip_date")),
      from_location: String(fd.get("from_location")),
      to_location: String(fd.get("to_location")),
      purpose: String(fd.get("purpose")),
      odo_start: fd.get("odo_start") ? Number(fd.get("odo_start")) : null,
      odo_end: fd.get("odo_end") ? Number(fd.get("odo_end")) : null,
      business_km: fd.get("business_km") ? Number(fd.get("business_km")) : null,
      technician_id: fd.get("technician_id") ? Number(fd.get("technician_id")) : null,
      project_id: fd.get("project_id") ? Number(fd.get("project_id")) : null,
      notes: String(fd.get("notes") || ""),
    };
    await api.createTrip(body);
    (e.currentTarget as HTMLFormElement).reset();
    setAdding(false);
    await reload();
  }

  async function remove(id: number) {
    if (!confirm("Delete this trip?")) return;
    await api.deleteTrip(id);
    await reload();
  }

  const totalKm = trips.reduce((sum, t) => sum + parseFloat(t.business_km || "0"), 0);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-semibold">Vehicle trip logbook</h2>
          <p className="text-[var(--muted)] text-sm">
            SARS-compliant log of every business trip. Export CSV at tax time.
          </p>
        </div>
        <div className="flex gap-2">
          <select
            value={vehicleFilter}
            onChange={(e) => setVehicleFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="w-auto text-sm"
          >
            <option value="all">All vehicles</option>
            {vehicles.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} {v.registration ? `(${v.registration})` : ""}
              </option>
            ))}
          </select>
          <a
            href={api.tripsExportCsvUrl(
              vehicleFilter === "all" ? {} : { vehicle_id: vehicleFilter }
            )}
            className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15"
          >
            📄 Export CSV
          </a>
          <button
            onClick={() => setAdding(!adding)}
            className="bg-[var(--brand)] text-black font-medium px-4 py-1.5 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white text-sm"
          >
            {adding ? "Cancel" : "+ Log trip"}
          </button>
        </div>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <KPI label="Trips" value={trips.length} />
        <KPI label="Business km" value={`${totalKm.toLocaleString("en-ZA", { maximumFractionDigits: 0 })} km`} />
        <KPI
          label="Period"
          value={
            trips.length > 0
              ? `${trips[trips.length - 1].trip_date} → ${trips[0].trip_date}`
              : "—"
          }
        />
      </section>

      {adding && (
        <form onSubmit={handleAdd} className="card p-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <label className="text-xs">
              Date
              <input type="date" name="trip_date" required defaultValue={new Date().toISOString().slice(0, 10)} />
            </label>
            <label className="text-xs">
              Vehicle
              <select name="vehicle_id" required>
                {vehicles.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs">
              Technician (optional)
              <select name="technician_id">
                <option value="">—</option>
                {techs.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs">
              From
              <input name="from_location" required placeholder="JHB office" />
            </label>
            <label className="text-xs">
              To
              <input name="to_location" required placeholder="Upington" />
            </label>
            <label className="text-xs">
              Purpose
              <input name="purpose" required placeholder="Site survey / install / callout" />
            </label>
            <label className="text-xs">
              Odometer start
              <input name="odo_start" type="number" min="0" />
            </label>
            <label className="text-xs">
              Odometer end
              <input name="odo_end" type="number" min="0" />
            </label>
            <label className="text-xs">
              Business km (auto-computed if odo set)
              <input name="business_km" type="number" step="0.1" min="0" />
            </label>
            <label className="text-xs md:col-span-2">
              Link to project (optional)
              <select name="project_id">
                <option value="">—</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.client_name} — {p.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs md:col-span-3">
              Notes
              <input name="notes" placeholder="Optional" />
            </label>
          </div>
          <button className="bg-[var(--brand)] text-black text-sm font-medium px-4 py-2 rounded-lg">
            Save trip
          </button>
        </form>
      )}

      <div className="card divide-y divide-[var(--border)]">
        {trips.length === 0 && (
          <div className="p-6 text-center text-[var(--muted)] text-sm">No trips logged.</div>
        )}
        {trips.map((t) => (
          <div key={t.id} className="p-4 flex justify-between items-start gap-3 flex-wrap">
            <div className="flex-1 min-w-0">
              <p className="text-xs text-[var(--muted)]">{t.trip_date}</p>
              <p className="text-sm">
                <span className="font-medium">{t.from_location}</span> → <span className="font-medium">{t.to_location}</span>
              </p>
              <p className="text-xs text-[var(--muted)] mt-0.5">
                {t.purpose}
                {t.vehicle_name && ` · ${t.vehicle_name}`}
                {t.project_title && ` · linked: ${t.project_title}`}
              </p>
              {(t.odo_start || t.odo_end) && (
                <p className="text-[11px] text-[var(--muted)]">
                  Odo {t.odo_start ?? "?"} → {t.odo_end ?? "?"}
                </p>
              )}
            </div>
            <div className="text-right">
              <p className="font-bold">{parseFloat(t.business_km).toFixed(0)} km</p>
              <button
                onClick={() => remove(t.id)}
                className="text-[var(--bad)] text-xs hover:underline"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function KPI({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card p-4">
      <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}
