interface Props {
  phoneNumber?: string;
  callEnded?: boolean;
}

export default function VoiceCallPanel({ phoneNumber, callEnded }: Props) {
  return (
    <div className="mx-4 my-3 rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex items-center gap-4">
        {/* Phone icon */}
        <div className="relative flex-shrink-0">
          {!callEnded && (
            <div className="absolute inset-0 bg-blue-400 rounded-full animate-ping opacity-20" />
          )}
          <div
            className={`relative w-12 h-12 rounded-full flex items-center justify-center ${
              callEnded ? "bg-gray-400" : "bg-blue-600"
            }`}
          >
            <svg
              className="w-6 h-6 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
              />
            </svg>
          </div>
        </div>

        <div className="flex-1">
          <h3 className="text-sm font-semibold text-gray-900">
            {callEnded ? "Phone Call Ended" : "Phone Call In Progress"}
          </h3>
          <p className="text-xs text-gray-600 mt-0.5">
            {callEnded
              ? "Call ended. Processing results..."
              : "You are receiving a call from our Resolution team. Please answer your phone."}
          </p>
          {phoneNumber && !callEnded && (
            <p className="text-xs text-gray-500 mt-1">
              Calling: <span className="font-mono font-semibold">{phoneNumber}</span>
            </p>
          )}
        </div>

        {/* Status indicator */}
        <div className="flex-shrink-0 flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full ${
              callEnded ? "bg-gray-400" : "bg-blue-600 animate-pulse"
            }`}
          />
          <span
            className={`text-xs font-medium ${
              callEnded ? "text-gray-500" : "text-blue-600"
            }`}
          >
            {callEnded ? "Processing..." : "Live"}
          </span>
        </div>
      </div>
    </div>
  );
}
