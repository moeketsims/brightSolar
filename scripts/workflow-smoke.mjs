const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8001";
const EMAIL = process.env.SMOKE_EMAIL || "owner@brightsolarpower.co.za";
const PASSWORD = process.env.SMOKE_PASSWORD || "owner123";
const KEEP_DATA = process.env.WORKFLOW_KEEP_DATA === "1";

const state = {
  token: "",
  clientId: null,
  projectId: null,
  invoiceId: null,
  expenseId: null,
};

function url(path) {
  return new URL(path, API_URL).toString();
}

async function request(label, path, options = {}) {
  const headers = {
    ...(state.token ? { Authorization: `Bearer ${state.token}`, Cookie: `bsp_token=${state.token}` } : {}),
    ...(options.headers || {}),
  };
  const res = await fetch(url(path), { ...options, headers });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`${label} failed: ${res.status} ${res.statusText}\n${text.slice(0, 500)}`);
  }
  const contentType = res.headers.get("content-type") || "";
  if (!text) return { contentType, status: res.status };
  if (contentType.includes("application/json")) return JSON.parse(text);
  return { text, contentType, status: res.status };
}

async function json(label, path, body, method = "POST") {
  return request(label, path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function cleanup() {
  if (KEEP_DATA) {
    console.log("Keeping workflow test data because WORKFLOW_KEEP_DATA=1");
    return;
  }

  const steps = [
    async () => {
      if (state.invoiceId) await json("Cancel invoice cleanup", `/invoices/${state.invoiceId}`, { status: "cancelled" }, "PATCH");
    },
    async () => {
      if (state.invoiceId) await request("Delete invoice cleanup", `/invoices/${state.invoiceId}`, { method: "DELETE" });
    },
    async () => {
      if (state.expenseId) await request("Delete expense cleanup", `/expenses/${state.expenseId}`, { method: "DELETE" });
    },
    async () => {
      if (state.projectId) await request("Delete project cleanup", `/projects/${state.projectId}`, { method: "DELETE" });
    },
    async () => {
      if (state.clientId) await request("Delete client cleanup", `/clients/${state.clientId}`, { method: "DELETE" });
    },
  ];

  for (const step of steps) {
    try {
      await step();
    } catch (error) {
      console.warn(`Cleanup warning: ${error instanceof Error ? error.message : error}`);
    }
  }
}

async function main() {
  const runId = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const prefix = `SMOKE ${runId}`;

  try {
    const login = await request("Login", "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
    });
    state.token = login.access_token;
    if (!state.token) throw new Error("Login did not return an access token");

    const [vehicles, technicians] = await Promise.all([
      request("List vehicles", "/vehicles"),
      request("List technicians", "/technicians"),
    ]);
    const vehicle = vehicles.find((v) => v.active) || vehicles[0];
    const technician = technicians.find((t) => t.active) || technicians[0];
    if (!vehicle) throw new Error("Workflow test needs at least one vehicle");
    if (!technician) throw new Error("Workflow test needs at least one technician");

    const client = await json("Create client", "/clients", {
      name: `${prefix} Client`,
      phone: "+27 10 000 0000",
      email: `smoke-${runId}@brightsolarpower.co.za`,
      address: "1 Smoke Test Road, Johannesburg",
      notes: "Created by workflow smoke test; safe to delete.",
    });
    state.clientId = client.id;

    const project = await json("Create project", "/projects", {
      client_id: state.clientId,
      title: `${prefix} Quote-to-cash test`,
      service_type: "solar_install",
      site_address: "1 Smoke Test Road, Johannesburg",
      description: "Automated workflow smoke test project.",
      one_way_distance_km: 12,
      return_trips: 1,
      vehicle_id: vehicle.id,
      estimated_hours_on_site: 8,
      estimated_travel_hours: 1,
      overnight_nights: 0,
      people_on_site: 2,
      contingency_pct: 10,
      margin_pct: 20,
      materials: [
        { name: "Smoke test inverter", qty: 1, unit_cost: 5000 },
        { name: "Smoke test mounting kit", qty: 1, unit_cost: 1200 },
      ],
      tech_assignments: [
        { technician_id: technician.id, hours: 8, days: 0 },
      ],
      initial_activities: [
        { title: "Smoke test site survey", estimated_hours: 2, position: 0 },
        { title: "Smoke test install", estimated_hours: 6, position: 1 },
      ],
    });
    state.projectId = project.id;
    if (!Number(project.quoted?.total_inc_vat || project.quoted_total_inc_vat || 0)) {
      throw new Error("Created project did not compute a quoted total");
    }

    const quotePdf = await request("Render quote PDF", `/projects/${state.projectId}/quote.pdf`);
    if (!quotePdf.contentType.includes("application/pdf")) {
      throw new Error(`Quote PDF returned ${quotePdf.contentType}`);
    }

    const accepted = await json("Accept quote", `/projects/${state.projectId}/accept`, {
      accepted_by_name: "Workflow Smoke",
    });
    if (accepted.status !== "accepted") {
      throw new Error(`Expected accepted project, got ${accepted.status}`);
    }

    const invoice = await json("Create deposit invoice", `/projects/${state.projectId}/invoices`, {
      type: "deposit",
      description: "Workflow smoke deposit invoice",
      notes: "Generated by workflow smoke test.",
    });
    state.invoiceId = invoice.id;
    if (!Number(invoice.total_inc_vat)) throw new Error("Invoice did not compute a total");

    const invoicePdf = await request("Render invoice PDF", `/invoices/${state.invoiceId}/pdf`);
    if (!invoicePdf.contentType.includes("application/pdf")) {
      throw new Error(`Invoice PDF returned ${invoicePdf.contentType}`);
    }

    const sentInvoice = await json("Mark invoice sent", `/invoices/${state.invoiceId}`, { status: "sent" }, "PATCH");
    if (sentInvoice.status !== "sent") throw new Error(`Expected sent invoice, got ${sentInvoice.status}`);

    const payment = await json("Record invoice payment", `/invoices/${state.invoiceId}/payments`, {
      amount: invoice.total_inc_vat,
      method: "eft",
      reference: `${prefix}-PAY`,
      note: "Workflow smoke payment.",
    });
    if (!payment.id) throw new Error("Payment did not return an id");

    const fd = new FormData();
    fd.append("project_id", String(state.projectId));
    fd.append("category", "materials");
    fd.append("amount", "123.45");
    fd.append("description", "Workflow smoke material expense");
    fd.append("technician_id", String(technician.id));
    fd.append("idempotency_key", `${prefix}-expense`);
    const expense = await request("Create expense", "/expenses", { method: "POST", body: fd });
    state.expenseId = expense.id;

    const detail = await request("Reload project detail", `/projects/${state.projectId}`);
    if (!detail.expenses.some((item) => item.id === state.expenseId)) {
      throw new Error("Project detail did not include created expense");
    }
    if (!detail.events.some((event) => String(event.summary || "").includes("Invoice"))) {
      throw new Error("Project event feed did not include invoice activity");
    }

    const dashboard = await request("Dashboard summary", "/projects/dashboard/summary");
    if (!dashboard.cards.some((card) => card.id === state.projectId)) {
      throw new Error("Dashboard did not include active workflow project");
    }

    console.log("Workflow passed:");
    console.log(`- client ${state.clientId}`);
    console.log(`- project ${state.projectId}`);
    console.log(`- quote PDF rendered`);
    console.log(`- invoice ${state.invoiceId} rendered, sent, and paid`);
    console.log(`- expense ${state.expenseId} logged`);
    console.log(`- dashboard and project detail reflected the workflow`);
  } finally {
    await cleanup();
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
