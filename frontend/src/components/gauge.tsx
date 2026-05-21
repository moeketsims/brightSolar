export function MarginGauge({
  burn,
  colour,
  label,
}: {
  burn: number;
  colour: "green" | "amber" | "red";
  label?: string;
}) {
  const pct = Math.min(burn, 1.3) * 100;
  const colourMap = {
    green: "var(--good)",
    amber: "var(--warn)",
    red: "var(--bad)",
  };
  return (
    <div className="space-y-1.5">
      {label !== undefined && (
        <div className="flex justify-between text-[11px] uppercase tracking-wide text-[var(--muted)]">
          <span>{label}</span>
          <span className="font-medium">{Math.round(burn * 100)}% burned</span>
        </div>
      )}
      <div className="gauge-track">
        <div
          className="gauge-fill"
          style={{
            width: `${pct}%`,
            background: colourMap[colour],
            boxShadow: `0 0 12px ${colourMap[colour]}55`,
          }}
        />
        <div
          className="absolute top-0 bottom-0"
          style={{ left: `${100}%`, borderLeft: "1px dashed rgba(255,255,255,0.25)" }}
        />
      </div>
    </div>
  );
}

export function StatusChip({ status }: { status: string }) {
  const map: Record<string, { bg: string; fg: string; label: string }> = {
    quoting: { bg: "bg-sky-500/15", fg: "text-sky-300", label: "Quoting" },
    quoted: { bg: "bg-indigo-500/15", fg: "text-indigo-300", label: "Quoted" },
    accepted: { bg: "bg-violet-500/15", fg: "text-violet-300", label: "Accepted" },
    in_progress: { bg: "bg-amber-500/15", fg: "text-amber-300", label: "On site" },
    completed: { bg: "bg-emerald-500/15", fg: "text-emerald-300", label: "Completed" },
    invoiced: { bg: "bg-teal-500/15", fg: "text-teal-300", label: "Invoiced" },
    paid: { bg: "bg-emerald-600/15", fg: "text-emerald-200", label: "Paid" },
    lost: { bg: "bg-zinc-500/15", fg: "text-zinc-400", label: "Lost" },
  };
  const c = map[status] || { bg: "bg-white/10", fg: "text-white/70", label: status };
  return <span className={`chip ${c.bg} ${c.fg}`}>{c.label}</span>;
}
