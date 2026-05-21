import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = [
  "/login",
  "/favicon.ico",
  "/brand",
  "/manifest.webmanifest",
  "/sw.js",
];

export function middleware(req: NextRequest) {
  const path = req.nextUrl.pathname;
  if (PUBLIC_PATHS.some((p) => path === p || path.startsWith(p + "/"))) {
    return NextResponse.next();
  }
  if (path.startsWith("/_next") || path.startsWith("/api")) {
    return NextResponse.next();
  }
  const token = req.cookies.get("bsp_token")?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|brand|manifest.webmanifest|sw.js).*)",
  ],
};
