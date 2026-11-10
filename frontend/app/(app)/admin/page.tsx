"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button, Card, PageHeader, fieldClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function AdminPage() {
  const { can } = useAuth();
  const [templates, setTemplates] = useState<any[]>([]);
  const [name, setName] = useState("");
  useEffect(() => { if (can("config.manage") || can("dashboard.view")) api.get("/assessment-templates").then(setTemplates); }, [can]);

  return (
    <div>
      <PageHeader title="Administration" subtitle="Methodology, people, red flags, and the audit log. Published templates cannot be edited in place." />
      <div className="mb-4 flex flex-wrap gap-2">
        {can("users.manage") ? <Link href="/admin/users"><Button variant="secondary">Users and roles</Button></Link> : null}
        {can("audit.view") ? <Link href="/admin/audit"><Button variant="secondary">Audit log</Button></Link> : null}
        {can("config.manage") ? <Link href="/admin/settings"><Button variant="secondary">Settings and red flags</Button></Link> : null}
      </div>
      {can("config.manage") ? (
        <Card>
          <h2 className="font-semibold text-navy">Assessment templates</h2>
          <div className="mt-3 space-y-2">
            {templates.map((template) => (
              <Link key={template.id} href={`/admin/templates/${template.id}`} className="block rounded-lg border border-line px-3 py-2 text-sm">
                <span className="font-medium">{template.name}</span>
                <span className="ml-2 text-muted">{template.status}</span>
              </Link>
            ))}
          </div>
          <form className="mt-4 flex gap-2" onSubmit={async (event) => {
            event.preventDefault();
            const created = await api.post("/assessment-templates", { name, description: "" });
            window.location.href = `/admin/templates/${created.id}`;
          }}>
            <input className={fieldClass} placeholder="New template name" value={name} onChange={(event) => setName(event.target.value)} required />
            <Button type="submit">Create</Button>
          </form>
        </Card>
      ) : null}
    </div>
  );
}
