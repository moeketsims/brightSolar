"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export default function AcceptButton({
  projectId,
  accepted,
  acceptedBy,
  acceptedAt,
  clientName,
}: {
  projectId: number;
  accepted: boolean;
  acceptedBy: string | null;
  acceptedAt: string | null;
  clientName: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function accept() {
    const name = prompt(
      `Client acceptance — who signed off on behalf of ${clientName}?`,
      clientName
    );
    if (!name) return;
    setBusy(true);
    try {
      await api.acceptQuote(projectId, name.trim());
      router.refresh();
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (accepted) {
    return (
      <div className="chip bg-emerald-500/20 text-emerald-300 flex items-center gap-1.5">
        ✓ Accepted by {acceptedBy}
        {acceptedAt && (
          <span className="text-emerald-400/70 ml-1">
            · {new Date(acceptedAt).toLocaleDateString("en-ZA", { dateStyle: "medium" })}
          </span>
        )}
      </div>
    );
  }

  return (
    <button
      onClick={accept}
      disabled={busy}
      className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500 text-black font-medium hover:bg-emerald-400 disabled:opacity-50"
    >
      {busy ? "…" : "✓ Mark accepted"}
    </button>
  );
}
