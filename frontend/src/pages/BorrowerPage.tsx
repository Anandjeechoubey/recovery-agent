import { useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { sendMessage, getWorkflowStatus } from "../api/client";
import { useSSE } from "../hooks/useSSE";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import StageIndicator from "../components/chat/StageIndicator";
import VoiceCallPanel from "../components/chat/VoiceCallPanel";

export default function BorrowerPage() {
  const [searchParams] = useSearchParams();
  const initialId = searchParams.get("id") ?? "";

  const [borrowerId, setBorrowerId] = useState(initialId);
  const [connectedId, setConnectedId] = useState<string | null>(
    initialId || null
  );
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const {
    messages,
    currentStage,
    outcome,
    connected,
  } = useSSE(connectedId);

  const handleConnect = useCallback(async () => {
    if (!borrowerId.trim()) return;
    setConnecting(true);
    setConnectError(null);
    try {
      await getWorkflowStatus(borrowerId.trim());
      setConnectedId(borrowerId.trim());
    } catch {
      setConnectError("Workflow not found. Please check the borrower ID.");
    } finally {
      setConnecting(false);
    }
  }, [borrowerId]);

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!connectedId) return;
      try {
        await sendMessage(connectedId, message);
      } catch (err) {
        console.error("Failed to send message:", err);
      }
    },
    [connectedId]
  );

  // Entry screen
  if (!connectedId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Borrower Portal</h1>
        <p className="text-gray-500 mb-8">
          Enter your Borrower ID to connect to your collections case
        </p>
        <div className="flex gap-3 w-full max-w-md">
          <input
            type="text"
            value={borrowerId}
            onChange={(e) => setBorrowerId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleConnect()}
            placeholder="Enter Borrower ID (e.g., B001)"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleConnect}
            disabled={connecting || !borrowerId.trim()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300"
          >
            {connecting ? "Connecting..." : "Connect"}
          </button>
        </div>
        {connectError && (
          <p className="mt-3 text-red-600 text-sm">{connectError}</p>
        )}
      </div>
    );
  }

  const isVoiceStage = currentStage === "resolution";
  const isChatDisabled = isVoiceStage || outcome !== null;

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <StageIndicator currentStage={currentStage} outcome={outcome} />

      <div className="flex-1 flex flex-col bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        {/* Connection status bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b text-xs">
          <span className="text-gray-500">
            Borrower: <span className="font-mono font-semibold">{connectedId}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                connected ? "bg-green-500" : "bg-red-400"
              }`}
            />
            {connected ? "Connected" : "Reconnecting..."}
          </span>
        </div>

        {isVoiceStage ? (
          <VoiceCallPanel />
        ) : (
          <ChatWindow messages={messages} />
        )}

        <ChatInput
          onSend={handleSendMessage}
          disabled={isChatDisabled}
          placeholder={
            outcome
              ? "Conversation has ended"
              : isVoiceStage
              ? "Voice call in progress..."
              : "Type your message..."
          }
        />
      </div>
    </div>
  );
}
