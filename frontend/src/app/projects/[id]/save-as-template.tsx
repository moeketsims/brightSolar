"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function SaveAsTemplate({
  projectId,
  defaultName,
}: {
  projectId: number;
  defaultName: string;
}) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    const name = prompt(
      "Template name (helps future-you pick the right one when quoting):",
      defaultName
    );
    if (!name) return;
    setSaving(true);
    try {
      await api.saveTemplateFromProject(projectId, name);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      alert(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <button
      onClick={save}
      disabled={saving}
      className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 disabled:opacity-50"
    >
      {saving ? "Saving…" : saved ? "✓ Saved" : "📋 Save as template"}
    </button>
  );
}
