"use client";

import { useEffect, useState } from "react";
import { Card, Empty, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { label } from "@/lib/format";

export default function ResourcesPage() {
  const [data, setData] = useState<any>({ items: [], summary: null });
  useEffect(() => { api.get("/resources").then(setData); }, []);
  const summary = data.summary;
  return (
    <div>
      <PageHeader title="Resource feasibility" subtitle="This release records demand and gaps. Calendar capacity planning is a later release." />
      {summary ? <Card className="mb-4">Demand {summary.total_demand} · confirmed internal {summary.confirmed_internal} · external dependency {summary.external_dependency} · critical gaps {summary.critical_skill_gaps} · {summary.delivery_feasibility}</Card> : null}
      {data.items.length ? data.items.map((item: any) => (
        <div key={item.id} className="mb-2 rounded-lg border border-line bg-white px-4 py-3 text-sm">{item.quantity} × {item.role} · {label(item.resource_type)} · {label(item.availability_status)}{item.identified_gap ? " · gap" : ""}</div>
      )) : <Empty title="No resource plan" body="Add required roles from an opportunity." />}
    </div>
  );
}
