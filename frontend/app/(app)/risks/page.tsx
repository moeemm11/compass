"use client";

import { useEffect, useState } from "react";
import { Card, Empty, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { label } from "@/lib/format";

export default function RisksPage() {
  const [risks, setRisks] = useState<any[]>([]);
  useEffect(() => { api.get("/risks").then(setRisks); }, []);
  return (
    <div>
      <PageHeader title="Risk management" subtitle="Inherent score is probability × impact. Residual score uses the same scale after mitigation." />
      {risks.length ? risks.map((risk) => (
        <Card key={risk.id} className="mb-3">
          <p className="font-medium">{risk.reference_number} · {risk.title}</p>
          <p className="text-sm text-muted">{risk.category} · inherent {risk.inherent_score} · residual {risk.residual_score ?? "—"} · {label(risk.status)}</p>
          <p className="mt-1 text-sm">{risk.mitigation_plan}</p>
        </Card>
      )) : <Empty title="No risks" body="Risks added to an opportunity appear in this register." />}
    </div>
  );
}
