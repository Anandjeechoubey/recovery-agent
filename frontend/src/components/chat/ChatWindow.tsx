import { useEffect, useRef } from "react";
import type { ChatMessage as ChatMessageType } from "../../api/types";
import ChatMessage from "./ChatMessage";

interface Props {
  messages: ChatMessageType[];
}

export default function ChatWindow({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const chatMessages = messages.filter((m) => m.role !== "system");

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-1 bg-gray-50">
      {chatMessages.length === 0 && (
        <div className="text-center text-gray-400 mt-20">
          Waiting for agent to connect...
        </div>
      )}
      {chatMessages.map((msg, idx) => (
        <ChatMessage key={idx} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
