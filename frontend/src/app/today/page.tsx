"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  type Technician,
  type TodayBoard,
} from "@/lib/api";
import ActivityCard from "@/components/activity-card";

export default function TodayPage() {
  const [date, setDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [board, setBoard] = useState<TodayBoard | null>(null);
  const [techs, setTechs] = useState<Technician[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      const [b, t] = await Promise.all([api.today(date), api.listTechnicians()]);
      setBoard(b);
      setTechs(t);
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000); // auto-refresh every 30s for running clocks
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  if (!board) {
    return <div className="text-[var(--muted)]">Loading…</div>;
  }

  const isToday = date === new Date().toISOString().slice(0, 10);
  const totalScheduledHours = board.columns.reduce(
    (sum, c) => sum + parseFloat(c.scheduled_hours || "0"),
    0
  );

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-semibold">Today</h2>
          <p className="text-[var(--muted)] text-sm">
            {isToday ? "What's happening right now across all projects." : `Schedule for ${date}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-auto text-sm"
          />
          <button
            onClick={() => setDate(new Date().toISOString().slice(0, 10))}
            className="text-xs text-[var(--brand)] px-3 py-1.5 border border-[var(--border)] rounded-lg hover:border-[var(--brand)]/60"
          >
            Today
          </button>
        </div>
      </header>

      {err && <div className="card p-3 text-[var(--bad)] text-sm">{err}</div>}

      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPI label="Techs working" value={board.columns.filter((c) => c.activities.length > 0 && c.technician_id).length} />
        <KPI label="Activities scheduled" value={board.total_activities} />
        <KPI
          label="Hours booked"
          value={`${totalScheduledHours.toFixed(1)}h`}
        />
        <KPI
          label="Overloaded techs"
          value={board.columns.filter((c) => c.overload).length}
          warn={board.columns.some((c) => c.overload)}
        />
      </section>

      {board.columns.length === 0 && (
        <div className="card p-10 text-center text-[var(--muted)]">
          No technicians set up. Add some in Settings.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {board.columns.map((col) => {
          const hours = parseFloat(col.scheduled_hours || "0");
          const pctOfDay = Math.min(hours / 9, 1.3) * 100;
          const unassigned = col.technician_id === null;
          return (
            <div
              key={col.technician_id ?? "unassigned"}
              className={`card p-4 space-y-3 ${
                col.overload ? "border-rose-500/40" : unassigned ? "border-dashed" : ""
              }`}
            >
              <div className="flex justify-between items-baseline">
                <div>
                  <p className="font-semibold">
                    {col.technician_name}
                    {col.overload && (
                      <span className="text-[var(--bad)] text-xs ml-2">⚠ overloaded</span>
                    )}
                  </p>
                  {!unassigned && (
                    <p className="text-xs text-[var(--muted)]">
                      {hours.toFixed(1)}h booked · 9h standard day
                    </p>
                  )}
                </div>
                <span className="chip bg-white/5 text-white/70">
                  {col.activities.length}
                </span>
              </div>

              {!unassigned && (
                <div className="gauge-track">
                  <div
                    className="gauge-fill"
                    style={{
                      width: `${pctOfDay}%`,
                      background: col.overload ? "var(--bad)" : "var(--brand)",
                    }}
                  />
                </div>
              )}

              <div className="space-y-2">
                {col.activities.length === 0 && (
                  <p className="text-xs text-[var(--muted)] pt-2">Nothing booked.</p>
                )}
                {col.activities.map((ta) => (
                  <div key={`${col.technician_id}-${ta.activity.id}`} className="space-y-1">
                    <Link
                      href={`/projects/${ta.project_id}`}
                      className="text-[11px] text-[var(--brand)] hover:underline block"
                    >
                      {ta.client_name} · {ta.project_title}
                    </Link>
                    <ActivityCard
                      activity={ta.activity}
                      techs={techs}
                      compact
                    />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function KPI({ label, value, warn }: { label: string; value: string | number; warn?: boolean }) {
  return (
    <div className="card p-4">
      <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${warn ? "text-[var(--bad)]" : ""}`}>{value}</p>
    </div>
  );
}
