const STAGES = [
  { key: "assessment", label: "Assessment", number: 1 },
  { key: "resolution", label: "Resolution", number: 2 },
  { key: "final_notice", label: "Final Notice", number: 3 },
];

interface Props {
  currentStage: string;
  outcome: string | null;
}

export default function StageIndicator({ currentStage, outcome }: Props) {
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);

  return (
    <div className="flex items-center justify-between mb-6 bg-white rounded-lg p-4 shadow-sm">
      {STAGES.map((stage, idx) => {
        const isActive = stage.key === currentStage;
        const isComplete = idx < currentIdx || outcome !== null;
        return (
          <div key={stage.key} className="flex items-center flex-1">
            <div className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : isComplete
                      ? "bg-green-500 text-white"
                      : "bg-gray-200 text-gray-500"
                }`}
              >
                {isComplete && !isActive ? "\u2713" : stage.number}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  isActive
                    ? "text-blue-600"
                    : isComplete
                      ? "text-green-600"
                      : "text-gray-400"
                }`}
              >
                {stage.label}
              </span>
            </div>
            {idx < STAGES.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-4 ${
                  idx < currentIdx ? "bg-green-500" : "bg-gray-200"
                }`}
              />
            )}
          </div>
        );
      })}
      {outcome && (
        <span
          className={`ml-4 px-3 py-1 rounded-full text-xs font-semibold ${
            outcome === "agreement" || outcome === "resolved"
              ? "bg-green-100 text-green-800"
              : outcome === "escalate"
                ? "bg-red-100 text-red-800"
                : "bg-yellow-100 text-yellow-800"
          }`}
        >
          {outcome.toUpperCase()}
        </span>
      )}
    </div>
  );
}
