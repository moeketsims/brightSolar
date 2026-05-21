"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  formatZAR,
  type Invoice,
  type InvoiceType,
} from "@/lib/api";

const TYPE_LABEL: Record<InvoiceType, string> = {
  deposit: "Deposit",
  progress: "Progress",
  final: "Final",
  retention: "Retention release",
};

const STATUS_META: Record<string, { bg: string; fg: string; label: string }> = {
  draft: { bg: "bg-zinc-500/15", fg: "text-zinc-300", label: "Draft" },
  sent: { bg: "bg-sky-500/15", fg: "text-sky-300", label: "Sent" },
  paid: { bg: "bg-emerald-500/15", fg: "text-emerald-300", label: "Paid" },
  cancelled: { bg: "bg-zinc-500/10", fg: "text-zinc-500", label: "Cancelled" },
};

export default function InvoicesPanel({ projectId }: { projectId: number }) {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [creating, setCreating] = useState(false);
  const [type, setType] = useState<InvoiceType>("deposit");
  const [busy, setBusy] = useState(false);
  const [paymentFor, setPaymentFor] = useState<Invoice | null>(null);

  async function reload() {
    setInvoices(await api.listProjectInvoices(projectId));
  }
  useEffect(() => {
    reload();
  }, [projectId]);

  async function create() {
    setBusy(true);
    try {
      await api.createInvoice(projectId, { type });
      await reload();
      setCreating(false);
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function setStatus(inv: Invoice, status: Invoice["status"]) {
    await api.updateInvoice(inv.id, { status });
    await reload();
    router.refresh();
  }

  async function removeInv(inv: Invoice) {
    if (!confirm(`Delete draft invoice ${inv.invoice_number}?`)) return;
    try {
      await api.deleteInvoice(inv.id);
      await reload();
    } catch (e) {
      alert(String(e));
    }
  }

  const totalOutstanding = invoices.reduce(
    (sum, i) => sum + (i.status === "paid" || i.status === "cancelled" ? 0 : parseFloat(i.outstanding)),
    0
  );
  const totalInvoiced = invoices.reduce(
    (sum, i) => sum + (i.status === "cancelled" ? 0 : parseFloat(i.total_inc_vat)),
    0
  );

  return (
    <div className="card p-5 space-y-3">
      <div className="flex justify-between items-baseline flex-wrap gap-2">
        <h3 className="font-semibold">Invoices &amp; payments</h3>
        <div className="text-xs text-[var(--muted)]">
          {invoices.length} invoices · Invoiced {formatZAR(totalInvoiced)}
          {totalOutstanding > 0 && (
            <span className="text-[var(--bad)] font-medium">
              {" · "}Outstanding {formatZAR(totalOutstanding)}
            </span>
          )}
        </div>
      </div>

      {invoices.length === 0 && (
        <p className="text-xs text-[var(--muted)]">
          No invoices yet. Generate a deposit invoice once the client has accepted the quote.
        </p>
      )}

      <div className="space-y-2">
        {invoices.map((i) => {
          const meta = STATUS_META[i.status];
          const overdue = i.is_overdue;
          return (
            <div
              key={i.id}
              className={`border rounded-lg p-3 ${
                overdue ? "border-rose-500/40" : "border-[var(--border)]"
              }`}
            >
              <div className="flex justify-between items-start gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`chip ${meta.bg} ${meta.fg}`}>{meta.label}</span>
                    {overdue && (
                      <span className="chip bg-rose-500/20 text-rose-300">
                        ⚠ {i.days_overdue}d overdue
                      </span>
                    )}
                    <span className="font-mono text-sm">{i.invoice_number}</span>
                    <span className="text-xs text-[var(--muted)]">· {TYPE_LABEL[i.type]}</span>
                  </div>
                  <div className="text-xs text-[var(--muted)] mt-1">
                    Issued {i.issued_at} · Due {i.due_at}
                    {i.description && <> · {i.description}</>}
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold">{formatZAR(i.total_inc_vat)}</p>
                  {i.status !== "paid" && i.status !== "cancelled" && parseFloat(i.paid_total) > 0 && (
                    <p className="text-[11px] text-[var(--muted)]">
                      Paid {formatZAR(i.paid_total)} · outstanding <span className="text-[var(--bad)] font-medium">{formatZAR(i.outstanding)}</span>
                    </p>
                  )}
                </div>
              </div>
              <div className="flex gap-2 mt-2 flex-wrap">
                <a
                  href={api.invoicePdfUrl(i.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-2.5 py-1 rounded-lg bg-white/10 hover:bg-white/15"
                >
                  📄 PDF
                </a>
                {i.status === "draft" && (
                  <button
                    onClick={() => setStatus(i, "sent")}
                    className="text-xs px-2.5 py-1 rounded-lg bg-sky-500/20 text-sky-300 hover:bg-sky-500/30"
                  >
                    📧 Mark sent
                  </button>
                )}
                {i.status !== "paid" && i.status !== "cancelled" && (
                  <button
                    onClick={() => setPaymentFor(i)}
                    className="text-xs px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
                  >
                    💰 Record payment
                  </button>
                )}
                {i.status !== "cancelled" && i.status !== "paid" && (
                  <button
                    onClick={() => setStatus(i, "cancelled")}
                    className="text-xs px-2.5 py-1 rounded-lg hover:bg-white/10 text-[var(--muted)]"
                  >
                    Cancel
                  </button>
                )}
                {i.status === "draft" && (
                  <button
                    onClick={() => removeInv(i)}
                    className="ml-auto text-xs text-rose-400 hover:underline"
                  >
                    Delete
                  </button>
                )}
              </div>
              {i.payments.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[var(--border)] space-y-1">
                  {i.payments.map((p) => (
                    <div key={p.id} className="text-xs flex justify-between">
                      <span>
                        {p.received_at} · {p.method.toUpperCase()}
                        {p.reference && ` · ref ${p.reference}`}
                      </span>
                      <span className="text-emerald-300 font-medium">
                        + {formatZAR(p.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!creating ? (
        <button
          onClick={() => setCreating(true)}
          className="w-full text-sm py-2 border border-dashed border-[var(--border)] rounded-lg hover:border-[var(--brand)]/60 hover:text-[var(--brand)] transition"
        >
          + Generate invoice
        </button>
      ) : (
        <div className="border border-[var(--border)] rounded-lg p-3 bg-black/20 space-y-3">
          <select value={type} onChange={(e) => setType(e.target.value as InvoiceType)} className="text-sm">
            <option value="deposit">Deposit invoice</option>
            <option value="progress">Progress invoice</option>
            <option value="final">Final invoice</option>
            <option value="retention">Retention release</option>
          </select>
          <p className="text-[11px] text-[var(--muted)]">
            Amount is auto-computed from the project quoted total minus already-invoiced portions.
            You can override on the invoice once drafted.
          </p>
          <div className="flex gap-2">
            <button
              onClick={create}
              disabled={busy}
              className="bg-[var(--brand)] text-black text-sm font-medium px-3 py-1.5 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white disabled:opacity-50"
            >
              {busy ? "…" : "Create draft"}
            </button>
            <button
              onClick={() => setCreating(false)}
              className="text-xs text-[var(--muted)] hover:underline"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {paymentFor && (
        <PaymentModal
          invoice={paymentFor}
          onClose={() => setPaymentFor(null)}
          onSaved={async () => {
            setPaymentFor(null);
            await reload();
            router.refresh();
          }}
        />
      )}
    </div>
  );
}

function PaymentModal({
  invoice,
  onClose,
  onSaved,
}: {
  invoice: Invoice;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [amount, setAmount] = useState(invoice.outstanding);
  const [method, setMethod] = useState("eft");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.recordPayment(invoice.id, {
        amount,
        method,
        reference: reference || undefined,
        note: note || undefined,
      });
      onSaved();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <form
        onSubmit={save}
        className="card p-5 space-y-3 max-w-md w-full"
      >
        <h3 className="font-semibold">Record payment on {invoice.invoice_number}</h3>
        <p className="text-xs text-[var(--muted)]">
          Outstanding: <span className="text-white">{formatZAR(invoice.outstanding)}</span>
        </p>
        <div>
          <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">Amount (R)</label>
          <input type="number" step="0.01" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </div>
        <div>
          <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">Method</label>
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="eft">EFT</option>
            <option value="cash">Cash</option>
            <option value="card">Card</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">Reference</label>
          <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="EFT ref, cheque no..." />
        </div>
        <div>
          <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">Note</label>
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional" />
        </div>
        <div className="flex gap-2 pt-2">
          <button
            disabled={busy}
            className="bg-[var(--brand)] text-black text-sm font-medium px-4 py-2 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white disabled:opacity-50 flex-1"
          >
            {busy ? "Saving…" : "Record payment"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-[var(--muted)] px-3"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
