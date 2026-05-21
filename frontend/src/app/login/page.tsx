"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await api.login(email, password);
      // Cookie is now set; redirect to dashboard
      window.location.href = "/";
    } catch (ex: any) {
      setErr(ex?.message || "Login failed");
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form
        onSubmit={submit}
        className="card p-8 w-full max-w-sm space-y-5"
      >
        <div className="text-center space-y-2">
          <Image
            src="/brand/logo.png"
            alt="Bright Solar Power"
            width={220}
            height={60}
            className="mx-auto h-14 w-auto"
            priority
          />
          <p className="text-sm text-[var(--muted)]">Operations</p>
        </div>

        {err && (
          <div className="bg-rose-500/10 border border-rose-500/40 text-rose-300 text-sm p-3 rounded-lg">
            {err}
          </div>
        )}

        <div>
          <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">
            Email
          </label>
          <input
            type="text"
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@brightsolarpower.co.za"
            required
            autoComplete="email"
            autoFocus
          />
        </div>
        <div>
          <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </div>

        <button
          disabled={busy}
          className="w-full bg-[var(--brand)] text-black font-semibold py-3 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <div className="text-[11px] text-[var(--muted)] pt-4 border-t border-[var(--border)]">
          <p className="font-semibold mb-1">Dev accounts:</p>
          <p>owner@brightsolarpower.co.za · owner123</p>
          <p>foreman@brightsolarpower.co.za · foreman123</p>
          <p>sipho@brightsolarpower.co.za · tech123</p>
          <p>accountant@brightsolarpower.co.za · acct123</p>
        </div>
      </form>
    </div>
  );
}
