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
