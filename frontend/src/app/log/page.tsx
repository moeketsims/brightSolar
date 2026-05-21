"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  formatZAR,
  type ExpenseCategory,
  type ProjectSummary,
} from "@/lib/api";
import { newIdempotencyKey, queueExpense } from "@/lib/offline-queue";

const CATEGORIES: { value: ExpenseCategory; label: string; icon: string }[] = [
  { value: "diesel", label: "Diesel", icon: "⛽" },
  { value: "lodging", label: "Lodging", icon: "🏨" },
  { value: "meals", label: "Meals", icon: "🍽" },
  { value: "tolls", label: "Tolls", icon: "🛣" },
  { value: "materials", label: "Materials", icon: "🔧" },
  { value: "labour", label: "Labour", icon: "👷" },
  { value: "equipment_hire", label: "Equipment", icon: "🏗" },
  { value: "other", label: "Other", icon: "◦" },
];

type Step = "photo" | "project" | "category" | "amount" | "done";

export default function LogReceiptPage() {
  const [step, setStep] = useState<Step>("photo");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [category, setCategory] = useState<ExpenseCategory | null>(null);
  const [amount, setAmount] = useState("");
  const [desc, setDesc] = useState("");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((e) => setErr(String(e)));
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => setCoords(null),
        { enableHighAccuracy: false, timeout: 4000 }
      );
    }
  }, []);

  async function onFile(f: File | null) {
    setFile(f);
    if (f) {
      const url = URL.createObjectURL(f);
      setPreview(url);
      // Kick off OCR in the background; prefill amount if it returns before the user types one
      api
        .ocrReceipt(f)
        .then((r) => {
          if (r.amount && !amount) setAmount(String(r.amount));
        })
        .catch(() => {});
      setStep("project");
    }
  }

  async function submit() {
    if (!project || !category || !amount) return;
    setSaving(true);
    setErr(null);
    const key = newIdempotencyKey();
    const commonPayload = {
      idempotency_key: key,
      project_id: project.id,
      category: category as string,
      amount: String(amount),
      description: desc || undefined,
      latitude: coords?.lat ?? null,
      longitude: coords?.lng ?? null,
    };
    // Try online first. If offline or fetch fails, queue locally.
    if (typeof navigator !== "undefined" && navigator.onLine) {
      try {
        await api.uploadExpense({
          project_id: project.id,
          category,
          amount,
          description: desc || undefined,
          latitude: coords?.lat ?? null,
          longitude: coords?.lng ?? null,
          file,
          idempotency_key: key,
        } as any);
        setStep("done");
        setSaving(false);
        return;
      } catch (e) {
        // Fall through to queue if network error; rethrow auth errors
        if (String(e).includes("401")) {
          setErr("Not signed in — please log in again");
          setSaving(false);
          return;
        }
      }
    }
    // Offline or failed — queue locally
    try {
      await queueExpense({
        ...commonPayload,
        file_blob: file || undefined,
        file_name: file?.name || null,
      });
      setStep("done");
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }

  function reset() {
    setFile(null);
    setPreview(null);
    setProject(null);
    setCategory(null);
    setAmount("");
    setDesc("");
    setStep("photo");
  }

  const activeProjects = projects.filter((p) =>
    ["accepted", "in_progress", "quoted"].includes(p.status)
  );
  const listed = activeProjects.length > 0 ? activeProjects : projects;

  return (
    <div className="max-w-md mx-auto">
      <header className="mb-5">
        <h2 className="text-2xl font-semibold">Log a receipt</h2>
        <p className="text-[var(--muted)] text-sm">
          Snap → pick project → category → amount. Everything gets stored against the project.
        </p>
      </header>

      {err && <div className="card p-3 text-[var(--bad)] text-sm mb-3">{err}</div>}

      <ProgressBar step={step} />

      {step === "photo" && (
        <div className="card p-6 text-center space-y-4">
          <p className="text-sm text-[var(--muted)]">
            Point at the receipt. Camera opens full-screen on phone.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => onFile(e.target.files?.[0] || null)}
            className="hidden"
          />
          <button
            onClick={() => fileRef.current?.click()}
            className="w-full bg-[var(--brand)] text-black font-semibold rounded-2xl py-10 text-2xl hover:bg-[var(--brand-dark)] hover:text-white"
          >
            📸 Snap receipt
          </button>
          <button
            onClick={() => setStep("project")}
            className="text-xs text-[var(--muted)] underline"
          >
            Skip photo (I'll enter by hand)
          </button>
        </div>
      )}

      {step !== "photo" && step !== "done" && preview && (
        <div className="card p-3 mb-3 flex items-center gap-3">
          <img src={preview} alt="receipt" className="w-16 h-16 object-cover rounded border border-[var(--border)]" />
          <div className="flex-1 text-xs">
            <p className="text-[var(--muted)]">Receipt captured</p>
            <button
              onClick={() => {
                setFile(null);
                setPreview(null);
                setStep("photo");
              }}
              className="text-[var(--brand)] underline"
            >
              retake
            </button>
          </div>
        </div>
      )}

      {step === "project" && (
        <div className="card p-4 space-y-2">
          <h3 className="font-semibold text-sm mb-2">Which project?</h3>
          {listed.length === 0 && (
            <p className="text-xs text-[var(--muted)]">No projects. Create one first.</p>
          )}
          {listed.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                setProject(p);
                setStep("category");
              }}
              className="w-full text-left p-3 rounded-lg hover:bg-white/5 border border-[var(--border)] transition"
            >
              <p className="font-medium text-sm">{p.title}</p>
              <p className="text-xs text-[var(--muted)]">
                {p.client_name} · {p.status.replace("_", " ")}
              </p>
            </button>
          ))}
        </div>
      )}

      {step === "category" && (
        <div className="card p-4 space-y-3">
          <div className="flex justify-between items-baseline">
            <h3 className="font-semibold text-sm">What was it for?</h3>
            <button onClick={() => setStep("project")} className="text-xs text-[var(--muted)]">
              ← change project
            </button>
          </div>
          <p className="text-xs text-[var(--muted)]">
            Against: <span className="text-white">{project?.title}</span>
          </p>
          <div className="grid grid-cols-2 gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                onClick={() => {
                  setCategory(c.value);
                  setStep("amount");
                }}
                className="card p-4 hover:border-[var(--brand)]/60 transition flex flex-col items-center gap-1"
              >
                <span className="text-2xl">{c.icon}</span>
                <span className="text-sm font-medium">{c.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {step === "amount" && (
        <div className="card p-4 space-y-3">
          <div className="flex justify-between items-baseline">
            <h3 className="font-semibold text-sm">How much?</h3>
            <button onClick={() => setStep("category")} className="text-xs text-[var(--muted)]">
              ← change category
            </button>
          </div>
          <p className="text-xs text-[var(--muted)]">
            {CATEGORIES.find((c) => c.value === category)?.label} on{" "}
            <span className="text-white">{project?.title}</span>
          </p>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-3xl text-[var(--muted)]">R</span>
              <input
                type="number"
                inputMode="decimal"
                step="0.01"
                autoFocus
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="text-3xl font-bold py-3"
                placeholder="0.00"
              />
            </div>
            <input
              placeholder="Note (optional) — e.g. Engen, Kimberley"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
            />
          </div>
          {coords && (
            <p className="text-[11px] text-[var(--muted)]">
              📍 Location captured: {coords.lat.toFixed(4)}, {coords.lng.toFixed(4)}
            </p>
          )}
          <button
            onClick={submit}
            disabled={saving || !amount}
            className="w-full bg-[var(--brand)] text-black font-semibold py-4 rounded-xl text-lg hover:bg-[var(--brand-dark)] hover:text-white disabled:opacity-50"
          >
            {saving ? "Saving…" : `Log ${amount ? formatZAR(amount) : "expense"}`}
          </button>
        </div>
      )}

      {step === "done" && (
        <div className="card p-8 text-center space-y-4">
          <div className="text-5xl">✅</div>
          <div>
            <p className="font-semibold">Expense logged</p>
            <p className="text-xs text-[var(--muted)] mt-1">
              Against <span className="text-white">{project?.title}</span>
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <button
              onClick={reset}
              className="bg-[var(--brand)] text-black font-semibold py-3 rounded-xl hover:bg-[var(--brand-dark)] hover:text-white"
            >
              Log another
            </button>
            <a
              href={`/projects/${project?.id}`}
              className="text-sm text-[var(--brand)] underline"
            >
              View project →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

function ProgressBar({ step }: { step: Step }) {
  const steps: Step[] = ["photo", "project", "category", "amount"];
  const idx = step === "done" ? steps.length : steps.indexOf(step);
  return (
    <div className="flex gap-1 mb-3">
      {steps.map((s, i) => (
        <div
          key={s}
          className={`flex-1 h-1 rounded transition ${
            i <= idx ? "bg-[var(--brand)]" : "bg-white/10"
          }`}
        />
      ))}
    </div>
  );
}
