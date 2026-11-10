"use client";

import { useEffect, useState } from "react";
import { Button, Card, PageHeader, fieldClass } from "@/components/ui";
import { api, downloadPdf } from "@/lib/api";
import { money, scoreText } from "@/lib/format";

export default function ReportsPage() {
  const [report, setReport] = useState<any>(null);
  const [assessments, setAssessments] = useState<any[]>([]);
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");
  const [comparison, setComparison] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.get("/reports/opportunities").then(setReport);
    api.get("/assessments").then(setAssessments);
  }, []);

  return (
    <div>
      <PageHeader title="Reports" subtitle="Portfolio totals and a comparison of assessments that share one template version. PDFs are generated on the server." />
      {report ? (
        <Card className="mb-4">
          <p className="text-sm">Opportunities {report.summary.total} · pipeline {money(report.summary.pipeline_value)} · average score {scoreText(report.summary.average_score)}</p>
        </Card>
      ) : null}
      <Card>
        <h2 className="font-semibold text-navy">Compare two assessments</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <select className={fieldClass} value={left} onChange={(event) => setLeft(event.target.value)}>
            <option value="">First assessment</option>
            {assessments.map((item) => <option key={item.id} value={item.id}>{item.assessment_number} · {item.opportunity_name}</option>)}
          </select>
          <select className={fieldClass} value={right} onChange={(event) => setRight(event.target.value)}>
            <option value="">Second assessment</option>
            {assessments.map((item) => <option key={item.id} value={item.id}>{item.assessment_number} · {item.opportunity_name}</option>)}
          </select>
        </div>
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        <Button className="mt-3" disabled={!left || !right} onClick={() => api.get(`/reports/compare?ids=${left},${right}`).then(setComparison).catch((err) => setError(err.message))}>Compare</Button>
        {comparison ? (
          <table className="mt-4 w-full text-left text-sm">
            <thead><tr><th className="py-2">Criterion</th>{comparison.columns.map((column: any) => <th key={column.assessment_id} className="py-2">{column.label}<br />{scoreText(column.score)}</th>)}</tr></thead>
            <tbody>
              {comparison.rows.map((row: any) => (
                <tr key={row.criterion} className="border-t border-line"><td className="py-2">{row.criterion}</td>{row.scores.map((score: any, index: number) => <td key={index}>{scoreText(score.weighted_score)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </Card>
      <div className="mt-4 space-y-2">
        {assessments.map((item) => (
          <div key={item.id} className="flex items-center justify-between rounded-lg border border-line bg-white px-4 py-3 text-sm">
            <span>{item.assessment_number} · {item.opportunity_name}</span>
            <Button variant="secondary" onClick={() => downloadPdf(item.id, item.assessment_number)}>PDF</Button>
          </div>
        ))}
      </div>
    </div>
  );
}
