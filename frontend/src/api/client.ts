import type {
  ActivePrompt,
  BorrowerWorkflow,
  PromptVersion,
  StartWorkflowRequest,
  WorkflowStatus,
} from "./types";

const API_BASE = "/api";
const TOKEN_KEY = "recoverai_token";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json();
}

// Workflow
export const startWorkflow = (data: StartWorkflowRequest) =>
  request<{ workflow_id: string; run_id: string }>("/workflow/start", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const listWorkflows = () =>
  request<BorrowerWorkflow[]>("/workflow/list");

export const getWorkflowStatus = (borrowerId: string) =>
  request<WorkflowStatus>(`/workflow/${borrowerId}/status`);

export const cancelWorkflow = (borrowerId: string) =>
  request<{ status: string }>(`/workflow/${borrowerId}/cancel`, {
    method: "POST",
  });

// Chat
export const sendMessage = (borrowerId: string, message: string) =>
  request<{ status: string; current_stage: string }>(`/chat/${borrowerId}`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });

export const getChatHistory = (borrowerId: string) =>
  request<WorkflowStatus>(`/chat/${borrowerId}/history`);

// SSE stream URL
export const getStreamUrl = (borrowerId: string) =>
  `${API_BASE}/chat/${borrowerId}/stream`;

// Prompts
export const listPrompts = (agentType: string) =>
  request<PromptVersion[]>(`/admin/prompts/${agentType}`);

export const getActivePrompt = (agentType: string) =>
  request<ActivePrompt>(`/admin/prompts/${agentType}/active`);

export const rollbackPrompt = (agentType: string, versionId: string) =>
  request<{ status: string }>(`/admin/prompts/${agentType}/rollback/${versionId}`, {
    method: "POST",
  });
