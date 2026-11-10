"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Empty, PageHeader, toneForStatus } from "@/components/ui";
import { api } from "@/lib/api";
import { label, scoreText } from "@/lib/format";

export default function AssessmentsPage() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api.get("/assessments").then(setItems); }, []);
  return (
    <div>
      <PageHeader title="Assessments" subtitle="Open an assessment to score criteria, review the result, or record a decision." />
      <div className="overflow-hidden rounded-xl border border-line bg-white">
        {items.map((item) => (
          <Link key={item.id} href={`/assessments/${item.id}`} className="flex items-center justify-between border-b border-line px-4 py-3 text-sm">
            <span>
              <span className="font-medium text-navy">{item.assessment_number}</span>
              <span className="ml-2">{item.opportunity_name}</span>
            </span>
            <span className="flex items-center gap-3">
              <Badge tone={toneForStatus(item.status)}>{label(item.status)}</Badge>
              <span>{scoreText(item.calculated_score)}</span>
              <span className="text-muted">{item.recommendation_name || `${item.completion_percentage}% complete`}</span>
            </span>
          </Link>
        ))}
        {!items.length ? <div className="p-6"><Empty title="No assessments" body="Start one from an opportunity workspace." /></div> : null}
      </div>
    </div>
  );
}
