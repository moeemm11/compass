"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button, Card, Empty, Field, PageHeader, fieldClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { label } from "@/lib/format";

export default function PartnersPage() {
  const { can } = useAuth();
  const [partners, setPartners] = useState<any[]>([]);
  const [lookups, setLookups] = useState<any>(null);
  const [name, setName] = useState("");
  const [countryId, setCountryId] = useState("");
  const [error, setError] = useState("");

  function load() { api.get("/partners").then(setPartners); }
  useEffect(() => { load(); api.get("/lookups").then(setLookups); }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/partners", { name, country_id: countryId || null, partnership_status: "prospect" });
      setName("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the partner");
    }
  }

  return (
    <div>
      <PageHeader title="Partners" subtitle="Capabilities, agreements, and commitment status used when an opportunity needs a delivery partner." />
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-3">
          {partners.map((partner) => (
            <Card key={partner.id}>
              <p className="font-semibold text-navy">{partner.name}</p>
              <p className="text-sm text-muted">{partner.country_name || "Country not set"} · {label(partner.partnership_status)} · NDA {label(partner.nda_status)} · agreement {label(partner.agreement_status)}</p>
              <p className="mt-2 text-sm">{partner.capabilities.map((item: any) => item.name).join(", ") || "No capabilities recorded"}</p>
            </Card>
          ))}
          {!partners.length ? <Empty title="No partners" body="Add the organisations Diyar may deliver with." /> : null}
        </div>
        {can("partners.manage") ? (
          <Card>
            <h2 className="font-semibold text-navy">Add partner</h2>
            {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
            <form className="mt-3 space-y-3" onSubmit={create}>
              <Field label="Company name"><input className={fieldClass} required value={name} onChange={(event) => setName(event.target.value)} /></Field>
              <Field label="Country">
                <select className={fieldClass} value={countryId} onChange={(event) => setCountryId(event.target.value)}>
                  <option value="">Select</option>
                  {lookups?.countries?.map((country: any) => <option key={country.id} value={country.id}>{country.name}</option>)}
                </select>
              </Field>
              <Button type="submit">Save partner</Button>
            </form>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
