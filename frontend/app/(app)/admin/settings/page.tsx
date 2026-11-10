"use client";

import { useEffect, useState } from "react";
import { Button, Card, PageHeader, fieldClass } from "@/components/ui";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<any>(null);
  const [flags, setFlags] = useState<any[]>([]);
  useEffect(() => {
    api.get("/admin/settings").then(setSettings);
    api.get("/admin/red-flags").then(setFlags);
  }, []);
  return (
    <div className="space-y-4">
      <PageHeader title="Settings and red flags" subtitle="Red flags escalate an opportunity. They never change the calculated score. Administrative approval can be turned off without removing the administrator role." />
      {settings ? (
        <Card>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={settings.admin_can_approve === "true"} onChange={(event) => {
              const value = event.target.checked ? "true" : "false";
              api.put("/admin/settings/admin_can_approve", { value }).then(() => setSettings({ ...settings, admin_can_approve: value }));
            }} />
            System administrators may also record executive decisions
          </label>
          <div className="mt-3 flex items-center gap-2">
            <input className={fieldClass + " max-w-[120px]"} value={settings.session_minutes} onChange={(event) => setSettings({ ...settings, session_minutes: event.target.value })} />
            <Button variant="secondary" onClick={() => api.put("/admin/settings/session_minutes", { value: settings.session_minutes })}>Save session minutes</Button>
          </div>
        </Card>
      ) : null}
      <Card>
        <h2 className="font-semibold text-navy">Red flag rules</h2>
        {flags.map((flag) => (
          <div key={flag.id} className="mt-3 border-t border-line pt-3 text-sm">
            <label className="flex items-center gap-2 font-medium">
              <input type="checkbox" checked={flag.is_active} onChange={(event) => api.put(`/admin/red-flags/${flag.id}`, { is_active: event.target.checked }).then(() => api.get("/admin/red-flags").then(setFlags))} />
              {flag.name}
            </label>
            <p className="text-muted">{flag.description}</p>
            <input className={`${fieldClass} mt-2`} defaultValue={JSON.stringify(flag.parameters || {})} onBlur={(event) => {
              try { api.put(`/admin/red-flags/${flag.id}`, { parameters: JSON.parse(event.target.value || "{}") }); } catch { /* keep the previous parameters */ }
            }} />
          </div>
        ))}
      </Card>
    </div>
  );
}
