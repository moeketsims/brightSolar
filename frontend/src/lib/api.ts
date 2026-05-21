const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export type ProjectStatus =
  | "quoting"
  | "quoted"
  | "accepted"
  | "in_progress"
  | "completed"
  | "invoiced"
  | "paid"
  | "lost";

export type ServiceType =
  | "solar_install"
  | "backup_install"
  | "inverter"
  | "battery"
  | "maintenance"
  | "repair"
  | "inspection"
  | "other";

export type ExpenseCategory =
  | "diesel"
  | "lodging"
  | "meals"
  | "tolls"
  | "materials"
  | "labour"
  | "equipment_hire"
  | "other";

export type TechRateType = "hourly" | "daily";

export interface Settings {
  id: number;
  diesel_price_per_litre: string;
  default_lodging_per_night: string;
  default_per_diem: string;
  default_contingency_pct: string;
  default_margin_pct: string;
  vat_pct: string;
  business_name: string;
  base_address: string | null;
  base_latitude: number | null;
  base_longitude: number | null;
  business_phone: string | null;
  business_email: string | null;
  business_website: string | null;
  business_vat_number: string | null;
  business_reg_number: string | null;
  bank_name: string | null;
  bank_account_name: string | null;
  bank_account_number: string | null;
  bank_branch_code: string | null;
  quote_validity_days: number;
  deposit_pct_default: string;
  quote_terms: string | null;
}

export interface Technician {
  id: number;
  name: string;
  rate_type: TechRateType;
  hourly_rate: string;
  daily_rate: string;
  phone: string | null;
  active: boolean;
}

export interface Vehicle {
  id: number;
  name: string;
  registration: string | null;
  fuel_consumption_l_per_100km: string;
  running_cost_per_km: string;
  active: boolean;
}

export interface Client {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  notes: string | null;
  created_at: string;
}

export interface MaterialLine {
  name: string;
  qty: string | number;
  unit_cost: string | number;
}

export interface TechAssignment {
  technician_id: number;
  hours?: string | number;
  days?: string | number;
}

export interface CostLine {
  key: string;
  label: string;
  detail: string;
  amount: number;
}

export interface CostBreakdown {
  lines: CostLine[];
  subtotal: number;
  contingency: number;
  margin: number;
  total_ex_vat: number;
  vat: number;
  total_inc_vat: number;
}

export type ActivityStatus =
  | "pending"
  | "scheduled"
  | "in_progress"
  | "blocked"
  | "done"
  | "skipped";

export interface TimeEntry {
  id: number;
  activity_id: number;
  technician_id: number;
  technician_name?: string | null;
  started_at: string;
  ended_at: string | null;
  hours: string | null;
  note: string | null;
}

export interface Activity {
  id: number;
  project_id: number;
  title: string;
  description: string | null;
  status: ActivityStatus;
  position: number;
  estimated_hours: string;
  scheduled_date: string | null;
  due_date: string | null;
  blocker_reason: string | null;
  notes: string | null;
  assigned_tech_ids: number[];
  started_at: string | null;
  completed_at: string | null;
  actual_hours: string;
  time_entries: TimeEntry[];
  created_at: string;
  updated_at: string;
}

export interface ActivityCreate {
  title: string;
  description?: string | null;
  status?: ActivityStatus;
  estimated_hours?: number | string;
  scheduled_date?: string | null;
  due_date?: string | null;
  blocker_reason?: string | null;
  notes?: string | null;
  assigned_tech_ids?: number[];
}

export interface ActivityUpdate {
  title?: string;
  description?: string | null;
  status?: ActivityStatus;
  estimated_hours?: number | string;
  scheduled_date?: string | null;
  due_date?: string | null;
  blocker_reason?: string | null;
  notes?: string | null;
  assigned_tech_ids?: number[];
  position?: number;
}

export interface TodayActivity {
  activity: Activity;
  project_id: number;
  project_title: string;
  client_name: string;
}

export interface TodayTechColumn {
  technician_id: number | null;
  technician_name: string;
  scheduled_hours: string;
  activities: TodayActivity[];
  overload: boolean;
}

export interface TodayBoard {
  date: string;
  columns: TodayTechColumn[];
  total_activities: number;
}

export interface ProjectInputs {
  client_id: number;
  title: string;
  service_type: ServiceType;
  site_address?: string | null;
  description?: string | null;
  one_way_distance_km: string | number;
  return_trips: number;
  vehicle_id: number | null;
  estimated_hours_on_site: string | number;
  estimated_travel_hours: string | number;
  overnight_nights: number;
  people_on_site: number;
  contingency_pct?: string | number | null;
  margin_pct?: string | number | null;
  materials: MaterialLine[];
  tech_assignments: TechAssignment[];
  initial_activities?: TemplateActivity[];
  from_template_id?: number | null;
}

export interface TemplateActivity {
  title: string;
  description?: string | null;
  estimated_hours: string | number;
  position: number;
}

export interface ServiceTemplate {
  id: number;
  name: string;
  service_type: ServiceType;
  description: string | null;
  default_people_on_site: number;
  default_estimated_hours_on_site: string;
  default_contingency_pct: string;
  default_margin_pct: string;
  materials: MaterialLine[];
  activities: TemplateActivity[];
  created_at: string;
  updated_at: string;
}

export interface Expense {
  id: number;
  project_id: number;
  category: ExpenseCategory;
  amount: string;
  description: string | null;
  receipt_path: string | null;
  technician_id: number | null;
  latitude: number | null;
  longitude: number | null;
  incurred_at: string;
  created_at: string;
}

export interface ProjectSummary {
  id: number;
  client_id: number;
  client_name: string;
  title: string;
  service_type: ServiceType;
  status: ProjectStatus;
  site_address: string | null;
  quoted_total_ex_vat: string;
  quoted_total_inc_vat: string;
  actual_total: string;
  margin_ex_vat: string;
  margin_pct_realised: number;
  created_at: string;
}

export type ProjectEventKind =
  | "created"
  | "updated"
  | "status_changed"
  | "note"
  | "scope_changed"
  | "tech_added"
  | "tech_removed";

export interface ProjectEvent {
  id: number;
  project_id: number;
  kind: ProjectEventKind;
  summary: string;
  details: string | null;
  note: string | null;
  quote_before: string | null;
  quote_after: string | null;
  created_at: string;
}

export interface ProjectDetail {
  id: number;
  client: Client;
  title: string;
  service_type: ServiceType;
  status: ProjectStatus;
  site_address: string | null;
  description: string | null;
  quote_number: string | null;
  accepted_at: string | null;
  accepted_by_name: string | null;
  one_way_distance_km: string;
  return_trips: number;
  vehicle: Vehicle | null;
  estimated_hours_on_site: string;
  estimated_travel_hours: string;
  overnight_nights: number;
  people_on_site: number;
  contingency_pct: string;
  margin_pct: string;
  vat_pct: string;
  diesel_price_snapshot: string;
  lodging_rate_snapshot: string;
  per_diem_snapshot: string;
  materials: MaterialLine[];
  tech_assignments: TechAssignment[];
  activities: Activity[];
  quoted: CostBreakdown;
  actuals: { total: string; by_category: Record<string, string> };
  expenses: Expense[];
  events: ProjectEvent[];
  created_at: string;
  updated_at: string;
}

export interface ReconciliationLine {
  key: string;
  label: string;
  quoted: string;
  actual: string;
  delta: string;
  pct_of_quoted: number;
}

export interface ActivityAccuracy {
  activity_id: number;
  title: string;
  estimated_hours: string;
  actual_hours: string;
  delta_hours: string;
  status: string;
}

export interface LearningSuggestion {
  id: string;
  summary: string;
  field: string;
  target: string;
  suggested_value: string;
  current_value: string;
}

export interface Reconciliation {
  project_id: number;
  ready: boolean;
  quoted_total_ex_vat: string;
  actual_total: string;
  margin_quoted: string;
  margin_realised: string;
  margin_delta: string;
  total_hours_estimated: string;
  total_hours_actual: string;
  lines: ReconciliationLine[];
  activity_accuracy: ActivityAccuracy[];
  suggestions: LearningSuggestion[];
}

export interface ApplySuggestionIn {
  suggestion_id: string;
  field: string;
  target: string;
  value: string | number;
}

export interface Trip {
  id: number;
  vehicle_id: number;
  project_id: number | null;
  trip_date: string;
  from_location: string;
  to_location: string;
  purpose: string;
  odo_start: number | null;
  odo_end: number | null;
  business_km: string;
  technician_id: number | null;
  notes: string | null;
  vehicle_name?: string | null;
  project_title?: string | null;
}

export type UserRole = "owner" | "foreman" | "tech" | "accountant";

export interface CurrentUser {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  active: boolean;
  technician_id: number | null;
}

export type InvoiceType = "deposit" | "progress" | "final" | "retention";
export type InvoiceStatus = "draft" | "sent" | "paid" | "cancelled";

export interface Payment {
  id: number;
  invoice_id: number;
  received_at: string;
  amount: string;
  method: string;
  reference: string | null;
  note: string | null;
  created_at: string;
}

export interface Invoice {
  id: number;
  project_id: number;
  invoice_number: string;
  type: InvoiceType;
  status: InvoiceStatus;
  issued_at: string;
  due_at: string;
  subtotal_ex_vat: string;
  vat: string;
  total_inc_vat: string;
  retention_pct: string;
  retention_amount: string;
  description: string | null;
  notes: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
  paid_total: string;
  outstanding: string;
  is_overdue: boolean;
  days_overdue: number;
  payments: Payment[];
}

export interface InvoiceWithProject extends Invoice {
  project_title: string;
  client_name: string;
}

export interface AgedDebtors {
  bucket_0_30: string;
  bucket_31_60: string;
  bucket_61_90: string;
  bucket_90_plus: string;
  total_outstanding: string;
  overdue_count: number;
}

export interface DashboardProjectCard {
  id: number;
  client_name: string;
  title: string;
  status: ProjectStatus;
  quoted_inc_vat: string;
  quoted_ex_vat: string;
  actual_total: string;
  burn_ratio: number;
  status_colour: "green" | "amber" | "red";
}

export interface DashboardOut {
  active_projects: number;
  quoted_pipeline: string;
  expenses_this_month: string;
  projects_over_budget: number;
  activities_in_progress: number;
  activities_overdue: number;
  activities_blocked: number;
  debtors: AgedDebtors;
  cards: DashboardProjectCard[];
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    credentials: "include",
    cache: "no-store",
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
    window.location.href = "/login";
    throw new Error("Not authenticated");
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  apiBase: API,

  settings: () => json<Settings>("/settings"),
  updateSettings: (body: Partial<Settings>) =>
    json<Settings>("/settings", { method: "PATCH", body: JSON.stringify(body) }),

  listTechnicians: () => json<Technician[]>("/technicians"),
  createTechnician: (body: Partial<Technician>) =>
    json<Technician>("/technicians", { method: "POST", body: JSON.stringify(body) }),

  listVehicles: () => json<Vehicle[]>("/vehicles"),
  createVehicle: (body: Partial<Vehicle>) =>
    json<Vehicle>("/vehicles", { method: "POST", body: JSON.stringify(body) }),

  listClients: () => json<Client[]>("/clients"),
  createClient: (body: Partial<Client>) =>
    json<Client>("/clients", { method: "POST", body: JSON.stringify(body) }),

  dashboard: () => json<DashboardOut>("/projects/dashboard/summary"),
  listProjects: () => json<ProjectSummary[]>("/projects"),
  getProject: (id: number) => json<ProjectDetail>(`/projects/${id}`),
  createProject: (body: ProjectInputs) =>
    json<ProjectDetail>("/projects", { method: "POST", body: JSON.stringify(body) }),
  updateProject: (id: number, body: Partial<ProjectInputs> & { status?: ProjectStatus }) =>
    json<ProjectDetail>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  previewProject: (body: ProjectInputs) =>
    json<CostBreakdown>("/projects/preview", { method: "POST", body: JSON.stringify(body) }),
  addNote: (projectId: number, note: string) =>
    json<ProjectEvent>(`/projects/${projectId}/notes`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),

  listActivities: (projectId: number) =>
    json<Activity[]>(`/projects/${projectId}/activities`),
  createActivity: (projectId: number, body: ActivityCreate) =>
    json<Activity>(`/projects/${projectId}/activities`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateActivity: (activityId: number, body: ActivityUpdate) =>
    json<Activity>(`/activities/${activityId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteActivity: (activityId: number) =>
    json<void>(`/activities/${activityId}`, { method: "DELETE" }),
  startActivity: (activityId: number, technician_id: number, note?: string) =>
    json<Activity>(`/activities/${activityId}/start`, {
      method: "POST",
      body: JSON.stringify({ technician_id, note }),
    }),
  stopActivity: (activityId: number, technician_id: number, note?: string) =>
    json<Activity>(`/activities/${activityId}/stop`, {
      method: "POST",
      body: JSON.stringify({ technician_id, note }),
    }),
  completeActivity: (activityId: number) =>
    json<Activity>(`/activities/${activityId}/complete`, { method: "POST" }),
  today: (date?: string) =>
    json<TodayBoard>(`/today${date ? `?date=${date}` : ""}`),

  reconciliation: (projectId: number) =>
    json<Reconciliation>(`/projects/${projectId}/reconciliation`),
  applySuggestion: (projectId: number, body: ApplySuggestionIn) =>
    json<{ applied: boolean }>(`/projects/${projectId}/reconciliation/apply`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listTemplates: () => json<ServiceTemplate[]>("/templates"),
  getTemplate: (id: number) => json<ServiceTemplate>(`/templates/${id}`),
  createTemplate: (body: Partial<ServiceTemplate>) =>
    json<ServiceTemplate>("/templates", { method: "POST", body: JSON.stringify(body) }),
  updateTemplate: (id: number, body: Partial<ServiceTemplate>) =>
    json<ServiceTemplate>(`/templates/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTemplate: (id: number) =>
    json<void>(`/templates/${id}`, { method: "DELETE" }),
  saveTemplateFromProject: (projectId: number, name: string) =>
    json<ServiceTemplate>(
      `/templates/from-project/${projectId}?name=${encodeURIComponent(name)}`,
      { method: "POST" }
    ),

  quotePdfUrl: (projectId: number) => `${API}/projects/${projectId}/quote.pdf`,
  acceptQuote: (projectId: number, accepted_by_name: string) =>
    json<ProjectDetail>(`/projects/${projectId}/accept`, {
      method: "POST",
      body: JSON.stringify({ accepted_by_name }),
    }),

  listProjectInvoices: (projectId: number) =>
    json<Invoice[]>(`/projects/${projectId}/invoices`),
  listAllInvoices: (status?: InvoiceStatus) =>
    json<InvoiceWithProject[]>(`/invoices${status ? `?status=${status}` : ""}`),
  getInvoice: (id: number) => json<Invoice>(`/invoices/${id}`),
  createInvoice: (
    projectId: number,
    body: {
      type: InvoiceType;
      subtotal_ex_vat?: number | string;
      due_at?: string;
      retention_pct?: number | string;
      description?: string;
      notes?: string;
    }
  ) =>
    json<Invoice>(`/projects/${projectId}/invoices`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateInvoice: (id: number, body: Partial<Invoice>) =>
    json<Invoice>(`/invoices/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteInvoice: (id: number) => json<void>(`/invoices/${id}`, { method: "DELETE" }),
  recordPayment: (
    invoiceId: number,
    body: { amount: number | string; received_at?: string; method?: string; reference?: string; note?: string }
  ) =>
    json<Payment>(`/invoices/${invoiceId}/payments`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deletePayment: (invoiceId: number, paymentId: number) =>
    json<void>(`/invoices/${invoiceId}/payments/${paymentId}`, { method: "DELETE" }),
  invoicePdfUrl: (invoiceId: number) => `${API}/invoices/${invoiceId}/pdf`,

  listTrips: (params: { vehicle_id?: number; from_date?: string; to_date?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.vehicle_id) q.append("vehicle_id", String(params.vehicle_id));
    if (params.from_date) q.append("from_date", params.from_date);
    if (params.to_date) q.append("to_date", params.to_date);
    const s = q.toString();
    return json<Trip[]>(`/trips${s ? `?${s}` : ""}`);
  },
  createTrip: (body: Partial<Trip>) =>
    json<Trip>("/trips", { method: "POST", body: JSON.stringify(body) }),
  updateTrip: (id: number, body: Partial<Trip>) =>
    json<Trip>(`/trips/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteTrip: (id: number) => json<void>(`/trips/${id}`, { method: "DELETE" }),
  tripsExportCsvUrl: (params: { vehicle_id?: number; from_date?: string; to_date?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.vehicle_id) q.append("vehicle_id", String(params.vehicle_id));
    if (params.from_date) q.append("from_date", params.from_date);
    if (params.to_date) q.append("to_date", params.to_date);
    const s = q.toString();
    return `${API}/trips/export.csv${s ? `?${s}` : ""}`;
  },

  async ocrReceipt(file: File | Blob): Promise<{ amount: string | null }> {
    const fd = new FormData();
    fd.append("receipt", file);
    const res = await fetch(`${API}/expenses/ocr`, { method: "POST", body: fd, credentials: "include" });
    if (!res.ok) return { amount: null };
    return res.json();
  },

  // Auth
  login: (email: string, password: string) =>
    json<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => json<void>("/auth/logout", { method: "POST" }),
  me: () => json<CurrentUser>("/auth/me"),
  listUsers: () => json<CurrentUser[]>("/auth/users"),
  createUser: (body: { email: string; name: string; password: string; role: UserRole; technician_id?: number | null }) =>
    json<CurrentUser>("/auth/users", { method: "POST", body: JSON.stringify(body) }),
  updateUser: (id: number, body: { name?: string; role?: UserRole; active?: boolean; password?: string; technician_id?: number | null }) =>
    json<CurrentUser>(`/auth/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteUser: (id: number) => json<void>(`/auth/users/${id}`, { method: "DELETE" }),

  async uploadExpense(opts: {
    project_id: number;
    category: ExpenseCategory;
    amount: number | string;
    description?: string;
    technician_id?: number | null;
    latitude?: number | null;
    longitude?: number | null;
    file?: File | Blob | null;
    idempotency_key?: string;
  }): Promise<Expense> {
    const fd = new FormData();
    fd.append("project_id", String(opts.project_id));
    fd.append("category", opts.category);
    fd.append("amount", String(opts.amount));
    if (opts.idempotency_key) fd.append("idempotency_key", opts.idempotency_key);
    if (opts.description) fd.append("description", opts.description);
    if (opts.technician_id != null) fd.append("technician_id", String(opts.technician_id));
    if (opts.latitude != null) fd.append("latitude", String(opts.latitude));
    if (opts.longitude != null) fd.append("longitude", String(opts.longitude));
    if (opts.file) fd.append("receipt", opts.file);
    const res = await fetch(`${API}/expenses`, {
      method: "POST",
      body: fd,
      credentials: "include",
    });
    if (res.status === 401 && typeof window !== "undefined") {
      window.location.href = "/login";
      throw new Error("Not authenticated");
    }
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  },

  deleteExpense: (id: number) => json<void>(`/expenses/${id}`, { method: "DELETE" }),
};

export function formatZAR(v: string | number | null | undefined): string {
  const n = typeof v === "string" ? parseFloat(v) : v ?? 0;
  return new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR", maximumFractionDigits: 0 }).format(n || 0);
}

export function formatZARPrecise(v: string | number | null | undefined): string {
  const n = typeof v === "string" ? parseFloat(v) : v ?? 0;
  return new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR" }).format(n || 0);
}

export function absoluteUrl(path: string | null): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${API}${path}`;
}
