"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Banner, Button, Card, PageHeader, fieldClass } from "@/components/ui";
import { api } from "@/lib/api";

export default function TemplateEditorPage() {
  const params = useParams<{ id: string }>();
  const [template, setTemplate] = useState<any>(null);
  const [draft, setDraft] = useState<any>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const data = await api.get(`/assessment-templates/${params.id}`);
    setTemplate(data);
    setDraft(data.draft);
  }
  useEffect(() => { load().catch((err) => setError(err.message)); }, [params.id]);

  function weightTotal(items: Array<{ weight: number; is_active?: boolean }>) {
    return items.filter((item) => item.is_active !== false).reduce((sum, item) => sum + Number(item.weight || 0), 0);
  }

  async function save() {
    setError("");
    try {
      const saved = await api.put(`/assessment-templates/${params.id}`, {
        criteria: draft.criteria,
        scale: draft.scale,
        recommendation_rules: draft.recommendation_rules,
        questions: draft.questions,
        gap_normalized_threshold: Number(draft.gap_normalized_threshold),
      });
      setTemplate(saved);
      setDraft(saved.draft);
      setMessage(saved.draft.validation_errors.length ? saved.draft.validation_errors.join(" ") : "Draft saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  if (!template) return <p className="text-sm text-muted">{error || "Loading template…"}</p>;
  const editing = draft;

  return (
    <div>
      <PageHeader title={template.name} subtitle={`Status ${template.status}. A published version stays attached to existing assessments.`} />
      {error ? <div className="mb-3"><Banner>{error}</Banner></div> : null}
      {message ? <div className="mb-3"><Banner tone="info">{message}</Banner></div> : null}
      {!editing ? (
        <Card>
          <p className="text-sm">The current version is published and immutable.</p>
          <Button className="mt-3" onClick={() => api.post(`/assessment-templates/${template.id}/versions`).then(load)}>Create new version</Button>
          {template.published ? <p className="mt-3 text-sm text-muted">Published version {template.published.version_number} has {template.published.criteria.length} criteria.</p> : null}
        </Card>
      ) : (
        <div className="space-y-4">
          <Card>
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-navy">Criteria · version {editing.version_number}</h2>
              <p className={weightTotal(editing.criteria) === 100 ? "text-sm text-teal" : "text-sm text-red-700"}>Active weight total {weightTotal(editing.criteria)}%</p>
            </div>
            {editing.criteria.map((criterion: any, index: number) => (
              <div key={index} className="mt-4 rounded-lg border border-line p-3">
                <div className="grid gap-2 md:grid-cols-[1fr_120px]">
                  <input className={fieldClass} value={criterion.name} onChange={(event) => updateCriterion(index, { name: event.target.value })} />
                  <input className={fieldClass} type="number" value={criterion.weight} onChange={(event) => updateCriterion(index, { weight: Number(event.target.value) })} />
                </div>
                <textarea className={`${fieldClass} mt-2`} rows={2} value={criterion.description || ""} onChange={(event) => updateCriterion(index, { description: event.target.value })} />
                <p className="mt-2 text-xs text-muted">Subcriteria total {weightTotal(criterion.subcriteria)}%</p>
                {criterion.subcriteria.map((sub: any, subIndex: number) => (
                  <div key={subIndex} className="mt-2 grid gap-2 md:grid-cols-[1fr_100px]">
                    <input className={fieldClass} value={sub.name} onChange={(event) => updateSub(index, subIndex, { name: event.target.value })} />
                    <input className={fieldClass} type="number" value={sub.weight} onChange={(event) => updateSub(index, subIndex, { weight: Number(event.target.value) })} />
                  </div>
                ))}
                <Button variant="ghost" className="mt-2" onClick={() => updateCriterion(index, { subcriteria: [...criterion.subcriteria, { name: "New subcriterion", weight: 0, is_active: true, is_mandatory: true, scoring_guidance: "" }] })}>Add subcriterion</Button>
              </div>
            ))}
            <Button variant="secondary" className="mt-3" onClick={() => setDraft({ ...editing, criteria: [...editing.criteria, { name: "New criterion", description: "", weight: 0, is_active: true, is_mandatory: true, requires_evidence: false, subcriteria: [] }] })}>Add criterion</Button>
          </Card>
          <Card>
            <h2 className="font-semibold text-navy">Scoring scale</h2>
            <p className="text-sm text-muted">Maximum {editing.scale.maximum_value}. Ratings are not hardcoded in the scoring engine.</p>
            {editing.scale.values.map((value: any, index: number) => (
              <div key={index} className="mt-2 grid gap-2 md:grid-cols-4">
                <input className={fieldClass} type="number" value={value.numeric_value} onChange={(event) => updateScale(index, { numeric_value: Number(event.target.value) })} />
                <input className={fieldClass} value={value.label} onChange={(event) => updateScale(index, { label: event.target.value })} />
                <input className={fieldClass} value={value.description} onChange={(event) => updateScale(index, { description: event.target.value })} />
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={value.requires_justification} onChange={(event) => updateScale(index, { requires_justification: event.target.checked })} /> Justification required</label>
              </div>
            ))}
          </Card>
          <Card>
            <h2 className="font-semibold text-navy">Recommendation thresholds</h2>
            {editing.recommendation_rules.map((rule: any, index: number) => (
              <div key={index} className="mt-2 grid gap-2 md:grid-cols-[1fr_90px_90px]">
                <input className={fieldClass} value={rule.recommendation_name} onChange={(event) => updateRule(index, { recommendation_name: event.target.value })} />
                <input className={fieldClass} type="number" value={rule.minimum_score} onChange={(event) => updateRule(index, { minimum_score: Number(event.target.value) })} />
                <input className={fieldClass} type="number" value={rule.maximum_score} onChange={(event) => updateRule(index, { maximum_score: Number(event.target.value) })} />
              </div>
            ))}
          </Card>
          <div className="flex gap-2">
            <Button onClick={save}>Save draft</Button>
            <Button variant="secondary" onClick={() => api.post(`/assessment-templates/${template.id}/publish`).then(load).catch((err) => setError(err.message))}>Publish</Button>
          </div>
          {editing.validation_errors?.length ? <p className="text-sm text-red-700">{editing.validation_errors.join(" ")}</p> : null}
        </div>
      )}
    </div>
  );

  function updateCriterion(index: number, patch: any) {
    const criteria = draft.criteria.map((criterion: any, itemIndex: number) => itemIndex === index ? { ...criterion, ...patch } : criterion);
    setDraft({ ...draft, criteria });
  }
  function updateSub(index: number, subIndex: number, patch: any) {
    const criteria = draft.criteria.map((criterion: any, itemIndex: number) => itemIndex !== index ? criterion : {
      ...criterion,
      subcriteria: criterion.subcriteria.map((sub: any, current: number) => current === subIndex ? { ...sub, ...patch } : sub),
    });
    setDraft({ ...draft, criteria });
  }
  function updateScale(index: number, patch: any) {
    setDraft({ ...draft, scale: { ...draft.scale, values: draft.scale.values.map((value: any, itemIndex: number) => itemIndex === index ? { ...value, ...patch } : value) } });
  }
  function updateRule(index: number, patch: any) {
    setDraft({ ...draft, recommendation_rules: draft.recommendation_rules.map((rule: any, itemIndex: number) => itemIndex === index ? { ...rule, ...patch } : rule) });
  }
}
