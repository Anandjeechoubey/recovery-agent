import type { ChatMessage as ChatMessageType } from "../../api/types";

interface Props {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: Props) {
  const isAgent = message.role === "agent";
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={`flex ${isAgent ? "justify-start" : "justify-end"} mb-3`}>
      <div
        className={`max-w-[75%] rounded-lg px-4 py-2 ${
          isAgent
            ? "bg-gray-800 text-white rounded-bl-none"
            : "bg-blue-600 text-white rounded-br-none"
        }`}
      >
        <div className="text-xs opacity-70 mb-1">
          {isAgent ? "Agent" : "You"} &middot; {time}
        </div>
        <div className="text-sm whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  );
}
