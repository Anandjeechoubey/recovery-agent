import { useState, useEffect, useCallback } from "react";
import { getWorkflowStatus } from "../api/client";
import type { WorkflowStatus } from "../api/types";

export function useWorkflowPolling(borrowerId: string | null, intervalMs = 5000) {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    if (!borrowerId) return;
    try {
      const s = await getWorkflowStatus(borrowerId);
      setStatus(s);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [borrowerId]);

  useEffect(() => {
    poll();
    const id = setInterval(poll, intervalMs);
    return () => clearInterval(id);
  }, [poll, intervalMs]);

  return { status, error, refresh: poll };
}
