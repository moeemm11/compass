"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Banner, Button, fieldClass } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const ACCOUNTS = [
  ["admin@diyar.local", "System Administrator"],
  ["bd@diyar.local", "Business Development"],
  ["evaluator@diyar.local", "Evaluator"],
  ["functional@diyar.local", "Functional Reviewer"],
  ["commercial@diyar.local", "Commercial Reviewer"],
  ["executive@diyar.local", "Executive Approver"],
  ["viewer@diyar.local", "Executive Viewer"],
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("executive@diyar.local");
  const [password, setPassword] = useState("Compass123!");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-navy p-12 text-white lg:flex">
        <div>
          <p className="text-sm tracking-[0.2em]">DIYAR COMPASS</p>
          <h1 className="mt-10 max-w-md text-4xl font-semibold leading-tight">Navigate opportunities. Make informed decisions.</h1>
          <p className="mt-4 max-w-md text-white/70">A single place to qualify an opportunity, explain the score, and record the management decision.</p>
        </div>
        <p className="text-sm text-white/50">Internal decision intelligence for Diyar.</p>
      </section>
      <section className="flex items-center justify-center px-6 py-12">
        <form onSubmit={onSubmit} className="w-full max-w-md space-y-4">
          <div>
            <h2 className="text-2xl font-semibold text-navy">Sign in</h2>
            <p className="mt-1 text-sm text-muted">Use your Diyar account. Demonstration password: Compass123!</p>
          </div>
          {error ? <Banner>{error}</Banner> : null}
          <label className="block space-y-1.5 text-sm">
            Email
            <input className={fieldClass} value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" />
          </label>
          <label className="block space-y-1.5 text-sm">
            Password
            <input className={fieldClass} type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
          </label>
          <Button type="submit" className="w-full" disabled={pending}>{pending ? "Signing in…" : "Sign in"}</Button>
          <div className="grid grid-cols-1 gap-2 pt-2 sm:grid-cols-2">
            {ACCOUNTS.map(([account, role]) => (
              <button key={account} type="button" className="rounded-md border border-line px-3 py-2 text-left text-xs hover:border-teal" onClick={() => setEmail(account)}>
                <span className="block font-medium text-ink">{role}</span>
                <span className="text-muted">{account}</span>
              </button>
            ))}
          </div>
        </form>
      </section>
    </div>
  );
}
