interface Props {
  phoneNumber?: string;
}

export default function VoiceCallPanel({ phoneNumber }: Props) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-gray-50 p-8">
      {/* Pulsing phone icon */}
      <div className="relative mb-8">
        <div className="absolute inset-0 bg-blue-400 rounded-full animate-ping opacity-20" />
        <div className="relative w-24 h-24 bg-blue-600 rounded-full flex items-center justify-center">
          <svg
            className="w-12 h-12 text-white"
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

      <h2 className="text-xl font-semibold text-gray-900 mb-2">
        Incoming Phone Call
      </h2>
      <p className="text-gray-600 text-center max-w-md mb-4">
        You are about to receive a phone call from our Resolution team.
        Please answer when your phone rings.
      </p>
      {phoneNumber && (
        <p className="text-gray-500 text-sm">
          Call will be placed to: <span className="font-mono font-semibold">{phoneNumber}</span>
        </p>
      )}
      <div className="mt-6 flex items-center gap-2 text-blue-600">
        <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
        <span className="text-sm font-medium">Call in progress...</span>
      </div>
    </div>
  );
}
