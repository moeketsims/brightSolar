"use client";

import { useEffect, useState } from "react";
import { flushQueue, installQueueFlusher, listQueued } from "@/lib/offline-queue";

export default function PwaInit() {
  const [online, setOnline] = useState(true);
  const [pending, setPending] = useState(0);
  const [lastFlush, setLastFlush] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if ("serviceWorker" in navigator) {
      if (process.env.NODE_ENV === "production") {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
      } else {
        navigator.serviceWorker.getRegistrations()
          .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
          .catch(() => {});
        if ("caches" in window) {
          caches.keys()
            .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
            .catch(() => {});
        }
      }
    }
    setOnline(navigator.onLine);
    const onOn = () => setOnline(true);
    const onOff = () => setOnline(false);
    window.addEventListener("online", onOn);
    window.addEventListener("offline", onOff);
    const stop = installQueueFlusher();

    const updatePending = async () => {
      const q = await listQueued().catch(() => []);
      setPending(q.length);
    };
    updatePending();
    const id = window.setInterval(updatePending, 5000);

    return () => {
      window.removeEventListener("online", onOn);
      window.removeEventListener("offline", onOff);
      stop();
      clearInterval(id);
    };
  }, []);

  async function manualFlush() {
    const { ok } = await flushQueue();
    if (ok > 0) setLastFlush(`Synced ${ok} pending item${ok > 1 ? "s" : ""}`);
    const q = await listQueued();
    setPending(q.length);
    setTimeout(() => setLastFlush(null), 3000);
  }

  if (online && pending === 0 && !lastFlush) return null;

  return (
    <div className="fixed bottom-4 right-4 z-40">
      {lastFlush && (
        <div className="chip bg-emerald-500/20 text-emerald-300 mb-2 block">{lastFlush}</div>
      )}
      {!online && (
        <div className="chip bg-amber-500/20 text-amber-300 mb-2 block">
          ⚠ Offline — receipts will queue locally
        </div>
      )}
      {pending > 0 && (
        <button
          onClick={manualFlush}
          className="chip bg-sky-500/20 text-sky-300 cursor-pointer hover:bg-sky-500/30"
          title="Try to sync queued receipts"
        >
          ⟳ {pending} pending {pending > 1 ? "items" : "item"} — sync now
        </button>
      )}
    </div>
  );
}
