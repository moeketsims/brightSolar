"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ProjectInputs } from "@/lib/api";
import { ProjectForm, emptyInputs } from "@/components/project-form";

export default function NewProjectPage() {
  const router = useRouter();
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(inputs: ProjectInputs) {
    setSaving(true);
    setErr(null);
    try {
      const p = await api.createProject(inputs);
      router.push(`/projects/${p.id}`);
    } catch (e) {
      setErr(String(e));
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <header>
        <h2 className="text-3xl font-semibold">Quote a new project</h2>
        <p className="text-[var(--muted)] text-sm">
          Fill it in honestly — travel, nights on site, every tech-hour. The quote on the
          right updates live. You can edit any of this later as scope grows.
        </p>
      </header>
      <ProjectForm
        initial={emptyInputs()}
        submitLabel="Save quote"
        onSubmit={handleSubmit}
        busy={saving}
        err={err}
        showTemplatePicker
      />
    </div>
  );
}
