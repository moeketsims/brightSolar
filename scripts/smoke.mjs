const FRONTEND_URL = process.env.FRONTEND_URL || "http://localhost:3000";
const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8001";
const EMAIL = process.env.SMOKE_EMAIL || "owner@brightsolarpower.co.za";
const PASSWORD = process.env.SMOKE_PASSWORD || "owner123";

const apiEndpoints = [
  "/auth/me",
  "/settings",
  "/clients",
  "/technicians",
  "/vehicles",
  "/projects/dashboard/summary",
  "/projects",
  "/projects/4",
  "/projects/4/activities",
  "/projects/4/reconciliation",
  "/templates",
  "/invoices",
  "/trips",
  "/today",
  "/exports/invoices.csv",
  "/exports/expenses.csv",
  "/trips/export.csv",
];

const frontendRoutes = [
  "/login",
  "/",
  "/today",
  "/projects",
  "/projects/new",
  "/projects/4",
  "/projects/4/edit",
  "/invoices",
  "/trips",
  "/log",
  "/clients",
  "/settings",
];

function absolute(base, path) {
  return new URL(path, base).toString();
}

async function request(label, url, options = {}) {
  const res = await fetch(url, { redirect: "manual", ...options });
  const body = await res.text();
  if (!res.ok) {
    throw new Error(`${label} failed: ${res.status} ${res.statusText}\n${body.slice(0, 300)}`);
  }
  return { res, body };
}

function assertNoBrokenText(label, body) {
  const markers = ["Failed to fetch", "Not authenticated", "Invalid or expired token", "Application error"];
  const hit = markers.find((marker) => body.includes(marker));
  if (hit) {
    throw new Error(`${label} contains broken-state text: ${hit}`);
  }
}

async function main() {
  const login = await request("API login", absolute(API_URL, "/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  });
  const token = JSON.parse(login.body).access_token;
  if (!token) throw new Error("API login did not return access_token");

  const authHeaders = {
    Authorization: `Bearer ${token}`,
    Cookie: `bsp_token=${token}`,
  };

  const checks = [];

  for (const endpoint of apiEndpoints) {
    const { res } = await request(`API ${endpoint}`, absolute(API_URL, endpoint), {
      headers: authHeaders,
    });
    checks.push(`API ${endpoint} -> ${res.status}`);
  }

  for (const route of frontendRoutes) {
    const { res, body } = await request(`Frontend ${route}`, absolute(FRONTEND_URL, route), {
      headers: authHeaders,
    });
    assertNoBrokenText(`Frontend ${route}`, body);
    checks.push(`Frontend ${route} -> ${res.status}`);
  }

  const loginPage = await request("Login page assets", absolute(FRONTEND_URL, "/login"));
  const cssMatch = loginPage.body.match(/\/_next\/static\/css\/[^"']+\.css[^"']*/);
  if (!cssMatch) throw new Error("Login page did not include a Next CSS asset");

  const cssUrl = cssMatch[0].replace(/&amp;/g, "&");
  const css = await request("Compiled CSS", absolute(FRONTEND_URL, cssUrl));
  const cssType = css.res.headers.get("content-type") || "";
  if (!cssType.includes("text/css")) throw new Error(`Compiled CSS returned ${cssType}`);

  const logo = await request("Logo image", absolute(FRONTEND_URL, "/brand/logo.png"));
  const logoType = logo.res.headers.get("content-type") || "";
  if (!logoType.includes("image/png")) throw new Error(`Logo returned ${logoType}`);

  checks.push(`CSS ${cssUrl} -> ${css.res.status}`);
  checks.push(`Logo /brand/logo.png -> ${logo.res.status}`);

  console.log(`Smoke passed against ${FRONTEND_URL} and ${API_URL}`);
  for (const check of checks) console.log(`- ${check}`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
