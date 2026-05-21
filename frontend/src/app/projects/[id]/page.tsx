"use client";

import Link from "next/link";
import { useEffect, useState, use } from "react";
import { notFound } from "next/navigation";
import { api, formatZAR, formatZARPrecise, absoluteUrl, type ProjectDetail } from "@/lib/api";
import { MarginGauge, StatusChip } from "@/components/gauge";
import StatusEditor from "./status-editor";
import QuickExpense from "./quick-expense";
import ActivitiesPanel from "./activities-panel";
import ActivityFeed from "./activity-feed";
import ReconciliationPanel from "./reconciliation-panel";
import SaveAsTemplate from "./save-as-template";
import AcceptButton from "./accept-button";
import InvoicesPanel from "./invoices-panel";

const CATEGORY_LABEL: Record<string, string> = {
  diesel: "Diesel",
  lodging: "Lodging",
  meals: "Meals",
  tolls: "Tolls",
  materials: "Materials",
  labour: "Labour",
  equipment_hire: "Equipment hire",
  other: "Other",
};

const CLOSED = ["completed", "invoiced", "paid", "lost"];

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [p, setP] = useState<ProjectDetail | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api
      .getProject(Number(id))
      .then(setP)
      .catch(() => setMissing(true));
  }, [id]);

  if (missing) notFound();
  if (!p) return <div className="text-[var(--muted)]">Loading…</div>;

  const actualTotal = parseFloat(p.actuals.total);
  const quotedExVat = p.quoted.total_ex_vat;
  const quotedIncVat = p.quoted.total_inc_vat;
  const burn = quotedExVat > 0 ? actualTotal / quotedExVat : 0;
  const colour: "green" | "amber" | "red" = burn < 0.7 ? "green" : burn < 1.0 ? "amber" : "red";
  const margin = quotedExVat - actualTotal;
  const locked = CLOSED.includes(p.status);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap justify-between items-start gap-4">
        <div>
          <Link href="/projects" className="text-xs text-[var(--muted)] hover:underline">
            ← All projects
          </Link>
          <p className="text-sm text-[var(--muted)] mt-2">{p.client.name}</p>
          <h2 className="text-3xl font-semibold">{p.title}</h2>
          <p className="text-sm text-[var(--muted)]">{p.site_address || "—"}</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <StatusChip status={p.status} />
          <StatusEditor projectId={p.id} status={p.status} />
          <Link
            href={`/projects/${p.id}/edit`}
            className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15"
          >
            ✎ Edit quote
          </Link>
          <a
            href={api.quotePdfUrl(p.id)}
            target="_blank"
            rel="noreferrer"
            className="text-xs px-3 py-1.5 rounded-lg bg-[var(--brand)] text-black font-medium hover:bg-[var(--brand-dark)] hover:text-white"
          >
            📄 Quote PDF
          </a>
          <SaveAsTemplate projectId={p.id} defaultName={p.title} />
          <AcceptButton
            projectId={p.id}
            accepted={!!p.accepted_at}
            acceptedBy={p.accepted_by_name}
            acceptedAt={p.accepted_at}
            clientName={p.client.name}
          />
        </div>
      </header>

      {locked && <ReconciliationPanel projectId={p.id} />}

      <section className="card p-5 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="md:col-span-2">
          <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">Budget health</p>
          <div className="mt-3">
            <MarginGauge burn={burn} colour={colour} label="Actuals vs quoted (ex VAT)" />
          </div>
          <p className="text-xs text-[var(--muted)] mt-2">
            At 70% you enter amber; above 100% you're burning margin.
          </p>
        </div>
        <Stat label="Quoted (inc VAT)" value={formatZAR(quotedIncVat)} />
        <Stat
          label={margin < 0 ? "OVER BUDGET by" : "Remaining budget"}
          value={formatZAR(Math.abs(margin))}
          tone={margin < 0 ? "bad" : "good"}
        />
      </section>

      <InvoicesPanel projectId={p.id} />

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ActivitiesPanel projectId={p.id} initial={p.activities} locked={locked} />
        <ActivityFeed projectId={p.id} events={p.events} />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5 space-y-3">
          <div className="flex justify-between items-baseline">
            <h3 className="font-semibold">Quoted breakdown</h3>
            <Link href={`/projects/${p.id}/edit`} className="text-xs text-[var(--brand)]">
              Edit inputs →
            </Link>
          </div>
          <div className="space-y-2">
            {p.quoted.lines.length === 0 && (
              <p className="text-xs text-[var(--muted)]">No cost lines.</p>
            )}
            {p.quoted.lines.map((l) => {
              const actualForKey = parseFloat(p.actuals.by_category[categoryForKey(l.key)] || "0");
              const delta = actualForKey - l.amount;
              return (
                <div key={l.key} className="flex justify-between text-sm">
                  <div className="min-w-0 pr-2">
                    <p>{l.label}</p>
                    <p className="text-[11px] text-[var(--muted)]">{l.detail}</p>
                    {actualForKey > 0 && (
                      <p className={`text-[11px] mt-0.5 ${delta > 0 ? "text-[var(--bad)]" : "text-[var(--good)]"}`}>
                        Actual: {formatZAR(actualForKey)} ({delta >= 0 ? "+" : ""}
                        {formatZAR(delta)})
                      </p>
                    )}
                  </div>
                  <p className="font-semibold whitespace-nowrap">{formatZARPrecise(l.amount)}</p>
                </div>
              );
            })}
          </div>
          <div className="border-t border-[var(--border)] pt-3 space-y-1 text-sm">
            <Row label="Subtotal" v={p.quoted.subtotal} />
            <Row label="+ Contingency" v={p.quoted.contingency} subdued />
            <Row label="+ Margin" v={p.quoted.margin} subdued />
            <Row label="Total ex VAT" v={p.quoted.total_ex_vat} strong />
            <Row label="+ VAT" v={p.quoted.vat} subdued />
            <div className="flex justify-between pt-1 items-center">
              <span className="text-xs uppercase text-[var(--muted)]">Quote</span>
              <span className="text-xl font-bold text-[var(--brand)]">
                {formatZARPrecise(p.quoted.total_inc_vat)}
              </span>
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-3">
          <div className="flex justify-between items-baseline">
            <h3 className="font-semibold">Actual expenses</h3>
            <span className="text-sm">
              Total: <span className="font-bold">{formatZAR(actualTotal)}</span>
            </span>
          </div>

          <QuickExpense projectId={p.id} />

          {Object.keys(p.actuals.by_category).length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {Object.entries(p.actuals.by_category).map(([cat, amt]) => (
                <span key={cat} className="chip bg-white/5 text-white/80">
                  {CATEGORY_LABEL[cat] || cat}: {formatZAR(amt)}
                </span>
              ))}
            </div>
          )}

          <div className="space-y-2 pt-2 max-h-[600px] overflow-y-auto">
            {p.expenses.length === 0 && (
              <p className="text-xs text-[var(--muted)]">No expenses yet.</p>
            )}
            {p.expenses.map((e) => {
              const url = absoluteUrl(e.receipt_path);
              return (
                <div
                  key={e.id}
                  className="flex gap-3 items-start border-t border-[var(--border)] pt-2 first:border-t-0 first:pt-0"
                >
                  {url ? (
                    <a href={url} target="_blank" rel="noreferrer" className="shrink-0">
                      <img
                        src={url}
                        alt="receipt"
                        className="w-14 h-14 object-cover rounded border border-[var(--border)]"
                      />
                    </a>
                  ) : (
                    <div className="w-14 h-14 rounded border border-dashed border-[var(--border)] flex items-center justify-center text-[var(--muted)] text-[10px] shrink-0">
                      no receipt
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-baseline">
                      <p className="text-sm">
                        <span className="text-[var(--brand)]">{CATEGORY_LABEL[e.category] || e.category}</span>
                        {e.description && <span className="text-white/70"> · {e.description}</span>}
                      </p>
                      <p className="font-semibold">{formatZAR(e.amount)}</p>
                    </div>
                    <p className="text-[11px] text-[var(--muted)]">
                      {new Date(e.incurred_at).toLocaleString("en-ZA", { dateStyle: "medium", timeStyle: "short" })}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="card p-5">
        <h3 className="font-semibold mb-3">Quote inputs (snapshot)</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <Info label="Distance (one way)" v={`${p.one_way_distance_km} km × ${p.return_trips} return`} />
          <Info label="Vehicle" v={p.vehicle ? `${p.vehicle.name} — ${p.vehicle.fuel_consumption_l_per_100km} L/100km` : "—"} />
          <Info label="Hours on site" v={`${p.estimated_hours_on_site}h`} />
          <Info
            label="Overnight"
            v={p.overnight_nights > 0 ? `${p.overnight_nights} night(s) × ${p.people_on_site} pax` : "—"}
          />
          <Info label="Diesel price snap" v={`R${p.diesel_price_snapshot}/L`} />
          <Info label="Lodging rate snap" v={`R${p.lodging_rate_snapshot}/night`} />
          <Info label="Per diem snap" v={`R${p.per_diem_snapshot}/day`} />
          <Info label="Margin / Contingency" v={`${p.margin_pct}% / ${p.contingency_pct}%`} />
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" }) {
  const colour = tone === "bad" ? "text-[var(--bad)]" : tone === "good" ? "text-[var(--good)]" : "";
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`text-xl font-bold mt-1 ${colour}`}>{value}</p>
    </div>
  );
}

function Row({ label, v, strong, subdued }: { label: string; v: number; strong?: boolean; subdued?: boolean }) {
  return (
    <div className="flex justify-between items-center">
      <span className={subdued ? "text-[var(--muted)] text-xs" : ""}>{label}</span>
      <span className={strong ? "font-bold" : subdued ? "text-sm" : "font-semibold"}>
        {formatZARPrecise(v)}
      </span>
    </div>
  );
}

function Info({ label, v }: { label: string; v: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p>{v}</p>
    </div>
  );
}

function categoryForKey(key: string): string {
  switch (key) {
    case "diesel":
      return "diesel";
    case "vehicle_wear":
      return "diesel";
    case "labour":
      return "labour";
    case "lodging":
      return "lodging";
    case "per_diem":
      return "meals";
    case "materials":
      return "materials";
    default:
      return key;
  }
}
