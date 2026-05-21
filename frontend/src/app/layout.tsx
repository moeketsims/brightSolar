import type { Metadata, Viewport } from "next";
import "./globals.css";
import ShellOrLogin from "@/components/shell-or-login";
import PwaInit from "@/components/pwa-init";

export const metadata: Metadata = {
  title: "Bright Solar — Ops",
  description: "Project costing and expense tracking for Bright Solar Power",
  icons: {
    icon: "/brand/logo.png",
  },
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a0d12",
};

const navItems = [
  { href: "/", label: "Dashboard", icon: "◈" },
  { href: "/today", label: "Today", icon: "⏱" },
  { href: "/projects", label: "Projects", icon: "▣" },
  { href: "/projects/new", label: "New project", icon: "+", accent: true },
  { href: "/invoices", label: "Invoices", icon: "R" },
  { href: "/trips", label: "Trip log", icon: "🚐" },
  { href: "/log", label: "Log receipt", icon: "◉" },
  { href: "/clients", label: "Clients", icon: "◆" },
  { href: "/settings", label: "Settings", icon: "◎" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ShellOrLogin navItems={navItems}>{children}</ShellOrLogin>
        <PwaInit />
      </body>
    </html>
  );
}
