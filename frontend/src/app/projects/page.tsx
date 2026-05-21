"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, formatZAR, type ProjectSummary } from "@/lib/api";
import { StatusChip } from "@/components/gauge";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects);
  }, []);

  if (!projects) return <div className="text-[var(--muted)]">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-semibold">Projects</h2>
          <p className="text-[var(--muted)] text-sm">
            Every project shows quoted cost vs actual spend so far.
          </p>
        </div>
        <Link
          href="/projects/new"
          className="bg-[var(--brand)] text-black font-medium px-4 py-2 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white"
        >
          + New project
        </Link>
      </div>

      <div className="space-y-3">
        {projects.length === 0 && (
          <div className="card p-8 text-center text-[var(--muted)]">No projects yet.</div>
        )}
        {projects.map((p) => {
          const margin = parseFloat(p.margin_ex_vat);
          const marginPct = p.margin_pct_realised;
          const ok = margin >= 0;
          return (
            <Link
              key={p.id}
              href={`/projects/${p.id}`}
              className="card p-4 hover:border-[var(--brand)]/60 transition grid grid-cols-1 md:grid-cols-6 gap-3 items-center"
            >
              <div className="md:col-span-2">
                <p className="text-xs text-[var(--muted)]">{p.client_name}</p>
                <p className="font-semibold">{p.title}</p>
                <p className="text-xs text-[var(--muted)] mt-0.5">{p.site_address || "—"}</p>
              </div>
              <div className="text-xs">
                <StatusChip status={p.status} />
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Quoted</p>
                <p className="font-semibold">{formatZAR(p.quoted_total_inc_vat)}</p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Spent</p>
                <p className="font-semibold">{formatZAR(p.actual_total)}</p>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Margin</p>
                <p className={`font-bold ${ok ? "text-[var(--good)]" : "text-[var(--bad)]"}`}>
                  {ok ? "+" : ""}
                  {formatZAR(margin)}
                </p>
                <p className="text-xs text-[var(--muted)]">{marginPct.toFixed(1)}%</p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
