export interface BorrowerWorkflow {
  borrower_id: string;
  name: string;
  total_debt: number;
  debt_type: string;
  days_past_due: number;
  phone_number: string;
  email: string;
  started_at: string;
  current_stage: string;
  outcome: string;
  attempt?: number;
}

export interface StartWorkflowRequest {
  borrower_id: string;
  name: string;
  account_last4: string;
  total_debt: number;
  debt_type: string;
  days_past_due: number;
  phone_number: string;
  email: string;
}

export interface ChatMessage {
  role: "agent" | "borrower" | "system";
  content: string;
  stage: string;
  timestamp: string;
}

export interface WorkflowStatus {
  current_stage: string;
  outcome: string;
  attempt: number;
  messages?: ChatMessage[];
}

export interface PromptVersion {
  id: string;
  version: number;
  is_active: boolean;
  token_count: number;
  created_at: string;
  content: string;
}

export interface ActivePrompt {
  id: string;
  version: number;
  content: string;
  token_count: number;
  evaluation_data: Record<string, unknown>;
}

// Learning loop types
export interface IterationSummary {
  iteration: number;
  timestamp: string;
  cost_this_iteration: number;
  cost_cumulative: number;
  agents: Record<
    string,
    {
      action: string;
      baseline_weighted_score: number;
      candidate_weighted_score: number;
    }
  >;
  meta_findings_count: number;
  errors: string[];
}

export interface MetricDetail {
  mean: number;
  std: number;
  min: number;
  max: number;
  n: number;
  per_conversation: number[];
}

export interface Comparison {
  metric: string;
  baseline_mean: number;
  candidate_mean: number;
  effect_size: number;
  p_value: number;
  ci_lower: number;
  ci_upper: number;
  significant: boolean;
  recommendation: string;
}

export interface AgentIterationData {
  action: string;
  change_description?: string;
  baseline_weighted_score: number;
  candidate_weighted_score?: number;
  baseline_metrics: Record<string, MetricDetail>;
  candidate_metrics?: Record<string, MetricDetail>;
  comparisons?: Comparison[];
  reason?: string;
  compliance_baseline?: number;
  compliance_candidate?: number;
  error?: string;
}

export interface MetaFinding {
  check_type: string;
  description: string;
  action_taken: string;
  evidence?: Record<string, unknown>;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
}

export interface IterationDetail {
  iteration: number;
  timestamp: string;
  prompt_versions_at_start?: Record<string, number>;
  agents: Record<string, AgentIterationData>;
  meta_evaluation: {
    findings: MetaFinding[];
    current_thresholds?: {
      p_value_threshold: number;
      min_effect_size: number;
    };
  };
  cost_cumulative: number;
  cost_this_iteration: number;
  errors: string[];
}

export interface CostSummary {
  total_usd: number;
  budget_usd: number;
  by_category: Record<string, number>;
  by_model: Record<string, { input_tokens: number; output_tokens: number }>;
}

export interface EvolutionReport {
  run_config: Record<string, unknown>;
  iterations: IterationDetail[];
  prompt_version_timeline: Record<string, Array<Record<string, unknown>>>;
  cost_summary: CostSummary;
}
