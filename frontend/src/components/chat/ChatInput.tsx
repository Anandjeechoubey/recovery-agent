import { useState, useCallback } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
  placeholder?: string;
}

export default function ChatInput({ onSend, disabled, placeholder }: Props) {
  const [text, setText] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = text.trim();
      if (!trimmed || disabled) return;
      onSend(trimmed);
      setText("");
    },
    [text, disabled, onSend]
  );

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-4 bg-white border-t">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        placeholder={placeholder ?? "Type your message..."}
        className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
      >
        Send
      </button>
    </form>
  );
}
