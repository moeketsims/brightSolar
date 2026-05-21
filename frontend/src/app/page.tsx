"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, formatZAR, type AgedDebtors, type DashboardOut } from "@/lib/api";
import { MarginGauge, StatusChip } from "@/components/gauge";

export default function Dashboard() {
  const [d, setD] = useState<DashboardOut | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .dashboard()
      .then(setD)
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) {
    return (
      <div className="card p-6 text-red-400">
        Could not reach API at {api.apiBase}. Is the backend running?
      </div>
    );
  }
  if (!d) {
    return <div className="text-[var(--muted)]">Loading…</div>;
  }

  const stats = [
    { label: "Active projects", value: d.active_projects, sub: "quoting · accepted · on site" },
    { label: "Quoted pipeline", value: formatZAR(d.quoted_pipeline), sub: "inc VAT, active" },
    { label: "Expenses this month", value: formatZAR(d.expenses_this_month), sub: "all logged receipts" },
    {
      label: "Over budget",
      value: d.projects_over_budget,
      sub: "actuals exceed quoted",
      warn: d.projects_over_budget > 0,
    },
    {
      label: "In progress now",
      value: d.activities_in_progress,
      sub: "activities running",
      good: d.activities_in_progress > 0,
    },
    {
      label: "Blocked",
      value: d.activities_blocked,
      sub: "activities waiting",
      warn: d.activities_blocked > 0,
    },
    {
      label: "Overdue",
      value: d.activities_overdue,
      sub: "past due date",
      warn: d.activities_overdue > 0,
    },
  ];

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight">Operations</h2>
          <p className="text-[var(--muted)] text-sm">Where the money is going, right now.</p>
        </div>
        <Link
          href="/projects/new"
          className="bg-[var(--brand)] text-black font-medium px-4 py-2.5 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white transition"
        >
          + Quote a new project
        </Link>
      </header>

      <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7 gap-3">
        {stats.map((s: any) => (
          <div key={s.label} className="card p-4 min-w-0">
            <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{s.label}</p>
            <p
              className={`text-2xl font-bold mt-1 break-words ${
                s.warn ? "text-[var(--bad)]" : s.good ? "text-[var(--good)]" : ""
              }`}
            >
              {s.value}
            </p>
            <p className="text-xs text-[var(--muted)] mt-1">{s.sub}</p>
          </div>
        ))}
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Aged debtors</h3>
          <Link href="/invoices" className="text-[var(--brand)] text-sm hover:underline">
            All invoices →
          </Link>
        </div>
        <DebtorsCard debtors={d.debtors} />
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Project health</h3>
          <Link href="/projects" className="text-[var(--brand)] text-sm hover:underline">
            All projects →
          </Link>
        </div>

        {d.cards.length === 0 ? (
          <div className="card p-10 text-center">
            <p className="text-[var(--muted)]">No projects yet.</p>
            <Link
              href="/projects/new"
              className="inline-block mt-4 bg-[var(--brand)] text-black font-medium px-4 py-2 rounded-lg"
            >
              Quote your first project
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {d.cards.map((c) => {
              const quoted = parseFloat(c.quoted_ex_vat);
              const actual = parseFloat(c.actual_total);
              const remaining = quoted - actual;
              return (
                <Link
                  key={c.id}
                  href={`/projects/${c.id}`}
                  className="card p-5 hover:border-[var(--brand)]/60 transition block"
                >
                  <div className="flex justify-between items-start gap-3 mb-3">
                    <div className="min-w-0">
                      <p className="text-xs text-[var(--muted)] truncate">{c.client_name}</p>
                      <p className="font-semibold truncate">{c.title}</p>
                    </div>
                    <StatusChip status={c.status} />
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-xs text-[var(--muted)] mb-1">
                        <span>
                          Spent <span className="text-white">{formatZAR(c.actual_total)}</span>
                        </span>
                        <span>
                          of <span className="text-white">{formatZAR(c.quoted_ex_vat)}</span>
                        </span>
                      </div>
                      <MarginGauge burn={c.burn_ratio} colour={c.status_colour} />
                    </div>
                    <div className="flex justify-between pt-2 border-t border-[var(--border)]">
                      <span className="text-xs text-[var(--muted)]">
                        {c.burn_ratio >= 1 ? "OVER by" : "Remaining"}
                      </span>
                      <span
                        className={`text-sm font-semibold ${
                          remaining < 0 ? "text-[var(--bad)]" : "text-[var(--good)]"
                        }`}
                      >
                        {formatZAR(Math.abs(remaining))}
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

function DebtorsCard({ debtors }: { debtors: AgedDebtors }) {
  const buckets = [
    { label: "0–30 days", value: debtors.bucket_0_30, colour: "bg-sky-500/15 text-sky-300" },
    { label: "31–60 days", value: debtors.bucket_31_60, colour: "bg-amber-500/15 text-amber-300" },
    { label: "61–90 days", value: debtors.bucket_61_90, colour: "bg-orange-500/15 text-orange-300" },
    { label: "90+ days", value: debtors.bucket_90_plus, colour: "bg-rose-500/15 text-rose-300" },
  ];
  const total = parseFloat(debtors.total_outstanding || "0");
  return (
    <div className="card p-4">
      <div className="flex flex-wrap gap-4 items-baseline mb-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Total outstanding</p>
          <p className={`text-2xl font-bold ${total > 0 ? "text-[var(--bad)]" : "text-[var(--muted)]"}`}>
            {formatZAR(total)}
          </p>
        </div>
        {debtors.overdue_count > 0 && (
          <span className="chip bg-rose-500/15 text-rose-300">
            ⚠ {debtors.overdue_count} overdue invoice{debtors.overdue_count > 1 ? "s" : ""}
          </span>
        )}
        {total === 0 && (
          <span className="chip bg-emerald-500/15 text-emerald-300">✓ no outstanding invoices</span>
        )}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {buckets.map((b) => (
          <div key={b.label} className="border border-[var(--border)] rounded-lg p-3">
            <p className={`chip ${b.colour} mb-2`}>{b.label}</p>
            <p className="text-lg font-semibold">{formatZAR(b.value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
