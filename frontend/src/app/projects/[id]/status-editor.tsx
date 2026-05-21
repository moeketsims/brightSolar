"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, type ProjectStatus } from "@/lib/api";

const options: ProjectStatus[] = [
  "quoting",
  "quoted",
  "accepted",
  "in_progress",
  "completed",
  "invoiced",
  "paid",
  "lost",
];

export default function StatusEditor({
  projectId,
  status,
}: {
  projectId: number;
  status: ProjectStatus;
}) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);

  async function onChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = e.target.value as ProjectStatus;
    setSaving(true);
    await api.updateProject(projectId, { status: next });
    setSaving(false);
    router.refresh();
  }

  return (
    <select
      disabled={saving}
      value={status}
      onChange={onChange}
      className="text-xs py-1 px-2 w-auto"
      style={{ width: "auto" }}
    >
      {options.map((o) => (
        <option key={o} value={o}>
          Set: {o.replace("_", " ")}
        </option>
      ))}
    </select>
  );
}
