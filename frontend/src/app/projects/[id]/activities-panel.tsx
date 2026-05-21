"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  type Activity,
  type Technician,
} from "@/lib/api";
import ActivityCard from "@/components/activity-card";

export default function ActivitiesPanel({
  projectId,
  initial,
  locked,
}: {
  projectId: number;
  initial: Activity[];
  locked: boolean;
}) {
  const router = useRouter();
  const [techs, setTechs] = useState<Technician[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState("");
  const [estHours, setEstHours] = useState("");
  const [scheduledDate, setScheduledDate] = useState("");
  const [assigned, setAssigned] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listTechnicians().then(setTechs);
  }, []);

  const activities = [...initial].sort((a, b) => a.position - b.position);
  const done = activities.filter((a) => a.status === "done").length;
  const blocked = activities.filter((a) => a.status === "blocked").length;
  const inProg = activities.filter((a) => a.status === "in_progress").length;
  const pct = activities.length > 0 ? Math.round((done / activities.length) * 100) : 0;

  const totalEst = activities.reduce((sum, a) => sum + (parseFloat(a.estimated_hours) || 0), 0);
  const totalActual = activities.reduce((sum, a) => sum + (parseFloat(a.actual_hours) || 0), 0);

  async function addActivity(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    await api.createActivity(projectId, {
      title: title.trim(),
      estimated_hours: estHours ? Number(estHours) : 0,
      scheduled_date: scheduledDate || null,
      assigned_tech_ids: assigned,
      status: scheduledDate ? "scheduled" : "pending",
    });
    setTitle("");
    setEstHours("");
    setScheduledDate("");
    setAssigned([]);
    setShowAdd(false);
    setBusy(false);
    router.refresh();
  }

  function toggleAssign(id: number) {
    setAssigned((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  return (
    <div className="card p-5 space-y-3">
      <div className="flex justify-between items-baseline">
        <h3 className="font-semibold">Activities</h3>
        <div className="text-xs text-[var(--muted)] flex gap-3">
          <span>{done}/{activities.length} done ({pct}%)</span>
          {inProg > 0 && <span className="text-amber-300">· {inProg} in progress</span>}
          {blocked > 0 && <span className="text-rose-300">· {blocked} blocked</span>}
        </div>
      </div>

      {activities.length > 0 && (
        <div className="space-y-2">
          <div className="gauge-track">
            <div
              className="gauge-fill"
              style={{
                width: `${pct}%`,
                background: "var(--brand)",
                boxShadow: "0 0 10px rgba(245, 158, 11, 0.3)",
              }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-[var(--muted)]">
            <span>
              Hours: <span className="text-white">{totalActual.toFixed(1)}h</span> actual / {totalEst.toFixed(1)}h estimated
            </span>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {activities.length === 0 && !showAdd && (
          <p className="text-xs text-[var(--muted)]">
            No activities yet. Break the project into work items so the team can clock into each one.
          </p>
        )}
        {activities.map((a) => (
          <ActivityCard key={a.id} activity={a} techs={techs} locked={locked} />
        ))}
      </div>

      {!locked && (
        <>
          {!showAdd ? (
            <button
              onClick={() => setShowAdd(true)}
              className="w-full text-sm py-2 border border-dashed border-[var(--border)] rounded-lg hover:border-[var(--brand)]/60 hover:text-[var(--brand)] transition"
            >
              + Add activity
            </button>
          ) : (
            <form onSubmit={addActivity} className="border border-[var(--border)] rounded-lg p-3 space-y-2 bg-black/20">
              <input
                placeholder="What needs to happen? e.g. 'Mount panels on north roof'"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                autoFocus
                className="text-sm"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  placeholder="Est. hours"
                  value={estHours}
                  onChange={(e) => setEstHours(e.target.value)}
                  className="text-sm"
                />
                <input
                  type="date"
                  value={scheduledDate}
                  onChange={(e) => setScheduledDate(e.target.value)}
                  className="text-sm"
                />
              </div>
              {techs.length > 0 && (
                <div>
                  <p className="text-[11px] uppercase tracking-wide text-[var(--muted)] mb-1">
                    Assign to
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {techs.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => toggleAssign(t.id)}
                        className={`chip transition ${
                          assigned.includes(t.id)
                            ? "bg-[var(--brand)] text-black"
                            : "bg-white/5 text-white/70 hover:bg-white/10"
                        }`}
                      >
                        {t.name.split(" ")[0]}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex gap-2">
                <button
                  disabled={busy || !title.trim()}
                  className="bg-[var(--brand)] text-black text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white disabled:opacity-50"
                >
                  {busy ? "…" : "Add"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAdd(false);
                    setTitle("");
                  }}
                  className="text-xs text-[var(--muted)] hover:underline"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </>
      )}
    </div>
  );
}
