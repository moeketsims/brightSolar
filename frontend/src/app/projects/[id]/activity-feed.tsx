"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, formatZAR, type ProjectEvent } from "@/lib/api";

const KIND_META: Record<string, { icon: string; colour: string; label: string }> = {
  created: { icon: "✨", colour: "text-emerald-300", label: "Created" },
  updated: { icon: "✎", colour: "text-sky-300", label: "Updated" },
  status_changed: { icon: "◈", colour: "text-violet-300", label: "Status" },
  scope_changed: { icon: "☑", colour: "text-amber-300", label: "Scope" },
  tech_added: { icon: "＋", colour: "text-emerald-300", label: "Tech added" },
  tech_removed: { icon: "−", colour: "text-rose-300", label: "Tech removed" },
  note: { icon: "💬", colour: "text-white/80", label: "Note" },
};

export default function ActivityFeed({
  projectId,
  events,
}: {
  projectId: number;
  events: ProjectEvent[];
}) {
  const router = useRouter();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function postNote(e: React.FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    setBusy(true);
    await api.addNote(projectId, note.trim());
    setNote("");
    setBusy(false);
    router.refresh();
  }

  return (
    <div className="card p-5 space-y-3">
      <div className="flex justify-between items-baseline">
        <h3 className="font-semibold">Change log & notes</h3>
        <span className="text-xs text-[var(--muted)]">{events.length} entries</span>
      </div>

      <form onSubmit={postNote} className="flex gap-2">
        <input
          placeholder="Add a note — e.g. 'Scope grew: client wants extra outlet'"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="text-sm"
        />
        <button
          disabled={!note.trim() || busy}
          className="bg-[var(--brand)] text-black font-medium rounded-lg text-sm px-3 disabled:opacity-50 hover:bg-[var(--brand-dark)] hover:text-white"
        >
          {busy ? "…" : "Post"}
        </button>
      </form>

      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {events.length === 0 && (
          <p className="text-xs text-[var(--muted)]">No activity yet.</p>
        )}
        {events.map((e) => {
          const meta = KIND_META[e.kind] || KIND_META.updated;
          const delta =
            e.quote_before != null && e.quote_after != null
              ? parseFloat(e.quote_after) - parseFloat(e.quote_before)
              : null;
          return (
            <div key={e.id} className="flex gap-3 border-t border-[var(--border)] pt-3 first:border-t-0 first:pt-0">
              <div className={`text-lg ${meta.colour}`}>{meta.icon}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm">{e.summary}</p>
                {e.details && (
                  <pre className="text-[11px] text-[var(--muted)] whitespace-pre-wrap font-sans mt-1">
                    {e.details}
                  </pre>
                )}
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[11px] text-[var(--muted)]">
                    {new Date(e.created_at).toLocaleString("en-ZA", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </span>
                  {delta !== null && delta !== 0 && (
                    <span
                      className={`chip ${
                        delta > 0 ? "bg-rose-500/15 text-rose-300" : "bg-emerald-500/15 text-emerald-300"
                      }`}
                    >
                      Quote {delta > 0 ? "+" : ""}
                      {formatZAR(delta)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
