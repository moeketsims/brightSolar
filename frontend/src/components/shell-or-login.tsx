"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import UserMenu from "./user-menu";

export default function ShellOrLogin({
  children,
  navItems,
}: {
  children: React.ReactNode;
  navItems: { href: string; label: string; icon: string; accent?: boolean }[];
}) {
  const pathname = usePathname();
  if (pathname === "/login") {
    return <>{children}</>;
  }
  return (
    <div className="min-h-screen flex flex-col md:flex-row">
      <aside className="md:w-64 md:min-h-screen md:border-r border-b md:border-b-0 border-[var(--border)] bg-[var(--surface)]/60 backdrop-blur">
        <div className="p-5 flex md:block items-center justify-between">
          <div className="flex items-center gap-3 md:block">
            <Image
              src="/brand/logo.png"
              alt="Bright Solar Power"
              width={180}
              height={48}
              className="h-10 md:h-12 w-auto md:mb-1"
              priority
            />
            <p className="text-[11px] text-[var(--muted)] tracking-wide md:mt-1">
              Operations
            </p>
          </div>
          <nav className="hidden md:flex flex-col gap-1 mt-6">
            {navItems.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`px-3 py-2 rounded-lg text-sm flex items-center gap-3 transition ${
                  n.accent
                    ? "bg-[var(--brand)] text-black font-medium hover:bg-[var(--brand-dark)] hover:text-white"
                    : "hover:bg-white/5"
                }`}
              >
                <span className="w-5 text-center opacity-70">{n.icon}</span>
                {n.label}
              </Link>
            ))}
          </nav>
          <nav className="md:hidden flex gap-1 overflow-x-auto hide-scrollbar">
            {navItems.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={`px-3 py-1.5 rounded text-xs whitespace-nowrap ${
                  n.accent ? "bg-[var(--brand)] text-black font-medium" : "bg-white/5 hover:bg-white/10"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <UserMenu />
        </div>
      </aside>
      <main className="flex-1 p-5 md:p-8 max-w-[1400px]">{children}</main>
    </div>
  );
}
