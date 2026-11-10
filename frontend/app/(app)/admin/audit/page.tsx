"use client";

import { useEffect, useState } from "react";
import { Card, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";

export default function AuditPage() {
  const [data, setData] = useState<any>({ items: [] });
  useEffect(() => { api.get("/audit-logs?page_size=50").then(setData); }, []);
  return (
    <div>
      <PageHeader title="Audit log" subtitle="Historical records are not editable from the application." />
      <Card>
        {data.items.map((item: any) => (
          <div key={item.id} className="border-b border-line py-3 text-sm">
            <p className="font-medium">{item.action}</p>
            <p className="text-muted">{item.actor} · {item.entity_type} · {new Date(item.created_at).toLocaleString()}</p>
          </div>
        ))}
      </Card>
    </div>
  );
}
