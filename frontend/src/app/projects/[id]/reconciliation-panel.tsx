"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  formatZAR,
  formatZARPrecise,
  type LearningSuggestion,
  type Reconciliation,
} from "@/lib/api";

export default function ReconciliationPanel({ projectId }: { projectId: number }) {
  const router = useRouter();
  const [data, setData] = useState<Reconciliation | null>(null);
  const [applying, setApplying] = useState<string | null>(null);
  const [applied, setApplied] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.reconciliation(projectId).then(setData).catch(() => setData(null));
  }, [projectId]);

  async function apply(s: LearningSuggestion) {
    if (!confirm(`Apply: ${s.summary}`)) return;
    setApplying(s.id);
    await api.applySuggestion(projectId, {
      suggestion_id: s.id,
      field: s.field,
      target: s.target,
      value: s.suggested_value,
    });
    setApplied((prev) => new Set(prev).add(s.id));
    setApplying(null);
    router.refresh();
  }

  if (!data) return null;

  const marginDelta = parseFloat(data.margin_delta);
  const hoursEst = parseFloat(data.total_hours_estimated);
  const hoursAct = parseFloat(data.total_hours_actual);
  const hoursDelta = hoursAct - hoursEst;

  return (
    <section className="card p-5 space-y-5 border-[var(--brand)]/40 bg-gradient-to-br from-amber-500/[0.04] to-transparent">
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <div>
          <h3 className="font-semibold text-lg">Project reconciliation</h3>
          <p className="text-[var(--muted)] text-sm">
            Now that the project is closed, here's how reality compared to your quote. Apply
            the suggestions so the next quote is sharper.
          </p>
        </div>
        <div className="flex gap-4 text-right">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
              Margin realised
            </p>
            <p className={`text-xl font-bold ${marginDelta >= 0 ? "text-[var(--good)]" : "text-[var(--bad)]"}`}>
              {formatZAR(data.margin_realised)}
            </p>
            <p className="text-xs text-[var(--muted)]">
              vs quoted {formatZAR(data.margin_quoted)} ({marginDelta >= 0 ? "+" : ""}
              {formatZAR(marginDelta)})
            </p>
          </div>
        </div>
      </div>

      {/* Suggestions */}
      {data.suggestions.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
            Learning suggestions
          </p>
          {data.suggestions.map((s) => {
            const done = applied.has(s.id);
            return (
              <div
                key={s.id}
                className={`border rounded-lg p-3 flex items-center gap-3 ${
                  done
                    ? "border-[var(--good)]/40 bg-emerald-500/5"
                    : "border-[var(--brand)]/40 bg-amber-500/5"
                }`}
              >
                <span className="text-xl">{done ? "✓" : "💡"}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{s.summary}</p>
                  <p className="text-[11px] text-[var(--muted)]">
                    {s.field} · current {s.current_value} → suggested {s.suggested_value}
                  </p>
                </div>
                <button
                  disabled={done || applying === s.id}
                  onClick={() => apply(s)}
                  className={`text-xs px-3 py-1.5 rounded-lg font-medium transition ${
                    done
                      ? "bg-emerald-500/20 text-emerald-300 cursor-default"
                      : "bg-[var(--brand)] text-black hover:bg-[var(--brand-dark)] hover:text-white"
                  }`}
                >
                  {done ? "Applied" : applying === s.id ? "…" : "Apply"}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Per-line cost reconciliation */}
      <div className="space-y-2">
        <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Cost by category</p>
        <div className="border border-[var(--border)] rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-[var(--muted)]">
              <tr>
                <th className="p-2 text-left font-normal text-[11px] uppercase">Line</th>
                <th className="p-2 text-right font-normal text-[11px] uppercase">Quoted</th>
                <th className="p-2 text-right font-normal text-[11px] uppercase">Actual</th>
                <th className="p-2 text-right font-normal text-[11px] uppercase">Δ</th>
                <th className="p-2 text-right font-normal text-[11px] uppercase">%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {data.lines.map((l) => {
                const delta = parseFloat(l.delta);
                const pct = l.pct_of_quoted * 100;
                const over = delta > 0;
                const significant = Math.abs(pct - 100) > 8;
                return (
                  <tr key={l.key}>
                    <td className="p-2">{l.label}</td>
                    <td className="p-2 text-right">{formatZAR(l.quoted)}</td>
                    <td className="p-2 text-right">{formatZAR(l.actual)}</td>
                    <td
                      className={`p-2 text-right ${
                        significant ? (over ? "text-[var(--bad)]" : "text-[var(--good)]") : ""
                      }`}
                    >
                      {delta >= 0 ? "+" : ""}
                      {formatZAR(delta)}
                    </td>
                    <td
                      className={`p-2 text-right text-xs ${
                        significant ? (over ? "text-[var(--bad)]" : "text-[var(--good)]") : "text-[var(--muted)]"
                      }`}
                    >
                      {pct.toFixed(0)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Activity hour accuracy */}
      {data.activity_accuracy.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
            Time accuracy per activity  —  {hoursAct.toFixed(1)}h actual of {hoursEst.toFixed(1)}h estimated
            <span className={`ml-2 ${hoursDelta > 0 ? "text-[var(--bad)]" : "text-[var(--good)]"}`}>
              ({hoursDelta >= 0 ? "+" : ""}{hoursDelta.toFixed(1)}h)
            </span>
          </p>
          <div className="border border-[var(--border)] rounded-lg divide-y divide-[var(--border)]">
            {data.activity_accuracy.map((a) => {
              const dh = parseFloat(a.delta_hours);
              const significant = Math.abs(dh) >= 2;
              return (
                <div key={a.activity_id} className="p-2 flex justify-between items-center text-sm">
                  <span className="flex-1 min-w-0 truncate">{a.title}</span>
                  <span className="text-[var(--muted)] text-xs mr-3">
                    {a.estimated_hours}h → {a.actual_hours}h
                  </span>
                  <span
                    className={`text-xs font-medium w-16 text-right ${
                      significant ? (dh > 0 ? "text-[var(--bad)]" : "text-[var(--good)]") : "text-[var(--muted)]"
                    }`}
                  >
                    {dh >= 0 ? "+" : ""}
                    {dh.toFixed(1)}h
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
