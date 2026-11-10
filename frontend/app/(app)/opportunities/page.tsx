"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Button, Empty, PageHeader, fieldClass, toneForStatus } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { label, money, scoreText } from "@/lib/format";

export default function OpportunitiesPage() {
  const { can } = useAuth();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [lookups, setLookups] = useState<any>(null);
  const [data, setData] = useState<any>({ items: [], total: 0 });

  useEffect(() => { api.get("/lookups").then(setLookups); }, []);
  useEffect(() => {
    const params = new URLSearchParams({ search, page_size: "50" });
    if (status) params.set("status", status);
    api.get(`/opportunities?${params.toString()}`).then(setData);
  }, [search, status]);

  return (
    <div>
      <PageHeader title="Opportunities" subtitle="Register, qualify, and follow each pursuit through assessment and decision." actions={can("opportunities.create") ? <Link href="/opportunities/new"><Button>New opportunity</Button></Link> : null} />
      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <input className={fieldClass} placeholder="Search name, client, or reference" value={search} onChange={(event) => setSearch(event.target.value)} />
        <select className={fieldClass} value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All statuses</option>
          {lookups?.statuses?.map((item: string) => <option key={item} value={item}>{label(item)}</option>)}
        </select>
      </div>
      <div className="overflow-hidden rounded-xl border border-line bg-white shadow-card">
        <table className="w-full text-left text-sm">
          <thead className="bg-canvas text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3">Opportunity</th>
              <th className="px-4 py-3">Client</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Value</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item: any) => (
              <tr key={item.id} className="border-t border-line">
                <td className="px-4 py-3">
                  <Link href={`/opportunities/${item.id}`} className="font-medium text-navy hover:underline">{item.name}</Link>
                  <p className="text-xs text-muted">{item.reference_number} · {item.country?.name}</p>
                </td>
                <td className="px-4 py-3">{item.client_name}</td>
                <td className="px-4 py-3"><Badge tone={toneForStatus(item.status)}>{item.status_label}</Badge></td>
                <td className="px-4 py-3">{money(item.estimated_value, item.currency_code)}</td>
                <td className="px-4 py-3">{scoreText(item.score)}</td>
                <td className="px-4 py-3">{item.recommendation || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data.items.length ? <div className="p-6"><Empty title="No opportunities match" body="Adjust the filters or register a new opportunity." /></div> : null}
      </div>
      <p className="mt-3 text-xs text-muted">{data.total} opportunities</p>
    </div>
  );
}
