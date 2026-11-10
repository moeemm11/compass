"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button, Card, PageHeader, fieldClass } from "@/components/ui";
import { api } from "@/lib/api";

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [form, setForm] = useState({ full_name: "", email: "", password: "Compass123!", role_id: "" });
  const [error, setError] = useState("");

  function load() {
    api.get("/users").then(setUsers);
    api.get("/roles").then((rows) => {
      setRoles(rows);
      setForm((current) => ({ ...current, role_id: current.role_id || rows[0]?.id || "" }));
    });
  }
  useEffect(load, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/users", { full_name: form.full_name, email: form.email, password: form.password, role_ids: [form.role_id] });
      setForm({ ...form, full_name: "", email: "" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the user");
    }
  }

  return (
    <div>
      <PageHeader title="Users and roles" subtitle="Access is enforced on the server. Deactivate an account instead of deleting it." />
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card>
          {users.map((user) => (
            <div key={user.id} className="flex items-center justify-between border-b border-line py-3 text-sm">
              <div>
                <p className="font-medium">{user.full_name}</p>
                <p className="text-muted">{user.email} · {user.roles.join(", ")}</p>
              </div>
              <Button variant="secondary" onClick={() => api.put(`/users/${user.id}`, { is_active: !user.is_active }).then(load)}>{user.is_active ? "Deactivate" : "Activate"}</Button>
            </div>
          ))}
        </Card>
        <Card>
          <h2 className="font-semibold">Add user</h2>
          {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
          <form className="mt-3 space-y-3" onSubmit={create}>
            <input className={fieldClass} placeholder="Full name" required value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} />
            <input className={fieldClass} type="email" placeholder="Email" required value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            <input className={fieldClass} type="password" required value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
            <select className={fieldClass} value={form.role_id} onChange={(event) => setForm({ ...form, role_id: event.target.value })}>
              {roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}
            </select>
            <Button type="submit">Create user</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
