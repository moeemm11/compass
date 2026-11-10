"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, Empty, PageHeader, fieldClass, toneForStatus } from "@/components/ui";
import { api } from "@/lib/api";
import { label, money, scoreText } from "@/lib/format";

export default function DashboardPage() {
  const [lookups, setLookups] = useState<any>(null);
  const [filters, setFilters] = useState({ status: "", country_id: "", service_line_id: "" });
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/lookups").then(setLookups).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    api.get(`/reports/dashboard?${params.toString()}`).then(setData).catch((err) => setError(err.message));
  }, [filters]);

  const kpis = data?.kpis;
  return (
    <div>
      <PageHeader title="Executive dashboard" subtitle="The live portfolio. Risk-adjusted value counts only opportunities with a recorded probability of winning." />
      {error ? <p className="mb-4 text-sm text-red-700">{error}</p> : null}
      <div className="mb-5 grid gap-3 md:grid-cols-3">
        <select className={fieldClass} value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
          <option value="">All statuses</option>
          {lookups?.statuses?.map((status: string) => <option key={status} value={status}>{label(status)}</option>)}
        </select>
        <select className={fieldClass} value={filters.country_id} onChange={(event) => setFilters({ ...filters, country_id: event.target.value })}>
          <option value="">All countries</option>
          {lookups?.countries?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <select className={fieldClass} value={filters.service_line_id} onChange={(event) => setFilters({ ...filters, service_line_id: event.target.value })}>
          <option value="">All service lines</option>
          {lookups?.service_lines?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
        <Kpi label="Opportunities" value={kpis?.total ?? "—"} />
        <Kpi label="Under assessment" value={kpis?.under_assessment ?? "—"} />
        <Kpi label="Awaiting decision" value={kpis?.awaiting_approval ?? "—"} />
        <Kpi label="Approved" value={kpis?.approved ?? "—"} />
        <Kpi label="Conditionally approved" value={kpis?.conditionally_approved ?? "—"} />
        <Kpi label="Rejected" value={kpis?.rejected ?? "—"} />
        <Kpi label="Pipeline value" value={money(kpis?.pipeline_value)} />
        <Kpi label="Risk-adjusted pipeline" value={money(kpis?.risk_adjusted_pipeline)} />
        <Kpi label="Average score" value={scoreText(kpis?.average_score)} />
      </div>
      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <ChartCard title="Opportunities by status" data={data?.by_status || []} dataKey="count" />
        <ChartCard title="Pipeline value by status" data={data?.pipeline_by_status || []} dataKey="value" />
        <ChartCard title="By country" data={data?.by_country || []} dataKey="count" />
        <ChartCard title="By service line" data={data?.by_service_line || []} dataKey="count" />
        <ChartCard title="Scores over time" data={data?.scores_over_time || []} dataKey="score" />
        <ChartCard title="Win / loss" data={data?.win_loss || []} dataKey="count" />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <Card>
          <h2 className="mb-3 font-semibold text-navy">Pending decisions</h2>
          {data?.pending_approvals?.length ? data.pending_approvals.map((item: any) => (
            <Link key={item.assessment_id + item.stage} href={`/assessments/${item.assessment_id}`} className="block border-t border-line py-3 text-sm">
              <p className="font-medium">{item.opportunity_name}</p>
              <p className="text-muted">{label(item.stage)} · {scoreText(item.score)} · {item.recommendation || "Score incomplete"}</p>
            </Link>
          )) : <Empty title="Nothing is waiting" body="Submitted assessments will appear here for review and decision." />}
        </Card>
        <Card>
          <h2 className="mb-3 font-semibold text-navy">Recent opportunities</h2>
          {data?.recent_opportunities?.length ? data.recent_opportunities.map((item: any) => (
            <Link key={item.id} href={`/opportunities/${item.id}`} className="block border-t border-line py-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium">{item.name}</p>
                <Badge tone={toneForStatus(item.status)}>{item.status_label}</Badge>
              </div>
              <p className="text-muted">{item.reference_number} · {money(item.estimated_value, item.currency_code)}</p>
            </Link>
          )) : <Empty title="No opportunities yet" body="Register the first opportunity to start a portfolio." />}
        </Card>
        <Card>
          <h2 className="mb-3 font-semibold text-navy">Upcoming actions</h2>
          {data?.upcoming_actions?.length ? data.upcoming_actions.map((item: any) => (
            <div key={item.id} className="border-t border-line py-3 text-sm">
              <p className="font-medium">{item.title}</p>
              <p className="text-muted">{item.opportunity_name} · due {item.due_date} · {label(item.priority)}</p>
            </div>
          )) : <Empty title="No dated actions" body="Gap-closure actions with a target date will show here." />}
          <h3 className="mb-2 mt-4 font-semibold text-navy">Recent decisions</h3>
          {data?.recent_decisions?.map((item: any) => (
            <p key={item.decision_date + item.opportunity_name} className="border-t border-line py-2 text-sm">
              {item.opportunity_name}: {label(item.decision)}{item.is_override ? " (override)" : ""}
            </p>
          ))}
        </Card>
      </div>
    </div>
  );
}

function Kpi({ label: name, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{name}</p>
      <p className="mt-2 text-2xl font-semibold text-navy">{value}</p>
    </Card>
  );
}

function ChartCard({ title, data, dataKey }: { title: string; data: any[]; dataKey: string }) {
  return (
    <Card>
      <h2 className="mb-3 font-semibold text-navy">{title}</h2>
      <div className="h-56">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} angle={-20} height={60} textAnchor="end" />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey={dataKey} fill="#0F766E" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <Empty title="No data" body="This chart fills as opportunities are recorded." />}
      </div>
    </Card>
  );
}
