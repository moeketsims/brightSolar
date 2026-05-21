/**
 * Minimal IndexedDB queue for expense uploads when the tech is offline.
 * Flushes automatically on load and when the network comes back.
 */

const DB_NAME = "bsp-offline";
const STORE = "pending_expenses";
const VERSION = 1;

export interface PendingExpense {
  id?: number; // auto-assigned
  idempotency_key: string;
  project_id: number;
  category: string;
  amount: string;
  description?: string;
  technician_id?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  file_blob?: Blob | null;
  file_name?: string | null;
  queued_at: number;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function queueExpense(exp: Omit<PendingExpense, "id" | "queued_at">): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    store.add({ ...exp, queued_at: Date.now() });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function listQueued(): Promise<PendingExpense[]> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const store = tx.objectStore(STORE);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result as PendingExpense[]);
    req.onerror = () => reject(req.error);
  });
}

async function removeQueued(id: number): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function flushQueue(): Promise<{ ok: number; failed: number }> {
  const queued = await listQueued();
  let ok = 0;
  let failed = 0;
  for (const q of queued) {
    const fd = new FormData();
    fd.append("project_id", String(q.project_id));
    fd.append("category", q.category);
    fd.append("amount", q.amount);
    fd.append("idempotency_key", q.idempotency_key);
    if (q.description) fd.append("description", q.description);
    if (q.technician_id != null) fd.append("technician_id", String(q.technician_id));
    if (q.latitude != null) fd.append("latitude", String(q.latitude));
    if (q.longitude != null) fd.append("longitude", String(q.longitude));
    if (q.file_blob) fd.append("receipt", q.file_blob, q.file_name || "receipt.jpg");
    try {
      const res = await fetch(`${API}/expenses`, {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      if (res.ok) {
        if (q.id !== undefined) await removeQueued(q.id);
        ok++;
      } else if (res.status === 401) {
        // Not logged in — leave in queue
        failed++;
      } else {
        failed++;
      }
    } catch {
      failed++;
    }
  }
  return { ok, failed };
}

export function installQueueFlusher(): () => void {
  if (typeof window === "undefined") return () => {};
  const flush = () => {
    if (navigator.onLine) flushQueue().catch(() => {});
  };
  flush(); // try on install
  window.addEventListener("online", flush);
  const id = window.setInterval(flush, 60000); // retry every minute
  return () => {
    window.removeEventListener("online", flush);
    clearInterval(id);
  };
}

export function newIdempotencyKey(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
