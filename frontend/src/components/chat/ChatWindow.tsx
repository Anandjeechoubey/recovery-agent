import { useEffect, useRef } from "react";
import type { ChatMessage as ChatMessageType } from "../../api/types";
import ChatMessage from "./ChatMessage";
import VoiceCallPanel from "./VoiceCallPanel";

interface Props {
  messages: ChatMessageType[];
  voiceCall?: {
    active: boolean;
    callEnded: boolean;
    phoneNumber?: string;
  };
}

export default function ChatWindow({ messages, voiceCall }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, voiceCall?.active, voiceCall?.callEnded]);

  const chatMessages = messages.filter((m) => m.role !== "system");

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-1 bg-gray-50">
      {chatMessages.length === 0 && !voiceCall?.active && (
        <div className="text-center text-gray-400 mt-20">
          Waiting for agent to connect...
        </div>
      )}
      {chatMessages.map((msg, idx) => (
        <ChatMessage key={idx} message={msg} />
      ))}
      {voiceCall?.active && (
        <VoiceCallPanel
          callEnded={voiceCall.callEnded}
          phoneNumber={voiceCall.phoneNumber}
        />
      )}
      <div ref={bottomRef} />
    </div>
  );
}
