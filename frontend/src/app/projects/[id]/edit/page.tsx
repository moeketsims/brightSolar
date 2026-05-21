"use client";

import Link from "next/link";
import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { api, type ProjectDetail, type ProjectInputs } from "@/lib/api";
import { ProjectForm } from "@/components/project-form";

const CLOSED: string[] = ["completed", "invoiced", "paid", "lost"];

export default function EditProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getProject(Number(id)).then(setProject).catch((e) => setErr(String(e)));
  }, [id]);

  if (!project) {
    return <div className="text-[var(--muted)]">Loading…</div>;
  }

  const initial: ProjectInputs = {
    client_id: project.client.id,
    title: project.title,
    service_type: project.service_type,
    site_address: project.site_address,
    description: project.description,
    one_way_distance_km: project.one_way_distance_km,
    return_trips: project.return_trips,
    vehicle_id: project.vehicle?.id ?? null,
    estimated_hours_on_site: project.estimated_hours_on_site,
    estimated_travel_hours: project.estimated_travel_hours,
    overnight_nights: project.overnight_nights,
    people_on_site: project.people_on_site,
    contingency_pct: project.contingency_pct,
    margin_pct: project.margin_pct,
    materials: project.materials,
    tech_assignments: project.tech_assignments,
  };

  async function handleSubmit(inputs: ProjectInputs) {
    setSaving(true);
    setErr(null);
    try {
      await api.updateProject(Number(id), inputs);
      router.push(`/projects/${id}`);
    } catch (e) {
      setErr(String(e));
      setSaving(false);
    }
  }

  const locked = CLOSED.includes(project.status);

  return (
    <div className="space-y-4">
      <header className="flex justify-between items-start">
        <div>
          <Link href={`/projects/${id}`} className="text-xs text-[var(--muted)] hover:underline">
            ← Back to project
          </Link>
          <h2 className="text-3xl font-semibold mt-2">Edit: {project.title}</h2>
          <p className="text-[var(--muted)] text-sm">
            Change anything — techs, days, materials, distance. Every change is logged to
            the activity feed with the quote impact.
          </p>
        </div>
      </header>
      <ProjectForm
        initial={initial}
        submitLabel="Save changes"
        onSubmit={handleSubmit}
        busy={saving}
        err={err}
        locked={locked}
      />
    </div>
  );
}
