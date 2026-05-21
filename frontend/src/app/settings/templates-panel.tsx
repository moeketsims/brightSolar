"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ServiceTemplate } from "@/lib/api";

export default function TemplatesPanel() {
  const [templates, setTemplates] = useState<ServiceTemplate[]>([]);

  async function reload() {
    setTemplates(await api.listTemplates());
  }
  useEffect(() => {
    reload();
  }, []);

  async function remove(id: number) {
    if (!confirm("Delete this template? Existing projects aren't affected.")) return;
    await api.deleteTemplate(id);
    await reload();
  }

  return (
    <div className="card p-5 space-y-3">
      <div className="flex justify-between items-baseline">
        <h3 className="font-semibold">Quote templates</h3>
        <span className="text-xs text-[var(--muted)]">
          {templates.length} saved · used when quoting new projects
        </span>
      </div>
      <p className="text-xs text-[var(--muted)]">
        Templates bottle the shape of a typical job (activities, BOM, markups). Save a
        completed project as a template from its page, or tune existing ones here.
      </p>
      <div className="space-y-2">
        {templates.length === 0 && (
          <p className="text-xs text-[var(--muted)]">
            No templates yet. Complete a project, then "Save as template" from the project page.
          </p>
        )}
        {templates.map((t) => {
          const matTotal = t.materials.reduce(
            (sum, m) => sum + Number(m.qty || 0) * Number(m.unit_cost || 0),
            0
          );
          return (
            <div
              key={t.id}
              className="border border-[var(--border)] rounded-lg p-3 flex items-start gap-3"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm">{t.name}</p>
                <p className="text-[11px] text-[var(--muted)]">
                  {t.service_type.replace("_", " ")} · {t.activities.length} activities · {t.materials.length} materials
                  {matTotal > 0 && ` (BOM ≈ R${Math.round(matTotal).toLocaleString("en-ZA")})`}
                </p>
                {t.description && (
                  <p className="text-[11px] text-[var(--muted)] mt-1 italic">{t.description}</p>
                )}
              </div>
              <button
                onClick={() => remove(t.id)}
                className="text-[var(--bad)] text-xs hover:underline"
              >
                Delete
              </button>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] text-[var(--muted)]">
        <Link href="/projects/new" className="text-[var(--brand)] hover:underline">
          Start a new quote
        </Link>{" "}
        to use these templates.
      </p>
    </div>
  );
}
