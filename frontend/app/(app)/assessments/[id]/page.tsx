"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge, Banner, Button, Card, PageHeader, fieldClass } from "@/components/ui";
import { api, downloadPdf } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { label, scoreText } from "@/lib/format";

export default function AssessmentPage() {
  const params = useParams<{ id: string }>();
  const { can, user } = useAuth();
  const [assessment, setAssessment] = useState<any>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [decision, setDecision] = useState("approved");
  const [comments, setComments] = useState("");
  const [overrideRecommendation, setOverrideRecommendation] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [exceptionJustification, setExceptionJustification] = useState("");
  const [reviewComments, setReviewComments] = useState("");

  async function load() {
    setAssessment(await api.get(`/assessments/${params.id}`));
  }
  useEffect(() => { load().catch((err) => setError(err.message)); }, [params.id]);

  function updateSub(subId: string, patch: any) {
    setAssessment((current: any) => ({
      ...current,
      criteria: current.criteria.map((criterion: any) => ({
        ...criterion,
        subcriteria: criterion.subcriteria.map((sub: any) => sub.id === subId ? { ...sub, ...patch } : sub),
      })),
    }));
  }

  function updateQuestion(id: string, response_text: string) {
    setAssessment((current: any) => ({
      ...current,
      questions: current.questions.map((question: any) => question.id === id ? { ...question, response_text } : question),
    }));
  }

  async function save() {
    setError("");
    const payload = {
      subcriterion_scores: assessment.criteria.flatMap((criterion: any) => criterion.subcriteria.map((sub: any) => ({
        subcriterion_id: sub.id,
        selected_score: sub.selected_score,
        comments: sub.comments || "",
      }))),
      responses: assessment.questions.map((question: any) => ({ question_id: question.id, response_text: question.response_text || "" })),
    };
    try {
      setAssessment(await api.put(`/assessments/${assessment.id}`, payload));
      setMessage("Draft saved. The score is calculated on the server.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function submit() {
    setError("");
    try {
      await save();
      setAssessment(await api.post(`/assessments/${assessment.id}/submit`));
      setMessage("Assessment submitted for review.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    }
  }

  if (!assessment) return <p className="text-sm text-muted">{error || "Loading assessment…"}</p>;
  const editable = assessment.can_edit && ["draft", "in_progress", "returned"].includes(assessment.status);
  const rules = assessment.recommendation_options || [];

  return (
    <div>
      <PageHeader
        title={assessment.opportunity_name}
        subtitle={`${assessment.assessment_number} · ${assessment.template.name} version ${assessment.template.version_number} · ${label(assessment.status)}`}
        actions={<Link href={`/opportunities/${assessment.opportunity_id}`}><Button variant="secondary">Opportunity</Button></Link>}
      />
      {error ? <div className="mb-4"><Banner>{error}</Banner></div> : null}
      {message ? <div className="mb-4"><Banner tone="info">{message}</Banner></div> : null}
      <div className="mb-5 grid gap-3 md:grid-cols-4">
        <Card className="p-4"><p className="text-xs uppercase text-muted">Score</p><p className="text-3xl font-semibold text-navy">{scoreText(assessment.calculated_score)}</p><p className="text-xs text-muted">Exact {assessment.calculated_score_exact || "—"}</p></Card>
        <Card className="p-4"><p className="text-xs uppercase text-muted">Completion</p><p className="text-3xl font-semibold text-navy">{assessment.completion_percentage}%</p><p className="text-xs text-muted">Separate from the score</p></Card>
        <Card className="p-4 md:col-span-2" style={{ borderTop: `4px solid ${assessment.recommendation_color}` }}>
          <p className="text-xs uppercase text-muted">{assessment.recommendation_final ? "Final recommendation" : "Recommendation"}</p>
          <p className="mt-1 text-lg font-semibold text-navy">{assessment.recommendation_name || "Not available until the assessment is complete"}</p>
          <p className="mt-1 text-sm text-muted">{assessment.recommendation_description}</p>
        </Card>
      </div>
      {assessment.red_flags?.length ? (
        <div className="mb-5"><Banner>Red flags do not change the score. {assessment.red_flags.map((flag: any) => flag.detail).join(" ")}</Banner></div>
      ) : null}
      {assessment.blockers?.length ? <div className="mb-5"><Banner>{assessment.blockers.join(" ")}</Banner></div> : null}
      <div className="space-y-4">
        {assessment.criteria.map((criterion: any) => (
          <Card key={criterion.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold text-navy">{criterion.name}</h2>
                <p className="text-sm text-muted">{criterion.description}</p>
              </div>
              <div className="text-right text-sm">
                <p>Weight {criterion.weight}%</p>
                <p>Weighted result {scoreText(criterion.weighted_score)}</p>
              </div>
            </div>
            <div className="mt-4 space-y-4">
              {criterion.subcriteria.map((sub: any) => (
                <div key={sub.id}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">{sub.name} <span className="text-muted">({sub.weight}% of this criterion)</span></p>
                    <Badge>{sub.selected_score ? assessment.scale.values.find((value: any) => value.numeric_value === sub.selected_score)?.label || sub.selected_score : "Not scored"}</Badge>
                  </div>
                  {sub.scoring_guidance ? <p className="text-xs text-muted">{sub.scoring_guidance}</p> : null}
                  <div className="mt-2 flex flex-wrap gap-2">
                    {assessment.scale.values.filter((value: any) => value.is_selectable).map((value: any) => (
                      <button key={value.numeric_value} disabled={!editable} className={`rounded-md border px-3 py-1.5 text-sm ${sub.selected_score === value.numeric_value ? "border-teal bg-teal-soft" : "border-line"}`} onClick={() => updateSub(sub.id, { selected_score: value.numeric_value })}>
                        {value.numeric_value} {value.label}
                      </button>
                    ))}
                  </div>
                  <textarea className={`${fieldClass} mt-2`} rows={2} disabled={!editable} placeholder="Justification or evidence note" value={sub.comments || ""} onChange={(event) => updateSub(sub.id, { comments: event.target.value })} />
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
      <Card className="mt-4">
        <h2 className="font-semibold text-navy">Questions</h2>
        <div className="mt-3 space-y-3">
          {assessment.questions.map((question: any) => (
            <label key={question.id} className="block text-sm">
              {question.prompt} {question.is_mandatory ? <span className="text-red-700">Required</span> : null}
              <textarea className={`${fieldClass} mt-1`} rows={3} disabled={!editable} value={question.response_text || ""} onChange={(event) => updateQuestion(question.id, event.target.value)} />
            </label>
          ))}
        </div>
      </Card>
      {editable ? (
        <div className="mt-4 flex gap-2">
          <Button onClick={save}>Save draft</Button>
          {(can("assessments.complete_any") || can("opportunities.edit_own")) && <Button variant="secondary" onClick={submit}>Submit for review</Button>}
          <label className="text-sm">
            <input type="file" className="hidden" onChange={async (event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              const form = new FormData();
              form.set("file", file);
              try { await api.upload(`/assessments/${assessment.id}/evidence`, form); setMessage("Evidence uploaded."); await load(); }
              catch (err) { setError(err instanceof Error ? err.message : "Upload failed"); }
            }} />
            <span className="inline-flex cursor-pointer rounded-md border border-line bg-white px-3.5 py-2">Upload evidence</span>
          </label>
        </div>
      ) : null}
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="font-semibold text-navy">Strengths</h2>
          <ul className="mt-2 list-disc pl-5 text-sm">{assessment.strengths.map((item: any) => <li key={item.criterion_name}>{item.criterion_name} ({item.score})</li>)}</ul>
          {!assessment.strengths.length ? <p className="text-sm text-muted">None yet.</p> : null}
        </Card>
        <Card>
          <h2 className="font-semibold text-navy">Gaps and recommended actions</h2>
          {assessment.gaps.map((gap: any) => <p key={gap.criterion_id} className="mt-2 text-sm">{gap.summary} {gap.suggestion}</p>)}
          {assessment.actions.map((action: any) => <p key={action.id} className="mt-2 text-sm text-muted">{action.reference_number}: {action.title}</p>)}
        </Card>
      </div>
      {assessment.status === "submitted" && can("assessments.review") && (
        <Card className="mt-4">
          <h2 className="font-semibold text-navy">Review</h2>
          <p className="text-sm text-muted">Functional review is recorded before commercial review. Requesting information returns the assessment.</p>
          <textarea className={`${fieldClass} mt-3`} rows={3} value={reviewComments} onChange={(event) => setReviewComments(event.target.value)} placeholder="Review comments" />
          <div className="mt-3 flex flex-wrap gap-2">
            {user?.roles.includes("Functional Reviewer") || user?.roles.includes("System Administrator") ? <Button onClick={() => api.post(`/assessments/${assessment.id}/reviews`, { stage: "functional_review", decision: "confirmed", comments: reviewComments }).then(setAssessment).catch((err) => setError(err.message))}>Confirm functional review</Button> : null}
            {user?.roles.includes("Commercial Reviewer") || user?.roles.includes("System Administrator") ? <Button onClick={() => api.post(`/assessments/${assessment.id}/reviews`, { stage: "commercial_review", decision: "confirmed", comments: reviewComments }).then(setAssessment).catch((err) => setError(err.message))}>Confirm commercial review</Button> : null}
            <Button variant="secondary" onClick={() => api.post(`/assessments/${assessment.id}/reviews`, { stage: user?.roles.includes("Commercial Reviewer") ? "commercial_review" : "functional_review", decision: "request_information", comments: reviewComments }).then(setAssessment).catch((err) => setError(err.message))}>Request information</Button>
          </div>
        </Card>
      )}
      {assessment.status === "pending_approval" && can("approvals.decide") && (
        <Card className="mt-4">
          <h2 className="font-semibold text-navy">Executive decision</h2>
          <p className="text-sm text-muted">The system recommendation stays visible even if you override it. An override and any red-flag exception both need a justification.</p>
          <div className="mt-3 grid gap-3">
            <select className={fieldClass} value={decision} onChange={(event) => setDecision(event.target.value)}>
              {(assessment.decision_options || []).map((item: string) => <option key={item} value={item}>{label(item)}</option>)}
            </select>
            <textarea className={fieldClass} rows={3} placeholder="Decision comments" value={comments} onChange={(event) => setComments(event.target.value)} />
            <select className={fieldClass} value={overrideRecommendation} onChange={(event) => setOverrideRecommendation(event.target.value)}>
              <option value="">Keep the system recommendation</option>
              {rules.map((rule) => <option key={rule}>{rule}</option>)}
            </select>
            <textarea className={fieldClass} rows={2} placeholder="Override justification, required if the recommendation changes" value={overrideReason} onChange={(event) => setOverrideReason(event.target.value)} />
            <textarea className={fieldClass} rows={2} placeholder="Exception justification, required to approve while a red flag is active" value={exceptionJustification} onChange={(event) => setExceptionJustification(event.target.value)} />
            <Button onClick={() => api.post(`/assessments/${assessment.id}/approve`, { decision, comments, override_recommendation: overrideRecommendation || null, override_reason: overrideReason, exception_justification: exceptionJustification }).then(setAssessment).catch((err) => setError(err.message))}>Record decision</Button>
          </div>
        </Card>
      )}
      <div className="mt-4">
        <Button variant="secondary" onClick={() => downloadPdf(assessment.id, assessment.assessment_number)}>Download executive PDF</Button>
      </div>
    </div>
  );
}
