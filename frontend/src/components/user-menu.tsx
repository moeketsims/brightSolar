"use client";

import { useEffect, useState } from "react";
import { api, type CurrentUser } from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
  owner: "Owner",
  foreman: "Foreman",
  tech: "Technician",
  accountant: "Accountant",
};

export default function UserMenu() {
  const [me, setMe] = useState<CurrentUser | null>(null);

  useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null));
  }, []);

  async function logout() {
    await api.logout();
    window.location.href = "/login";
  }

  if (!me) return null;

  return (
    <div className="mt-6 pt-4 border-t border-[var(--border)] space-y-2 hidden md:block">
      <div>
        <p className="text-sm font-medium truncate">{me.name}</p>
        <p className="text-[11px] text-[var(--muted)] truncate">{me.email}</p>
        <span className="chip bg-white/5 text-white/70 mt-1">
          {ROLE_LABEL[me.role] || me.role}
        </span>
      </div>
      <button
        onClick={logout}
        className="w-full text-left text-xs text-[var(--muted)] hover:text-white py-1.5 px-2 rounded hover:bg-white/5"
      >
        Sign out
      </button>
    </div>
  );
}
