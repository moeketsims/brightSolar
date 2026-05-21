"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, type ExpenseCategory } from "@/lib/api";

const cats: ExpenseCategory[] = [
  "diesel",
  "lodging",
  "meals",
  "tolls",
  "materials",
  "labour",
  "equipment_hire",
  "other",
];

export default function QuickExpense({ projectId }: { projectId: number }) {
  const router = useRouter();
  const [cat, setCat] = useState<ExpenseCategory>("diesel");
  const [amount, setAmount] = useState("");
  const [desc, setDesc] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!amount) return;
    setSaving(true);
    await api.uploadExpense({
      project_id: projectId,
      category: cat,
      amount,
      description: desc || undefined,
      file,
    });
    setAmount("");
    setDesc("");
    setFile(null);
    (e.target as HTMLFormElement).reset();
    setSaving(false);
    router.refresh();
  }

  return (
    <form
      onSubmit={submit}
      className="grid grid-cols-2 md:grid-cols-5 gap-2 p-3 bg-white/5 rounded-lg border border-[var(--border)]"
    >
      <select value={cat} onChange={(e) => setCat(e.target.value as ExpenseCategory)} className="text-sm">
        {cats.map((c) => <option key={c}>{c}</option>)}
      </select>
      <input
        type="number"
        step="0.01"
        placeholder="Amount (R)"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
        className="text-sm"
      />
      <input
        placeholder="Note (optional)"
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
        className="md:col-span-2 text-sm"
      />
      <label className="text-xs flex items-center gap-1.5 cursor-pointer bg-black/40 border border-[var(--border)] rounded-lg px-3 py-2">
        <input
          type="file"
          accept="image/*"
          capture="environment"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="hidden"
        />
        📷 {file ? "1 photo" : "Receipt"}
      </label>
      <button
        disabled={saving}
        className="md:col-span-5 bg-[var(--brand)] text-black font-medium py-2 rounded-lg text-sm hover:bg-[var(--brand-dark)] hover:text-white disabled:opacity-50"
      >
        {saving ? "Saving…" : "Log expense"}
      </button>
    </form>
  );
}
