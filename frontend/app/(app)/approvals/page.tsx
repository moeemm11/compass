"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Empty, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { label, scoreText } from "@/lib/format";

export default function ApprovalsPage() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api.get("/approvals/pending").then(setItems); }, []);
  return (
    <div>
      <PageHeader title="Approval inbox" subtitle="Functional review, commercial review, then the executive decision. Each stage is recorded." />
      {items.length ? items.map((item) => (
        <Link key={item.assessment_id + item.stage} href={`/assessments/${item.assessment_id}`} className="mb-3 block rounded-xl border border-line bg-white p-4 shadow-card">
          <p className="font-medium text-navy">{item.opportunity_name}</p>
          <p className="text-sm text-muted">{item.reference_number} · {label(item.stage)} · score {scoreText(item.score)} · {item.recommendation || "Pending a complete score"}</p>
        </Link>
      )) : <Empty title="Inbox is clear" body="Assessments appear here when they reach your stage." />}
    </div>
  );
}
