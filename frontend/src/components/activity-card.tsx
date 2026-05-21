"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  type Activity,
  type ActivityStatus,
  type Technician,
} from "@/lib/api";

const STATUS_META: Record<ActivityStatus, { label: string; bg: string; fg: string }> = {
  pending: { label: "Pending", bg: "bg-zinc-500/15", fg: "text-zinc-300" },
  scheduled: { label: "Scheduled", bg: "bg-sky-500/15", fg: "text-sky-300" },
  in_progress: { label: "In progress", bg: "bg-amber-500/15", fg: "text-amber-300" },
  blocked: { label: "Blocked", bg: "bg-rose-500/15", fg: "text-rose-300" },
  done: { label: "Done", bg: "bg-emerald-500/15", fg: "text-emerald-300" },
  skipped: { label: "Skipped", bg: "bg-zinc-500/10", fg: "text-zinc-500" },
};

const STATUS_OPTIONS: ActivityStatus[] = [
  "pending",
  "scheduled",
  "in_progress",
  "blocked",
  "done",
  "skipped",
];

export function StatusPill({ status }: { status: ActivityStatus }) {
  const m = STATUS_META[status];
  return <span className={`chip ${m.bg} ${m.fg}`}>{m.label}</span>;
}

export default function ActivityCard({
  activity,
  techs,
  locked,
  compact,
}: {
  activity: Activity;
  techs: Technician[];
  locked?: boolean;
  compact?: boolean;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const assigned = techs.filter((t) => activity.assigned_tech_ids.includes(t.id));
  const estH = parseFloat(activity.estimated_hours) || 0;
  const actualH = parseFloat(activity.actual_hours) || 0;
  const overEst = estH > 0 && actualH > estH;
  const openEntries = activity.time_entries.filter((te) => te.ended_at === null);

  async function refresh() {
    router.refresh();
  }

  async function setStatus(s: ActivityStatus) {
    setBusy(true);
    await api.updateActivity(activity.id, { status: s });
    setBusy(false);
    await refresh();
  }

  async function start(technicianId: number) {
    setBusy(true);
    try {
      await api.startActivity(activity.id, technicianId);
      await refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function stop(technicianId: number) {
    setBusy(true);
    try {
      await api.stopActivity(activity.id, technicianId);
      await refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function complete() {
    setBusy(true);
    await api.completeActivity(activity.id);
    setBusy(false);
    await refresh();
  }

  async function remove() {
    if (!confirm(`Delete activity "${activity.title}"?`)) return;
    setBusy(true);
    await api.deleteActivity(activity.id);
    setBusy(false);
    await refresh();
  }

  return (
    <div
      className={`border border-[var(--border)] rounded-lg overflow-hidden ${
        activity.status === "blocked" ? "border-rose-500/40" : ""
      } ${activity.status === "in_progress" ? "border-amber-500/40" : ""}`}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left p-3 hover:bg-white/[0.03] transition flex items-start gap-3"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusPill status={activity.status} />
            <p className={`text-sm ${activity.status === "done" ? "line-through text-[var(--muted)]" : ""}`}>
              {activity.title}
            </p>
            {openEntries.length > 0 && (
              <span className="chip bg-amber-500/20 text-amber-200 animate-pulse">
                ● clock running
              </span>
            )}
          </div>
          {!compact && (
            <div className="flex flex-wrap items-center gap-3 mt-1 text-[11px] text-[var(--muted)]">
              {assigned.length > 0 && (
                <span>👷 {assigned.map((t) => t.name.split(" ")[0]).join(", ")}</span>
              )}
              {activity.scheduled_date && <span>📅 {activity.scheduled_date}</span>}
              <span className={overEst ? "text-[var(--bad)] font-medium" : ""}>
                ⏱ {actualH.toFixed(1)}h / {estH}h est
              </span>
              {activity.due_date && <span>⏲ due {activity.due_date}</span>}
            </div>
          )}
          {activity.status === "blocked" && activity.blocker_reason && (
            <p className="text-xs text-rose-300 mt-1">🚫 {activity.blocker_reason}</p>
          )}
        </div>
        <span className="text-[var(--muted)] text-xs">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="p-3 pt-0 space-y-3 border-t border-[var(--border)] bg-black/20">
          {activity.description && (
            <p className="text-xs text-[var(--muted)] whitespace-pre-wrap pt-3">
              {activity.description}
            </p>
          )}

          {/* Tech start/stop controls */}
          {!locked && assigned.length > 0 && activity.status !== "done" && (
            <div className="space-y-2 pt-2">
              <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Clock in / out</p>
              <div className="flex flex-wrap gap-2">
                {assigned.map((t) => {
                  const running = openEntries.some((te) => te.technician_id === t.id);
                  return (
                    <div key={t.id} className="flex items-center gap-1.5 text-xs bg-white/5 border border-[var(--border)] rounded-lg px-2 py-1">
                      <span>{t.name.split(" ")[0]}</span>
                      {running ? (
                        <button
                          onClick={() => stop(t.id)}
                          disabled={busy}
                          className="bg-amber-500/30 text-amber-200 px-2 py-0.5 rounded font-medium hover:bg-amber-500/50 disabled:opacity-50"
                        >
                          ■ stop
                        </button>
                      ) : (
                        <button
                          onClick={() => start(t.id)}
                          disabled={busy}
                          className="bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-medium hover:bg-emerald-500/40 disabled:opacity-50"
                        >
                          ▶ start
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Time log */}
          {activity.time_entries.length > 0 && (
            <div className="space-y-1 pt-1">
              <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Time log</p>
              {activity.time_entries.map((te) => (
                <div key={te.id} className="text-xs flex justify-between">
                  <span>
                    {te.technician_name} · {new Date(te.started_at).toLocaleString("en-ZA", { dateStyle: "short", timeStyle: "short" })}
                    {te.ended_at && (
                      <>
                        {" → "}
                        {new Date(te.ended_at).toLocaleString("en-ZA", { timeStyle: "short" })}
                      </>
                    )}
                  </span>
                  <span className={te.ended_at ? "" : "text-amber-300"}>
                    {te.ended_at ? `${te.hours}h` : "running…"}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Status + completion controls */}
          {!locked && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[var(--border)]">
              <select
                value={activity.status}
                onChange={(e) => setStatus(e.target.value as ActivityStatus)}
                disabled={busy}
                className="text-xs py-1 px-2"
                style={{ width: "auto" }}
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    Set: {STATUS_META[s].label}
                  </option>
                ))}
              </select>
              {activity.status !== "done" && (
                <button
                  onClick={complete}
                  disabled={busy}
                  className="text-xs bg-emerald-500/20 text-emerald-300 px-3 py-1 rounded-lg hover:bg-emerald-500/40 disabled:opacity-50"
                >
                  ✓ Mark done
                </button>
              )}
              <button
                onClick={remove}
                disabled={busy}
                className="ml-auto text-xs text-rose-400 hover:underline disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
