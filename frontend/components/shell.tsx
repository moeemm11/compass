"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  Briefcase,
  ClipboardCheck,
  FileBarChart,
  Handshake,
  LayoutDashboard,
  LogOut,
  Menu,
  Scale,
  Settings,
  ShieldAlert,
  Users,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cx } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Executive Dashboard", icon: LayoutDashboard, show: (can: (code: string) => boolean) => can("dashboard.view") },
  { href: "/opportunities", label: "Opportunities", icon: Briefcase, show: (can: (code: string) => boolean) => can("opportunities.view_all") || can("opportunities.view_assigned") },
  { href: "/assessments", label: "Assessments", icon: ClipboardCheck, show: (can: (code: string) => boolean) => can("opportunities.view_all") || can("assessments.complete_assigned") || can("assessments.complete_any") },
  { href: "/approvals", label: "Approvals", icon: Scale, show: (can: (code: string) => boolean) => can("approvals.decide") || can("assessments.review") },
  { href: "/partners", label: "Partners", icon: Handshake, show: () => true },
  { href: "/commercial", label: "Commercial", icon: FileBarChart, show: (can: (code: string) => boolean) => can("dashboard.view") || can("commercial.edit") },
  { href: "/risks", label: "Risk Management", icon: ShieldAlert, show: (can: (code: string) => boolean) => can("dashboard.view") || can("opportunities.view_assigned") },
  { href: "/resources", label: "Resources", icon: Users, show: (can: (code: string) => boolean) => can("dashboard.view") || can("opportunities.view_assigned") },
  { href: "/reports", label: "Reports", icon: FileBarChart, show: (can: (code: string) => boolean) => can("reports.export") || can("dashboard.view") },
  { href: "/admin", label: "Administration", icon: Settings, show: (can: (code: string) => boolean) => can("config.manage") || can("users.manage") || can("audit.view") },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, ready, logout, can } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  if (!ready) return <div className="grid min-h-screen place-items-center text-sm text-muted">Loading COMPASS…</div>;
  if (!user) {
    if (typeof window !== "undefined") router.replace("/login");
    return null;
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside className={cx("fixed inset-y-0 left-0 z-30 w-[260px] bg-navy text-white lg:static", open ? "block" : "hidden lg:block")}>
        <div className="flex h-full flex-col">
          <div className="border-b border-white/10 px-5 py-5">
            <div className="flex items-center gap-3">
              <CompassMark />
              <div>
                <p className="text-sm font-semibold tracking-[0.16em]">DIYAR COMPASS</p>
                <p className="text-xs text-white/60">Decision intelligence</p>
              </div>
            </div>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4">
            {NAV.filter((item) => item.show(can)).map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} onClick={() => setOpen(false)} className={cx("flex items-center gap-3 rounded-md px-3 py-2 text-sm", active ? "bg-white/15 text-white" : "text-white/75 hover:bg-white/10 hover:text-white")}>
                  <Icon size={16} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="border-t border-white/10 p-4">
            <p className="text-sm font-medium">{user.full_name}</p>
            <p className="text-xs text-white/60">{user.roles[0]}</p>
            <button className="mt-3 flex items-center gap-2 text-sm text-white/75 hover:text-white" onClick={() => logout().then(() => router.push("/login"))}>
              <LogOut size={15} /> Sign out
            </button>
          </div>
        </div>
      </aside>
      <div className="min-w-0">
        <header className="flex items-center justify-between border-b border-line bg-white px-4 py-3 lg:px-8">
          <button className="rounded-md border border-line p-2 lg:hidden" onClick={() => setOpen((value) => !value)} aria-label="Open navigation">
            <Menu size={18} />
          </button>
          <p className="text-sm text-muted">Navigate opportunities. Make informed decisions.</p>
        </header>
        <main className="px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}

function CompassMark() {
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
      <circle cx="17" cy="17" r="15" fill="#14365C" stroke="#7DD3C7" strokeWidth="1.5" />
      <path d="M17 6 L20 17 L17 15 L14 17 Z" fill="#7DD3C7" />
      <path d="M17 28 L14 17 L17 19 L20 17 Z" fill="#F8FAFC" />
    </svg>
  );
}
