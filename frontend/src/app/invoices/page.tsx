"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, formatZAR, type InvoiceStatus, type InvoiceWithProject } from "@/lib/api";

const STATUSES: ("all" | InvoiceStatus)[] = ["all", "draft", "sent", "paid", "cancelled"];

export default function InvoicesIndex() {
  const [invoices, setInvoices] = useState<InvoiceWithProject[]>([]);
  const [filter, setFilter] = useState<"all" | InvoiceStatus>("all");

  useEffect(() => {
    api.listAllInvoices(filter === "all" ? undefined : filter).then(setInvoices);
  }, [filter]);

  const unpaid = invoices.filter((i) => i.status !== "paid" && i.status !== "cancelled");
  const overdue = unpaid.filter((i) => i.is_overdue);
  const totalOutstanding = unpaid.reduce((sum, i) => sum + parseFloat(i.outstanding), 0);
  const totalOverdue = overdue.reduce((sum, i) => sum + parseFloat(i.outstanding), 0);
  const totalPaid = invoices
    .filter((i) => i.status === "paid")
    .reduce((sum, i) => sum + parseFloat(i.total_inc_vat), 0);

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-3xl font-semibold">Invoices</h2>
        <p className="text-[var(--muted)] text-sm">All billing across every project.</p>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPI label="Total outstanding" value={formatZAR(totalOutstanding)} warn={totalOutstanding > 0} />
        <KPI label="Overdue" value={formatZAR(totalOverdue)} warn={totalOverdue > 0} />
        <KPI label="Paid" value={formatZAR(totalPaid)} good />
        <KPI label="Total invoices" value={invoices.length} />
      </section>

      <div className="flex gap-2 flex-wrap">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition ${
              filter === s
                ? "bg-[var(--brand)] border-[var(--brand)] text-black font-medium"
                : "bg-white/5 border-[var(--border)] hover:bg-white/10"
            }`}
          >
            {s === "all" ? "All" : s[0].toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <div className="card divide-y divide-[var(--border)]">
        {invoices.length === 0 && (
          <div className="p-6 text-center text-[var(--muted)] text-sm">No invoices.</div>
        )}
        {invoices.map((i) => (
          <div key={i.id} className="p-4 flex items-start gap-4 flex-wrap">
            <div className="flex-1 min-w-0">
              <p className="font-mono text-sm">{i.invoice_number}</p>
              <p className="text-xs text-[var(--muted)]">
                <Link href={`/projects/${i.project_id}`} className="hover:underline">
                  {i.client_name} · {i.project_title}
                </Link>
              </p>
              <p className="text-[11px] text-[var(--muted)] mt-0.5">
                {i.type} · issued {i.issued_at} · due {i.due_at}
              </p>
            </div>
            <div className="text-right">
              <p className="font-bold">{formatZAR(i.total_inc_vat)}</p>
              <p className="text-[11px] text-[var(--muted)]">
                {i.status === "paid"
                  ? "✓ paid in full"
                  : i.status === "cancelled"
                  ? "cancelled"
                  : `outstanding ${formatZAR(i.outstanding)}`}
              </p>
              {i.is_overdue && (
                <p className="text-[11px] text-[var(--bad)] font-medium">
                  ⚠ {i.days_overdue}d overdue
                </p>
              )}
            </div>
            <a
              href={api.invoicePdfUrl(i.id)}
              target="_blank"
              rel="noreferrer"
              className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 self-center"
            >
              📄 PDF
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

function KPI({ label, value, warn, good }: { label: string; value: string | number; warn?: boolean; good?: boolean }) {
  return (
    <div className="card p-4">
      <p className="text-[11px] uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${warn ? "text-[var(--bad)]" : good ? "text-[var(--good)]" : ""}`}>
        {value}
      </p>
    </div>
  );
}
