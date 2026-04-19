import {
  Brain,
  Shield,
  Workflow,
  Database,
  Github,
  ExternalLink,
} from "lucide-react";
import { Card, CardHeader, CardBody } from "../components/ui/Card.jsx";

const STAGES = [
  {
    step: 1,
    title: "Triage",
    description: "LLM classifies category, urgency, social-engineering signals.",
  },
  {
    step: 2,
    title: "Plan",
    description: "Resolver reasons about required tools via ReAct loop.",
  },
  {
    step: 3,
    title: "Act",
    description: "Guardrail + resilience wrap every tool call; retries with backoff.",
  },
  {
    step: 4,
    title: "Synthesize",
    description: "Structured Resolution produced with confidence calibration.",
  },
  {
    step: 5,
    title: "Audit",
    description: "JSONL + SQLite capture every step for replay.",
  },
];

const TECH = [
  { name: "FastAPI", category: "Backend" },
  { name: "OpenAI tool-calls", category: "LLM" },
  { name: "Pydantic v2", category: "Validation" },
  { name: "aiosqlite", category: "Audit DB" },
  { name: "asyncio", category: "Concurrency" },
  { name: "React 18 + Vite", category: "Frontend" },
  { name: "Tailwind CSS v3", category: "Styling" },
  { name: "TanStack Query", category: "Data" },
  { name: "Recharts", category: "Charts" },
  { name: "Zustand", category: "State" },
  { name: "SSE (EventSource)", category: "Live" },
  { name: "Lucide", category: "Icons" },
];

const DECISIONS = [
  "Strict type contract between triage, resolver, and synthesis — Pydantic v2 frozen models.",
  "Tool-call loop guard: canonical-JSON cache prevents pathological repetition burning the step budget.",
  "Chaos injection (timeout + malformed) calibrated for demo — exercises the fault-tolerance path without dominating outcomes.",
  "Confidence calibration blends LLM self-report with tool-success ratio and guardrail events.",
  "Irreversible action guard: issue_refund always gated by check_refund_eligibility.",
  "Escalate — not fail — when the step budget is exceeded; failure is system-level, escalation is logical.",
];

export function About() {
  return (
    <div className="space-y-5 max-w-5xl">
      <div>
        <h1 className="text-2xl font-semibold text-text tracking-tight">
          About Sentinel
        </h1>
        <p className="text-sm text-text-muted mt-1 max-w-2xl">
          Autonomous support ticket resolver built on a ReAct loop with
          deterministic guardrails, a chaos-tolerant tool layer, and a full
          queryable audit trail.
        </p>
      </div>

      <Card>
        <CardHeader
          title="Pipeline"
          subtitle="Every ticket flows through five stages"
          right={<Workflow className="w-4 h-4 text-text-muted" />}
        />
        <CardBody>
          <ol className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {STAGES.map((s) => (
              <li
                key={s.step}
                className="bg-surface-2 border border-border rounded-lg p-4"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-5 h-5 rounded-full bg-accent/10 border border-accent/30 text-accent text-[10px] font-mono flex items-center justify-center">
                    {s.step}
                  </span>
                  <h4 className="text-sm font-medium text-text">{s.title}</h4>
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  {s.description}
                </p>
              </li>
            ))}
          </ol>
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader
            title="Design Decisions"
            subtitle="What was chosen and why"
            right={<Brain className="w-4 h-4 text-text-muted" />}
          />
          <CardBody>
            <ul className="space-y-2.5">
              {DECISIONS.map((d, i) => (
                <li key={i} className="flex gap-2">
                  <span className="w-1 h-1 rounded-full bg-accent mt-2 shrink-0" />
                  <span className="text-sm text-text-dim leading-relaxed">
                    {d}
                  </span>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Tech Stack"
            subtitle="Every dependency visible to judges"
            right={<Database className="w-4 h-4 text-text-muted" />}
          />
          <CardBody>
            <div className="grid grid-cols-2 gap-2">
              {TECH.map((t) => (
                <div
                  key={t.name}
                  className="flex items-center justify-between bg-surface-2 border border-border rounded-md px-2.5 py-1.5"
                >
                  <span className="text-xs text-text">{t.name}</span>
                  <span className="text-[10px] uppercase tracking-wider text-text-muted">
                    {t.category}
                  </span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardBody>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-md bg-accent flex items-center justify-center">
                <Shield className="w-4 h-4 text-black" strokeWidth={2.5} />
              </div>
              <div>
                <div className="text-sm text-text font-medium">
                  Sentinel
                </div>
                <div className="text-xs text-text-muted">
                  Built for Ksolves Agentic AI Hackathon 2026
                </div>
              </div>
            </div>
            <a
              href="https://github.com/"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-text-dim hover:text-text transition-colors"
            >
              <Github className="w-3.5 h-3.5" />
              GitHub
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
