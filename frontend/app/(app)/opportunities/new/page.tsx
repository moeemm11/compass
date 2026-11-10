"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Banner, Button, Field, PageHeader, fieldClass } from "@/components/ui";
import { api } from "@/lib/api";

export default function NewOpportunityPage() {
  const router = useRouter();
  const [lookups, setLookups] = useState<any>(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState<any>({
    name: "",
    client_name: "",
    description: "",
    opportunity_source: "New Client",
    currency_code: "AED",
    strategic_importance: "medium",
    partner_required: false,
    service_line_ids: [] as string[],
  });

  useEffect(() => { api.get("/lookups").then(setLookups); }, []);

  function set(key: string, value: unknown) {
    setForm((current: any) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const created = await api.post("/opportunities", {
        ...form,
        estimated_value: form.estimated_value ? Number(form.estimated_value) : null,
        expected_duration: form.expected_duration ? Number(form.expected_duration) : null,
        business_unit_id: form.business_unit_id || null,
      });
      router.push(`/opportunities/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the opportunity");
    }
  }

  return (
    <div className="max-w-3xl">
      <PageHeader title="Register an opportunity" subtitle="Required fields establish the record. Status starts at Identified and moves only through the workflow." />
      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-line bg-white p-5 shadow-card">
        {error ? <Banner>{error}</Banner> : null}
        <Field label="Opportunity name"><input className={fieldClass} required value={form.name} onChange={(event) => set("name", event.target.value)} /></Field>
        <Field label="Client"><input className={fieldClass} required value={form.client_name} onChange={(event) => set("client_name", event.target.value)} /></Field>
        <Field label="Description"><textarea className={fieldClass} required rows={4} value={form.description} onChange={(event) => set("description", event.target.value)} /></Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Country">
            <select className={fieldClass} required value={form.country_id || ""} onChange={(event) => set("country_id", event.target.value)}>
              <option value="">Select</option>
              {lookups?.countries?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </Field>
          <Field label="Sector">
            <select className={fieldClass} required value={form.sector_id || ""} onChange={(event) => set("sector_id", event.target.value)}>
              <option value="">Select</option>
              {lookups?.sectors?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </Field>
          <Field label="Business unit">
            <select className={fieldClass} value={form.business_unit_id || ""} onChange={(event) => set("business_unit_id", event.target.value)}>
              <option value="">None</option>
              {lookups?.business_units?.map((item: any) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </Field>
          <Field label="Source">
            <select className={fieldClass} value={form.opportunity_source} onChange={(event) => set("opportunity_source", event.target.value)}>
              {lookups?.sources?.map((item: string) => <option key={item}>{item}</option>)}
            </select>
          </Field>
          <Field label="Estimated contract value">
            <input className={fieldClass} type="number" min="0" value={form.estimated_value || ""} onChange={(event) => set("estimated_value", event.target.value)} />
          </Field>
          <Field label="Currency">
            <select className={fieldClass} value={form.currency_code} onChange={(event) => set("currency_code", event.target.value)}>
              {lookups?.currencies?.map((item: any) => <option key={item.code} value={item.code}>{item.code} — {item.name}</option>)}
            </select>
          </Field>
          <Field label="Owner">
            <select className={fieldClass} required value={form.owner_id || ""} onChange={(event) => set("owner_id", event.target.value)}>
              <option value="">Select</option>
              {lookups?.users?.map((item: any) => <option key={item.id} value={item.id}>{item.full_name}</option>)}
            </select>
          </Field>
          <Field label="Strategic importance">
            <select className={fieldClass} value={form.strategic_importance} onChange={(event) => set("strategic_importance", event.target.value)}>
              {lookups?.strategic_importance?.map((item: string) => <option key={item} value={item}>{item}</option>)}
            </select>
          </Field>
          <Field label="Expected award date"><input className={fieldClass} type="date" onChange={(event) => set("expected_award_date", event.target.value || null)} /></Field>
          <Field label="Expected duration (months)"><input className={fieldClass} type="number" min="0" onChange={(event) => set("expected_duration", event.target.value)} /></Field>
        </div>
        <fieldset>
          <legend className="mb-2 text-sm font-medium">Service lines</legend>
          <div className="grid gap-2 md:grid-cols-2">
            {lookups?.service_lines?.map((item: any) => (
              <label key={item.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.service_line_ids.includes(item.id)} onChange={(event) => {
                  const next = event.target.checked ? [...form.service_line_ids, item.id] : form.service_line_ids.filter((id: string) => id !== item.id);
                  set("service_line_ids", next);
                }} />
                {item.name}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.partner_required} onChange={(event) => set("partner_required", event.target.checked)} />
          A delivery partner is mandatory for this opportunity
        </label>
        <Button type="submit">Create opportunity</Button>
      </form>
    </div>
  );
}
