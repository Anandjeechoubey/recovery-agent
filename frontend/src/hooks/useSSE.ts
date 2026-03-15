import { useEffect, useRef, useCallback, useState } from "react";
import { getChatHistory, getStreamUrl } from "../api/client";
import type { ChatMessage } from "../api/types";

interface SSEState {
  messages: ChatMessage[];
  currentStage: string;
  outcome: string | null;
  connected: boolean;
  historyLoaded: boolean;
}

export function useSSE(borrowerId: string | null) {
  const [state, setState] = useState<SSEState>({
    messages: [],
    currentStage: "pending",
    outcome: null,
    connected: false,
    historyLoaded: false,
  });
  const eventSourceRef = useRef<EventSource | null>(null);
  const historyLoadedRef = useRef(false);

  // Load chat history from DB on first connect
  useEffect(() => {
    if (!borrowerId || historyLoadedRef.current) return;

    let cancelled = false;
    (async () => {
      try {
        const history = await getChatHistory(borrowerId);
        if (cancelled) return;

        const historyMessages: ChatMessage[] = (history.messages ?? []).filter(
          (m: ChatMessage) => m.role !== "system"
        );

        setState((prev) => ({
          ...prev,
          messages: historyMessages,
          currentStage: history.current_stage ?? prev.currentStage,
          outcome: history.outcome && history.outcome !== "pending" ? history.outcome : prev.outcome,
          historyLoaded: true,
        }));
        historyLoadedRef.current = true;
      } catch {
        // History load failed (e.g. no workflow yet), proceed with SSE only
        setState((prev) => ({ ...prev, historyLoaded: true }));
        historyLoadedRef.current = true;
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [borrowerId]);

  const connect = useCallback(() => {
    if (!borrowerId) return;

    const es = new EventSource(getStreamUrl(borrowerId));
    eventSourceRef.current = es;

    es.onopen = () => {
      setState((prev) => ({ ...prev, connected: true }));
    };

    es.addEventListener("message", (e) => {
      const msg: ChatMessage = JSON.parse(e.data);
      setState((prev) => {
        // Deduplicate: skip if the last message has the same content, role, and close timestamp
        const last = prev.messages[prev.messages.length - 1];
        if (
          last &&
          last.role === msg.role &&
          last.content === msg.content &&
          last.stage === msg.stage
        ) {
          return prev;
        }
        return {
          ...prev,
          messages: [...prev.messages, msg],
        };
      });
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
