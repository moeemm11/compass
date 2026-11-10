"use client";

import { ReactNode } from "react";

export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export const fieldClass =
  "w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-teal focus:ring-2 focus:ring-teal/15";

export function Button({
  children,
  variant = "primary",
  type = "button",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-navy text-white hover:bg-navy-800",
    secondary: "border border-line bg-white text-ink hover:bg-canvas",
    ghost: "text-muted hover:bg-white hover:text-ink",
    danger: "bg-red-700 text-white hover:bg-red-800",
  }[variant];
  return (
    <button type={type} className={cx("inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50", styles, className)} {...props}>
      {children}
    </button>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-ink">{label}</span>
      {children}
      {hint ? <span className="block text-xs text-muted">{hint}</span> : null}
    </label>
  );
}

export function Card({ children, className, style }: { children: ReactNode; className?: string; style?: React.CSSProperties }) {
  return <section className={cx("rounded-xl border border-line bg-white p-5 shadow-card", className)} style={style}>{children}</section>;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "warn" | "bad" | "info" }) {
  const styles = {
    neutral: "bg-canvas text-ink",
    good: "bg-emerald-50 text-emerald-800",
    warn: "bg-amber-50 text-amber-800",
    bad: "bg-red-50 text-red-800",
    info: "bg-teal-soft text-teal",
  }[tone];
  return <span className={cx("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium", styles)}>{children}</span>;
}

export function toneForStatus(status?: string) {
  if (!status) return "neutral" as const;
  if (["approved", "won", "completed", "confirmed", "active"].includes(status)) return "good" as const;
  if (["rejected", "lost", "cancelled", "gap"].includes(status)) return "bad" as const;
  if (["on_hold", "conditionally_approved", "returned", "partial"].includes(status)) return "warn" as const;
  return "info" as const;
}

export function Banner({ children, tone = "bad" }: { children: ReactNode; tone?: "bad" | "info" }) {
  return <div className={cx("rounded-md px-3 py-2 text-sm", tone === "bad" ? "bg-red-50 text-red-800" : "bg-teal-soft text-teal")}>{children}</div>;
}

export function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center">
      <p className="font-medium text-ink">{title}</p>
      <p className="mt-1 text-sm text-muted">{body}</p>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-navy">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-3xl text-sm text-muted">{subtitle}</p> : null}
      </div>
      {actions}
    </div>
  );
}

export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-navy/40 p-4">
      <div className="mt-10 w-full max-w-2xl rounded-xl bg-white p-5 shadow-card">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-navy">{title}</h2>
          <button className="text-sm text-muted" onClick={onClose}>Close</button>
        </div>
        {children}
      </div>
    </div>
  );
}
