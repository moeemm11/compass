"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, Fragment, useEffect, useState } from "react";
import { Badge, Banner, Button, Card, Empty, Field, PageHeader, fieldClass, toneForStatus } from "@/components/ui";
import { API_URL, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { label, money, scoreText } from "@/lib/format";

const TABS = ["Overview", "Assessment", "Commercial", "Partners", "Risks", "Resources", "Documents", "Actions", "Decisions", "Activity"];

export default function OpportunityPage() {
  const params = useParams<{ id: string }>();
  const { can } = useAuth();
  const [item, setItem] = useState<any>(null);
  const [lookups, setLookups] = useState<any>(null);
  const [templates, setTemplates] = useState<any[]>([]);
  const [tab, setTab] = useState("Overview");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const [detail, lookupData, templateData] = await Promise.all([
      api.get(`/opportunities/${params.id}`),
      api.get("/lookups"),
      api.get("/assessment-templates"),
    ]);
    setItem(detail);
    setLookups(lookupData);
    setTemplates(templateData.filter((template: any) => template.status === "active"));
  }

  useEffect(() => { load().catch((err) => setError(err.message)); }, [params.id]);

  async function run(action: () => Promise<unknown>, success: string) {
    setError("");
    setMessage("");
    try {
      await action();
      await load();
      setMessage(success);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The change could not be saved");
    }
  }

  if (!item) return <p className="text-sm text-muted">{error || "Loading opportunity…"}</p>;

  return (
    <div>
      <PageHeader
        title={item.name}
        subtitle={`${item.reference_number} · ${item.client_name} · ${item.country?.name}`}
        actions={<Badge tone={toneForStatus(item.status)}>{item.status_label}</Badge>}
      />
      {error ? <div className="mb-4"><Banner>{error}</Banner></div> : null}
      {message ? <div className="mb-4"><Banner tone="info">{message}</Banner></div> : null}
      <div className="mb-5 flex gap-2 overflow-x-auto">
        {TABS.map((name) => (
          <button key={name} className={`rounded-full px-3 py-1.5 text-sm ${tab === name ? "bg-navy text-white" : "bg-white text-muted"}`} onClick={() => setTab(name)}>{name}</button>
        ))}
      </div>
      {tab === "Overview" && <Overview item={item} canEdit={can("opportunities.edit_own") || can("opportunities.edit_any")} onTransition={(status) => run(() => api.post(`/opportunities/${item.id}/transition`, { status }), "Status updated")} />}
      {tab === "Assessment" && <AssessmentTab item={item} templates={templates} canCreate={can("opportunities.edit_own") || can("assessments.complete_any")} onCreate={(templateId) => run(() => api.post("/assessments", { opportunity_id: item.id, template_id: templateId }), "Assessment created")} />}
      {tab === "Commercial" && <CommercialTab item={item} onSave={(payload) => run(() => api.put(`/opportunities/${item.id}/commercial`, payload), "Commercial assessment saved")} />}
      {tab === "Partners" && <PartnersTab item={item} onLink={(payload) => run(() => api.post(`/opportunities/${item.id}/partners`, payload), "Partner linked")} />}
      {tab === "Risks" && <RisksTab item={item} lookups={lookups} onSave={(payload) => run(() => api.post(`/opportunities/${item.id}/risks`, payload), "Risk recorded")} />}
      {tab === "Resources" && <ResourcesTab item={item} lookups={lookups} onSave={(payload) => run(() => api.post(`/opportunities/${item.id}/resources`, payload), "Resource recorded")} />}
      {tab === "Documents" && <DocumentsTab item={item} onUpload={(file) => {
        const form = new FormData();
        form.set("file", file);
        form.set("entity_type", "opportunity");
        form.set("entity_id", item.id);
        return run(() => api.upload("/attachments", form), "Document uploaded");
      }} />}
      {tab === "Actions" && <ActionsTab item={item} lookups={lookups} onSave={(payload) => run(() => api.post(`/opportunities/${item.id}/actions`, payload), "Action recorded")} />}
      {tab === "Decisions" && <DecisionsTab item={item} />}
      {tab === "Activity" && <ActivityTab item={item} />}
    </div>
  );
}

function Overview({ item, canEdit, onTransition }: { item: any; canEdit: boolean; onTransition: (status: string) => void }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <h2 className="font-semibold text-navy">Overview</h2>
        <p className="mt-3 text-sm leading-6">{item.description}</p>
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <Info label="Source" value={item.opportunity_source} />
          <Info label="Sector" value={item.sector?.name} />
          <Info label="Business unit" value={item.business_unit?.name} />
          <Info label="Owner" value={item.owner?.full_name} />
          <Info label="Value" value={money(item.estimated_value, item.currency_code)} />
          <Info label="Importance" value={label(item.strategic_importance)} />
          <Info label="Partner mandatory" value={item.partner_required ? "Yes" : "No"} />
          <Info label="Service lines" value={item.service_lines.map((line: any) => line.name).join(", ")} />
        </dl>
      </Card>
      <Card>
        <h2 className="font-semibold text-navy">Move status</h2>
        <p className="mt-1 text-xs text-muted">Approval outcomes are recorded by an executive, not from this list.</p>
        <div className="mt-3 space-y-2">
          {item.allowed_transitions.length ? item.allowed_transitions.map((status: string) => (
            <Button key={status} variant="secondary" className="w-full" disabled={!canEdit} onClick={() => onTransition(status)}>{label(status)}</Button>
          )) : <p className="text-sm text-muted">No manual transition is available from {item.status_label}.</p>}
        </div>
      </Card>
    </div>
  );
}

function AssessmentTab({ item, templates, canCreate, onCreate }: { item: any; templates: any[]; canCreate: boolean; onCreate: (id: string) => void }) {
  const [templateId, setTemplateId] = useState("");
  return (
    <Card>
      <h2 className="font-semibold text-navy">Assessments</h2>
      <p className="mt-1 text-sm text-muted">Each assessment keeps the template version it was created with.</p>
      <div className="mt-4 space-y-3">
        {item.assessments.length ? item.assessments.map((assessment: any) => (
          <Link key={assessment.id} href={`/assessments/${assessment.id}`} className="flex items-center justify-between rounded-lg border border-line px-3 py-3 text-sm">
            <span>
              <span className="font-medium">{assessment.assessment_number}</span>
              <span className="ml-2 text-muted">{label(assessment.status)}</span>
            </span>
            <span>{scoreText(assessment.calculated_score)} · {assessment.recommendation_name || "No recommendation yet"}</span>
          </Link>
        )) : <Empty title="No assessment yet" body="Choose a published template to start one." />}
      </div>
      {canCreate ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <select className={fieldClass + " max-w-sm"} value={templateId} onChange={(event) => setTemplateId(event.target.value)}>
            <option value="">Published template</option>
            {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
          </select>
          <Button disabled={!templateId} onClick={() => onCreate(templateId)}>Start assessment</Button>
        </div>
      ) : null}
    </Card>
  );
}

function CommercialTab({ item, onSave }: { item: any; onSave: (payload: any) => void }) {
  const current = item.commercial || {};
  const [form, setForm] = useState<any>({
    contract_value: current.contract_value || item.estimated_value || 0,
    currency_code: item.currency_code,
    internal_cost: current.internal_cost || 0,
    partner_cost: current.partner_cost || 0,
    travel_cost: current.travel_cost || 0,
    third_party_cost: current.third_party_cost || 0,
    licensing_cost: current.licensing_cost || 0,
    other_cost: current.other_cost || 0,
    bid_cost: current.bid_cost || 0,
    contingency: current.contingency || 0,
    probability_of_winning: current.probability_of_winning || 0,
    assumptions: current.assumptions || "",
    figures_confirmed: current.figures_confirmed || false,
  });
  const fields = ["internal_cost", "partner_cost", "travel_cost", "third_party_cost", "licensing_cost", "other_cost", "contingency", "bid_cost", "probability_of_winning"];
  return (
    <Card>
      <h2 className="font-semibold text-navy">Commercial feasibility</h2>
      <p className="mt-1 text-sm text-muted">{current.figures_label || "Estimated figures. These are assumptions, not confirmed financials."} Currency conversion is not enabled, so the currency stays {item.currency_code}.</p>
      <form className="mt-4 grid gap-3 md:grid-cols-3" onSubmit={(event: FormEvent) => { event.preventDefault(); onSave(form); }}>
        <Field label="Contract value"><input className={fieldClass} type="number" value={form.contract_value} onChange={(event) => setForm({ ...form, contract_value: Number(event.target.value) })} /></Field>
        {fields.map((field) => (
          <Field key={field} label={label(field)}>
            <input className={fieldClass} type="number" value={form[field]} onChange={(event) => setForm({ ...form, [field]: Number(event.target.value) })} />
          </Field>
        ))}
        <Field label="Assumptions"><textarea className={fieldClass} rows={3} value={form.assumptions} onChange={(event) => setForm({ ...form, assumptions: event.target.value })} /></Field>
        <label className="flex items-center gap-2 text-sm md:col-span-3">
          <input type="checkbox" checked={form.figures_confirmed} onChange={(event) => setForm({ ...form, figures_confirmed: event.target.checked })} />
          These figures are confirmed, not estimates
        </label>
        <div className="md:col-span-3"><Button type="submit">Save commercial assessment</Button></div>
      </form>
      {item.commercial ? (
        <dl className="mt-5 grid gap-3 text-sm md:grid-cols-4">
          <Info label="Total cost" value={money(item.commercial.total_cost, item.currency_code)} />
          <Info label="Gross profit" value={money(item.commercial.gross_profit, item.currency_code)} />
          <Info label="Gross margin" value={item.commercial.gross_margin === null ? "—" : `${item.commercial.gross_margin}%`} />
          <Info label="Expected revenue" value={money(item.commercial.expected_revenue, item.currency_code)} />
          <Info label="Expected contribution" value={money(item.commercial.expected_contribution, item.currency_code)} />
          <Info label="Partner cost share" value={item.commercial.partner_cost_percentage === null ? "—" : `${item.commercial.partner_cost_percentage}%`} />
        </dl>
      ) : null}
    </Card>
  );
}

function PartnersTab({ item, onLink }: { item: any; onLink: (payload: any) => void }) {
  const [partners, setPartners] = useState<any[]>([]);
  const [partnerId, setPartnerId] = useState("");
  const [commitment, setCommitment] = useState("proposed");
  useEffect(() => { api.get("/partners").then(setPartners); }, []);
  return (
    <Card>
      <h2 className="font-semibold text-navy">Partners</h2>
      <div className="mt-3 space-y-2">
        {item.partners.length ? item.partners.map((partner: any) => (
          <div key={partner.id} className="rounded-lg border border-line px-3 py-2 text-sm">
            <span className="font-medium">{partner.name}</span> · {partner.role} · {label(partner.commitment_status)}
          </div>
        )) : <Empty title="No partner linked" body="Link a partner from the directory." />}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <select className={fieldClass + " max-w-sm"} value={partnerId} onChange={(event) => setPartnerId(event.target.value)}>
          <option value="">Select partner</option>
          {partners.map((partner) => <option key={partner.id} value={partner.id}>{partner.name}</option>)}
        </select>
        <select className={fieldClass + " max-w-[180px]"} value={commitment} onChange={(event) => setCommitment(event.target.value)}>
          {["proposed", "confirmed", "contracted", "withdrawn"].map((status) => <option key={status} value={status}>{label(status)}</option>)}
        </select>
        <Button disabled={!partnerId} onClick={() => onLink({ partner_id: partnerId, commitment_status: commitment, role: "Delivery partner" })}>Link partner</Button>
        <Link href="/partners"><Button variant="secondary">Partner directory</Button></Link>
      </div>
    </Card>
  );
}

function RisksTab({ item, lookups, onSave }: { item: any; lookups: any; onSave: (payload: any) => void }) {
  const [form, setForm] = useState<any>({ title: "", category: "Technical", probability: 3, impact: 3, status: "open", mitigation_plan: "", description: "" });
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <h2 className="font-semibold text-navy">Risk register</h2>
        <div className="mt-3 space-y-2">
          {item.risks.map((risk: any) => (
            <div key={risk.id} className="rounded-lg border border-line px-3 py-2 text-sm">
              <p className="font-medium">{risk.reference_number} · {risk.title}</p>
              <p className="text-muted">{risk.category} · probability {risk.probability} × impact {risk.impact} = {risk.inherent_score} · {label(risk.status)}</p>
            </div>
          ))}
          {!item.risks.length ? <Empty title="No risks" body="Record a risk with probability and impact from 1 to 5." /> : null}
        </div>
        <form className="mt-4 space-y-3" onSubmit={(event) => { event.preventDefault(); onSave(form); }}>
          <Field label="Title"><input className={fieldClass} required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Category"><select className={fieldClass} value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{lookups?.risk_categories?.map((itemName: string) => <option key={itemName}>{itemName}</option>)}</select></Field>
            <Field label="Status"><select className={fieldClass} value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value })}>{lookups?.risk_statuses?.map((itemName: string) => <option key={itemName} value={itemName}>{label(itemName)}</option>)}</select></Field>
            <Field label="Probability"><input className={fieldClass} type="number" min={1} max={5} value={form.probability} onChange={(event) => setForm({ ...form, probability: Number(event.target.value) })} /></Field>
            <Field label="Impact"><input className={fieldClass} type="number" min={1} max={5} value={form.impact} onChange={(event) => setForm({ ...form, impact: Number(event.target.value) })} /></Field>
          </div>
          <Field label="Mitigation"><textarea className={fieldClass} value={form.mitigation_plan} onChange={(event) => setForm({ ...form, mitigation_plan: event.target.value })} /></Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" onChange={(event) => setForm({ ...form, is_regulatory_blocker: event.target.checked })} /> Regulatory blocker</label>
          <Button type="submit">Add risk</Button>
        </form>
      </Card>
      <Card>
        <h2 className="font-semibold text-navy">5 × 5 heatmap</h2>
        <p className="mt-1 text-xs text-muted">Rows are probability, columns are impact. The number is how many open records sit in that cell.</p>
        <div className="mt-4 grid grid-cols-6 gap-1 text-center text-xs">
          <div />
          {[1, 2, 3, 4, 5].map((impact) => <div key={impact} className="text-muted">I{impact}</div>)}
          {[5, 4, 3, 2, 1].map((probability) => (
            <Fragment key={probability}>
              <div className="text-muted">P{probability}</div>
              {[1, 2, 3, 4, 5].map((impact) => {
                const cell = item.heatmap.find((entry: any) => entry.probability === probability && entry.impact === impact);
                const intensity = cell?.count ? Math.min(cell.score / 25, 1) : 0;
                return <div key={`${probability}-${impact}`} className="grid h-10 place-items-center rounded" style={{ background: intensity ? `rgba(185, 28, 28, ${0.15 + intensity * 0.75})` : "#F3F5F8", color: intensity > 0.55 ? "white" : "#122033" }}>{cell?.count || ""}</div>;
              })}
            </Fragment>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ResourcesTab({ item, lookups, onSave }: { item: any; lookups: any; onSave: (payload: any) => void }) {
  const [form, setForm] = useState<any>({ role: "", required_skills: "", quantity: 1, allocation_percentage: 100, resource_type: "internal", availability_status: "unconfirmed" });
  const summary = item.resource_summary;
  return (
    <Card>
      <h2 className="font-semibold text-navy">Delivery feasibility: {summary.delivery_feasibility}</h2>
      <p className="mt-1 text-sm text-muted">Demand {summary.total_demand} · confirmed internal {summary.confirmed_internal} · external {summary.external_dependency} · gaps {summary.critical_skill_gaps}</p>
      <div className="mt-3 space-y-2">
        {item.resources.map((resource: any) => <div key={resource.id} className="rounded-lg border border-line px-3 py-2 text-sm">{resource.quantity} × {resource.role} · {label(resource.resource_type)} · {label(resource.availability_status)}</div>)}
      </div>
      <form className="mt-4 grid gap-3 md:grid-cols-3" onSubmit={(event) => { event.preventDefault(); onSave(form); }}>
        <Field label="Role"><input className={fieldClass} required value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })} /></Field>
        <Field label="Skills"><input className={fieldClass} value={form.required_skills} onChange={(event) => setForm({ ...form, required_skills: event.target.value })} /></Field>
        <Field label="Quantity"><input className={fieldClass} type="number" min={1} value={form.quantity} onChange={(event) => setForm({ ...form, quantity: Number(event.target.value) })} /></Field>
        <Field label="Type"><select className={fieldClass} value={form.resource_type} onChange={(event) => setForm({ ...form, resource_type: event.target.value })}>{lookups?.resource_types?.map((itemName: string) => <option key={itemName} value={itemName}>{label(itemName)}</option>)}</select></Field>
        <Field label="Availability"><select className={fieldClass} value={form.availability_status} onChange={(event) => setForm({ ...form, availability_status: event.target.value })}>{lookups?.availability_statuses?.map((itemName: string) => <option key={itemName} value={itemName}>{label(itemName)}</option>)}</select></Field>
        <div className="self-end"><Button type="submit">Add resource</Button></div>
      </form>
    </Card>
  );
}

function DocumentsTab({ item, onUpload }: { item: any; onUpload: (file: File) => void }) {
  return (
    <Card>
      <h2 className="font-semibold text-navy">Documents</h2>
      <div className="mt-3 space-y-2">
        {item.attachments.map((file: any) => (
          <button key={file.id} className="block text-sm text-brand underline" onClick={async () => {
            const response = await fetch(`${API_URL}/attachments/${file.id}`, { headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` } });
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = file.file_name;
            link.click();
          }}>{file.file_name}</button>
        ))}
        {!item.attachments.length ? <Empty title="No documents" body="Upload supporting files. Access still requires a signed-in user." /> : null}
      </div>
      <input className="mt-4 text-sm" type="file" onChange={(event) => { const file = event.target.files?.[0]; if (file) onUpload(file); }} />
    </Card>
  );
}

function ActionsTab({ item, lookups, onSave }: { item: any; lookups: any; onSave: (payload: any) => void }) {
  const [title, setTitle] = useState("");
  return (
    <Card>
      <h2 className="font-semibold text-navy">Action plan</h2>
      <div className="mt-3 space-y-2">
        {item.actions.map((action: any) => (
          <div key={action.id} className="rounded-lg border border-line px-3 py-2 text-sm">
            <p className="font-medium">{action.reference_number} · {action.title}</p>
            <p className="text-muted">{label(action.status)} · {label(action.priority)}{action.is_mandatory_for_commitment ? " · mandatory before commitment" : ""}</p>
          </div>
        ))}
        {!item.actions.length ? <Empty title="No actions" body="Submitting an assessment creates actions for criteria at or below the gap threshold." /> : null}
      </div>
      <form className="mt-4 flex gap-2" onSubmit={(event) => { event.preventDefault(); onSave({ title, priority: "medium", status: "not_started" }); setTitle(""); }}>
        <input className={fieldClass} placeholder="Required action" value={title} onChange={(event) => setTitle(event.target.value)} required />
        <Button type="submit">Add</Button>
      </form>
      <p className="mt-2 text-xs text-muted">Priorities: {lookups?.action_priorities?.join(", ")}</p>
    </Card>
  );
}

function DecisionsTab({ item }: { item: any }) {
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="font-semibold text-navy">Management decisions</h2>
        {item.decisions.length ? item.decisions.map((decision: any) => (
          <div key={decision.id} className="mt-3 border-t border-line pt-3 text-sm">
            <p className="font-medium">{label(decision.final_decision)} by {decision.decision_maker}</p>
            <p>System recommendation: {decision.calculated_recommendation} ({scoreText(decision.calculated_score)})</p>
            {decision.is_override ? <p>Override to {decision.override_recommendation}: {decision.override_reason}</p> : <p>The decision followed the system recommendation.</p>}
            {decision.exception_justification ? <p>Exception: {decision.exception_justification}</p> : null}
          </div>
        )) : <Empty title="No decision yet" body="The executive decision is recorded from the approval inbox." />}
      </Card>
      <Card>
        <h2 className="font-semibold text-navy">Approval history</h2>
        {item.approvals.map((approval: any) => (
          <p key={approval.id} className="mt-2 text-sm">{approval.decided_at}: {label(approval.stage)} — {label(approval.decision)} by {approval.approver}. {approval.comments}</p>
        ))}
      </Card>
    </div>
  );
}

function ActivityTab({ item }: { item: any }) {
  return (
    <Card>
      {item.activity.map((entry: any) => (
        <div key={entry.id} className="border-b border-line py-3 text-sm">
          <p className="font-medium">{entry.summary}</p>
          <p className="text-muted">{entry.actor} · {new Date(entry.created_at).toLocaleString()}</p>
        </div>
      ))}
    </Card>
  );
}

function Info({ label: name, value }: { label: string; value?: string }) {
  return <div><dt className="text-xs uppercase tracking-wide text-muted">{name}</dt><dd className="mt-1">{value || "—"}</dd></div>;
}
