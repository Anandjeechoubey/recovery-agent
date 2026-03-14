import { useEffect, useState } from "react";
import {
  getEvolutionReport,
  // getIteration
} from "../api/client";
import type {
  AgentIterationData,
  Comparison,
  CostSummary,
  EvolutionReport,
  IterationDetail,
  MetaFinding,
} from "../api/types";

const AGENT_TYPES = ["assessment", "resolution", "final_notice"] as const;

const ACTION_COLORS: Record<string, string> = {
  adopted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  no_change: "bg-gray-100 text-gray-600",
  error: "bg-orange-100 text-orange-800",
};

function Badge({ action }: { action: string }) {
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${ACTION_COLORS[action] ?? "bg-gray-100 text-gray-600"}`}
    >
      {action.replace("_", " ")}
    </span>
  );
}

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

/* ── Cost Breakdown ─────────────────────────────────────── */
function CostBreakdown({ cost }: { cost: CostSummary }) {
  const total = cost.total_usd || 1;
  const cats = Object.entries(cost.by_category).sort((a, b) => b[1] - a[1]);
  const maxCat = cats[0]?.[1] || 1;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">
        Cost Breakdown
      </h3>
      <div className="space-y-2">
        {cats.map(([cat, cost_val]) => (
          <div key={cat}>
            <div className="flex justify-between text-xs mb-0.5">
              <span className="text-gray-600">{cat.replaceAll("_", " ")}</span>
              <span className="text-gray-900 font-medium">
                ${cost_val.toFixed(4)} ({((cost_val / total) * 100).toFixed(1)}
                %)
              </span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full"
                style={{ width: `${(cost_val / maxCat) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-3 border-t border-gray-100">
        <h4 className="text-xs font-semibold text-gray-700 mb-2">
          Token Usage
        </h4>
        {Object.entries(cost.by_model).map(([model, tokens]) => (
          <div
            key={model}
            className="flex justify-between text-xs text-gray-500"
          >
            <span>{model}</span>
            <span>
              {tokens.input_tokens.toLocaleString()} in /{" "}
              {tokens.output_tokens.toLocaleString()} out
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Metrics Table ──────────────────────────────────────── */
function MetricsTable({
  agent,
  // agentType,
}: {
  agent: AgentIterationData;
  agentType: string;
}) {
  const hasCandidate =
    agent.candidate_metrics &&
    agent.action !== "no_change" &&
    agent.action !== "error";
  const compMap: Record<string, Comparison> = {};
  (agent.comparisons ?? []).forEach((c) => (compMap[c.metric] = c));

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-100">
            <th className="py-2 pr-3 font-medium">Metric</th>
            <th className="py-2 pr-3 font-medium">Baseline</th>
            {hasCandidate && (
              <>
                <th className="py-2 pr-3 font-medium">Candidate</th>
                <th className="py-2 pr-3 font-medium">Effect</th>
                <th className="py-2 pr-3 font-medium">p-value</th>
                <th className="py-2 font-medium">Sig?</th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {Object.entries(agent.baseline_metrics).map(([metric, baseline]) => {
            const cand = agent.candidate_metrics?.[metric];
            const comp = compMap[metric];
            return (
              <tr key={metric} className="border-b border-gray-50">
                <td className="py-2 pr-3 font-medium text-gray-700">
                  {metric.replaceAll("_", " ")}
                </td>
                <td className="py-2 pr-3 text-gray-900">
                  {baseline.mean.toFixed(2)}{" "}
                  <span className="text-gray-400">
                    ±{baseline.std.toFixed(2)}
                  </span>
                </td>
                {hasCandidate && (
                  <>
                    <td className="py-2 pr-3 text-gray-900">
                      {cand
                        ? `${cand.mean.toFixed(2)} ±${cand.std.toFixed(2)}`
                        : "—"}
                    </td>
                    <td
                      className={`py-2 pr-3 font-mono ${comp && comp.effect_size > 0 ? "text-green-600" : comp && comp.effect_size < 0 ? "text-red-600" : "text-gray-500"}`}
                    >
                      {comp
                        ? `${comp.effect_size > 0 ? "+" : ""}${comp.effect_size.toFixed(3)}`
                        : "—"}
                    </td>
                    <td className="py-2 pr-3 font-mono text-gray-600">
                      {comp ? comp.p_value.toFixed(4) : "—"}
                    </td>
                    <td className="py-2">
                      {comp?.significant ? (
                        <span className="text-green-600 font-bold">Yes</span>
                      ) : (
                        <span className="text-gray-400">No</span>
                      )}
                    </td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ── Per-Conversation Scores ─────────────────────────────── */
function ScoreDistribution({
  label,
  metrics,
}: {
  label: string;
  metrics: Record<string, { mean: number; per_conversation: number[] }>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-blue-600 hover:text-blue-800"
      >
        {open ? "Hide" : "Show"} {label} per-conversation scores
      </button>
      {open && (
        <div className="mt-2 bg-gray-50 rounded p-3 text-xs space-y-1.5">
          {Object.entries(metrics).map(([name, data]) => (
            <div key={name}>
              <span className="font-medium text-gray-700">
                {name.replaceAll("_", " ")}:
              </span>{" "}
              <span className="font-mono text-gray-600">
                [{data.per_conversation.map((s) => s.toFixed(1)).join(", ")}]
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Agent Card (one per agent per iteration) ────────────── */
function AgentCard({
  agentType,
  agent,
}: {
  agentType: string;
  agent: AgentIterationData;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-900 capitalize">
          {agentType.replaceAll("_", " ")}
        </h4>
        <Badge action={agent.action} />
      </div>

      {agent.change_description && (
        <p className="text-xs text-gray-500 italic mb-3 border-l-2 border-blue-200 pl-2">
          {agent.change_description}
        </p>
      )}

      {agent.error && (
        <p className="text-xs text-orange-700 bg-orange-50 p-2 rounded mb-3">
          {agent.error}
        </p>
      )}

      {agent.baseline_metrics &&
        Object.keys(agent.baseline_metrics).length > 0 && (
          <>
            <MetricsTable agent={agent} agentType={agentType} />

            <div className="mt-3 flex gap-4 text-xs text-gray-500">
              <span>
                Weighted:{" "}
                <span className="text-gray-900 font-medium">
                  {agent.baseline_weighted_score.toFixed(3)}
                </span>
                {agent.candidate_weighted_score != null &&
                  agent.action !== "no_change" && (
                    <>
                      {" → "}
                      <span className="text-gray-900 font-medium">
                        {agent.candidate_weighted_score.toFixed(3)}
                      </span>
                      <span
                        className={
                          agent.candidate_weighted_score >
                          agent.baseline_weighted_score
                            ? "text-green-600"
                            : "text-red-600"
                        }
                      >
                        {" ("}
                        {agent.candidate_weighted_score -
                          agent.baseline_weighted_score >
                        0
                          ? "+"
                          : ""}
                        {(
                          agent.candidate_weighted_score -
                          agent.baseline_weighted_score
                        ).toFixed(3)}
                        {")"}
                      </span>
                    </>
                  )}
              </span>
              {agent.compliance_baseline != null && (
                <span>
                  Compliance:{" "}
                  <span className="text-gray-900 font-medium">
                    {(agent.compliance_baseline * 100).toFixed(0)}%
                  </span>
                  {agent.compliance_candidate != null &&
                    agent.action !== "no_change" && (
                      <>
                        {" → "}
                        {(agent.compliance_candidate * 100).toFixed(0)}%
                      </>
                    )}
                </span>
              )}
            </div>

            <ScoreDistribution
              label="baseline"
              metrics={agent.baseline_metrics}
            />
            {agent.candidate_metrics && agent.action !== "no_change" && (
              <ScoreDistribution
                label="candidate"
                metrics={agent.candidate_metrics}
              />
            )}
          </>
        )}

      {agent.reason && (
        <p className="mt-2 text-xs text-gray-500">
          <span className="font-medium">Reason:</span> {agent.reason}
        </p>
      )}
    </div>
  );
}

/* ── Meta-Evaluation Findings ─────────────────────────────── */
function MetaFindings({ findings }: { findings: MetaFinding[] }) {
  if (!findings.length) return null;
  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-purple-900 mb-2">
        Meta-Evaluation Findings
      </h4>
      <div className="space-y-2">
        {findings.map((f, i) => (
          <div key={i} className="text-xs">
            <span className="font-medium text-purple-800 uppercase">
              [{f.check_type}]
            </span>{" "}
            <span className="text-gray-700">{f.description}</span>
            <p className="text-gray-500 mt-0.5 ml-4">
              Action: {f.action_taken}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Iteration Panel ─────────────────────────────────────── */
function IterationPanel({ iteration }: { iteration: IterationDetail }) {
  const [expanded, setExpanded] = useState(false);

  const agentSummary = AGENT_TYPES.map((at) => {
    const a = iteration.agents[at];
    return a ? a.action : "—";
  });

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-gray-900">
            Iteration {iteration.iteration}
          </span>
          <div className="flex gap-1.5">
            {AGENT_TYPES.map((at, i) => (
              <Badge key={at} action={agentSummary[i]} />
            ))}
          </div>
          {iteration.errors.length > 0 && (
            <span className="text-xs text-orange-600">
              ({iteration.errors.length} error
              {iteration.errors.length > 1 ? "s" : ""})
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>${iteration.cost_this_iteration.toFixed(4)}</span>
          <span className="text-gray-300">|</span>
          <span>cumulative: ${iteration.cost_cumulative.toFixed(4)}</span>
          <svg
            className={`w-4 h-4 transition-transform ${expanded ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 bg-gray-50 space-y-4">
          {iteration.prompt_versions_at_start && (
            <p className="text-xs text-gray-500 pt-2">
              Prompt versions at start:{" "}
              {Object.entries(iteration.prompt_versions_at_start)
                .map(([k, v]) => `${k}: v${v}`)
                .join(", ")}
            </p>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {AGENT_TYPES.map((at) => {
              const agent = iteration.agents[at];
              return agent ? (
                <AgentCard key={at} agentType={at} agent={agent} />
              ) : null;
            })}
          </div>

          <MetaFindings findings={iteration.meta_evaluation?.findings ?? []} />

          {iteration.meta_evaluation?.current_thresholds && (
            <p className="text-xs text-gray-500">
              Active thresholds: p=
              {iteration.meta_evaluation.current_thresholds.p_value_threshold},
              min_effect=
              {iteration.meta_evaluation.current_thresholds.min_effect_size}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Metrics Across Versions Chart ──────────────────────── */
function MetricsTimeline({ iterations }: { iterations: IterationDetail[] }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-4">
        Metrics Across Iterations
      </h3>
      {AGENT_TYPES.map((at) => {
        const metricNames = new Set<string>();
        iterations.forEach((it) => {
          const bm = it.agents[at]?.baseline_metrics;
          if (bm) Object.keys(bm).forEach((k) => metricNames.add(k));
        });

        if (!metricNames.size) return null;

        return (
          <div key={at} className="mb-5">
            <h4 className="text-xs font-semibold text-gray-700 capitalize mb-2">
              {at.replaceAll("_", " ")}
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b border-gray-100">
                    <th className="py-1.5 pr-3 font-medium">Iter</th>
                    {[...metricNames].sort().map((m) => (
                      <th key={m} className="py-1.5 pr-3 font-medium">
                        {m.replaceAll("_", " ")}
                      </th>
                    ))}
                    <th className="py-1.5 font-medium">Weighted</th>
                  </tr>
                </thead>
                <tbody>
                  {iterations.map((it) => {
                    const agent = it.agents[at];
                    if (!agent) return null;
                    const bm = agent.baseline_metrics ?? {};
                    return (
                      <tr
                        key={it.iteration}
                        className="border-b border-gray-50"
                      >
                        <td className="py-1.5 pr-3 font-medium text-gray-700">
                          {it.iteration}
                        </td>
                        {[...metricNames].sort().map((m) => {
                          const md = bm[m];
                          return (
                            <td
                              key={m}
                              className="py-1.5 pr-3 font-mono text-gray-600"
                            >
                              {md
                                ? `${md.mean.toFixed(2)} ±${md.std.toFixed(2)}`
                                : "—"}
                            </td>
                          );
                        })}
                        <td className="py-1.5 font-mono font-medium text-gray-900">
                          {agent.baseline_weighted_score?.toFixed(3) ?? "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Prompt Version Timeline ─────────────────────────────── */
function PromptTimeline({
  timeline,
}: {
  timeline: Record<string, Array<Record<string, unknown>>>;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">
        Prompt Version Timeline
      </h3>
      {AGENT_TYPES.map((at) => {
        const entries = timeline[at];
        if (!entries?.length) return null;
        return (
          <div key={at} className="mb-4">
            <h4 className="text-xs font-semibold text-gray-700 capitalize mb-2">
              {at.replaceAll("_", " ")}
            </h4>
            <div className="space-y-1">
              {entries.map((e, i) => (
                <div key={i} className="flex items-center gap-3 text-xs">
                  <span className="text-gray-400 w-12">
                    Iter {String(e.iteration)}
                  </span>
                  <span className="font-medium text-gray-700">
                    v{String(e.version)}
                  </span>
                  <span className="text-gray-500">
                    {String(e.token_count)} tokens
                  </span>
                  <Badge action={String(e.event)} />
                  {e.change_description ? (
                    <span className="text-gray-400 truncate max-w-xs">
                      {String(e.change_description)}
                    </span>
                  ) : (
                    <></>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────── */
export default function LearningLoopPage() {
  const [report, setReport] = useState<EvolutionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    getEvolutionReport()
      .then((data) => {
        if ("error" in data) {
          setError(String((data as Record<string, unknown>).error));
        } else {
          setReport(data);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading evolution report...</div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-gray-500 text-lg mb-2">
            {error || "No evolution data found"}
          </p>
          <p className="text-gray-400 text-sm">
            Run the learning loop first:{" "}
            <code className="bg-gray-100 px-2 py-0.5 rounded">
              python -m src.learning.loop
            </code>
          </p>
        </div>
      </div>
    );
  }

  const cost = report.cost_summary;
  const iterations = report.iterations;

  // Count adoptions/rejections across all iterations
  let adoptions = 0;
  let rejections = 0;
  let metaFindings = 0;
  for (const it of iterations) {
    for (const agent of Object.values(it.agents)) {
      if (agent.action === "adopted") adoptions++;
      else if (agent.action === "rejected") rejections++;
    }
    metaFindings += it.meta_evaluation?.findings?.length ?? 0;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Self-Learning Loop
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Evolution report &amp; metrics visualization
          </p>
        </div>
        <div className="text-xs text-gray-400">
          {report.run_config?.timestamp
            ? new Date(String(report.run_config.timestamp)).toLocaleString()
            : ""}
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <StatCard label="Iterations" value={String(iterations.length)} />
        <StatCard
          label="Total Cost"
          value={`$${cost.total_usd.toFixed(2)}`}
          sub={`of $${cost.budget_usd.toFixed(0)} budget`}
        />
        <StatCard
          label="Adoptions"
          value={String(adoptions)}
          sub={`of ${adoptions + rejections} proposals`}
        />
        <StatCard label="Rejections" value={String(rejections)} />
        <StatCard label="Meta Findings" value={String(metaFindings)} />
        <StatCard
          label="Budget Used"
          value={`${((cost.total_usd / cost.budget_usd) * 100).toFixed(1)}%`}
        />
      </div>

      {/* Cost Breakdown + Prompt Timeline side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CostBreakdown cost={cost} />
        <PromptTimeline timeline={report.prompt_version_timeline} />
      </div>

      {/* Metrics across iterations */}
      <MetricsTimeline iterations={iterations} />

      {/* Per-iteration detail (accordion) */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-3">
          Iteration Details
        </h2>
        <div className="space-y-2">
          {iterations.map((it) => (
            <IterationPanel key={it.iteration} iteration={it} />
          ))}
        </div>
      </div>
    </div>
  );
}
