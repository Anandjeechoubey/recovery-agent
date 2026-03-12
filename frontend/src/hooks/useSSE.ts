import { useEffect, useRef, useCallback, useState } from "react";
import { getStreamUrl } from "../api/client";
import type { ChatMessage } from "../api/types";

interface SSEState {
  messages: ChatMessage[];
  currentStage: string;
  outcome: string | null;
  connected: boolean;
}

export function useSSE(borrowerId: string | null) {
  const [state, setState] = useState<SSEState>({
    messages: [],
    currentStage: "pending",
    outcome: null,
    connected: false,
  });
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (!borrowerId) return;

    const es = new EventSource(getStreamUrl(borrowerId));
    eventSourceRef.current = es;

    es.onopen = () => {
      setState((prev) => ({ ...prev, connected: true }));
    };

    es.addEventListener("message", (e) => {
      const msg: ChatMessage = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, msg],
      }));
    });

    es.addEventListener("stage_change", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        currentStage: data.stage,
      }));
    });

    es.addEventListener("outcome", (e) => {
      const data = JSON.parse(e.data);
      setState((prev) => ({
        ...prev,
        outcome: data.outcome,
      }));
      es.close();
    });

    es.addEventListener("heartbeat", () => {
      // Keep-alive, no action needed
    });

    es.onerror = () => {
      setState((prev) => ({ ...prev, connected: false }));
      es.close();
      // Reconnect after 3s
      setTimeout(() => connect(), 3000);
    };
  }, [borrowerId]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [connect]);

  const addOptimisticMessage = useCallback((content: string, stage: string) => {
    const msg: ChatMessage = {
      role: "borrower",
      content,
      stage,
      timestamp: new Date().toISOString(),
    };
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, msg],
    }));
  }, []);

  return { ...state, addOptimisticMessage };
}
