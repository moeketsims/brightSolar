"use client";

import { useEffect, useState } from "react";
import { api, type Client } from "@/lib/api";

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [adding, setAdding] = useState(false);

  async function reload() {
    setClients(await api.listClients());
  }

  useEffect(() => {
    reload();
  }, []);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await api.createClient({
      name: String(fd.get("name")),
      phone: String(fd.get("phone") || "") || null,
      email: String(fd.get("email") || "") || null,
      address: String(fd.get("address") || "") || null,
    });
    (e.currentTarget as HTMLFormElement).reset();
    setAdding(false);
    await reload();
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-semibold">Clients</h2>
          <p className="text-[var(--muted)] text-sm">People you quote and deliver for.</p>
        </div>
        <button
          onClick={() => setAdding(!adding)}
          className="bg-[var(--brand)] text-black font-medium px-4 py-2 rounded-lg hover:bg-[var(--brand-dark)] hover:text-white"
        >
          {adding ? "Cancel" : "+ New client"}
        </button>
      </div>

      {adding && (
        <form onSubmit={add} className="card p-4 grid grid-cols-1 md:grid-cols-2 gap-2">
          <input name="name" placeholder="Name" required />
          <input name="phone" placeholder="Phone" />
          <input name="email" type="email" placeholder="Email" />
          <input name="address" placeholder="Address" />
          <button className="md:col-span-2 bg-[var(--brand)] text-black font-medium py-2 rounded-lg">
            Save client
          </button>
        </form>
      )}

      <div className="card divide-y divide-[var(--border)]">
        {clients.length === 0 && (
          <div className="p-6 text-center text-[var(--muted)] text-sm">No clients yet.</div>
        )}
        {clients.map((c) => (
          <div key={c.id} className="p-4 flex justify-between items-center">
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-xs text-[var(--muted)]">
                {c.phone || "—"} · {c.address || "no address"}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
