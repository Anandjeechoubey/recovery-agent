import { useState, useEffect, useCallback } from "react";
import { listPrompts, getActivePrompt, rollbackPrompt } from "../../api/client";
import type { PromptVersion } from "../../api/types";

const AGENT_TYPES = ["assessment", "resolution", "final_notice"];

export default function PromptManager() {
  const [agentType, setAgentType] = useState("assessment");
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  // const [activePrompt, setActivePrompt] = useState<ActivePrompt | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<number>(0);
  // const [allPrompts, setAllPrompts] = useState<ActivePrompt[]>([]);
  // const [showContent, setShowContent] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [v, a] = await Promise.all([
        listPrompts(agentType),
        getActivePrompt(agentType),
      ]);
      setVersions(v);
      // setActivePrompt(a);
      setSelectedVersion(a.version);
    } catch {
      setVersions([]);
      // setActivePrompt(null);
    }
  }, [agentType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRollback = useCallback(
    async (versionId: string) => {
      await rollbackPrompt(agentType, versionId);
      fetchData();
    },
    [agentType, fetchData],
  );

  return (
    <div className="h-160 w-240">
      <div className="flex gap-2 mb-4">
        {AGENT_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => {
              setAgentType(t);
              // setShowContent(false);
            }}
            className={`px-3 py-1.5 rounded-md text-sm font-medium capitalize ${
              agentType === t
                ? "bg-gray-900 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {t.replace("_", " ")}
          </button>
        ))}
      </div>
      {versions.length === 0 ? (
        <p className="text-gray-500 text-sm">
          No prompt versions found for this agent type.
        </p>
      ) : (
        <div className="space-y-2">
          {versions.map((v) => (
            <div
              key={v.id}
              className={`flex items-center justify-between p-3 rounded-md border ${
                v.version === selectedVersion
                  ? "border-blue-300 bg-blue-50"
                  : "border-gray-200"
              }`}
            >
              <div
                className="cursor-pointer"
                onClick={() => setSelectedVersion(v.version)}
              >
                <span className="font-medium text-sm">v{v.version}</span>
                {v.is_active && (
                  <span className="ml-2 px-2 py-0.5 bg-blue-600 text-white rounded text-xs">
                    Active
                  </span>
                )}
                <span className="ml-3 text-gray-500 text-xs">
                  {v.token_count} tokens &middot;{" "}
                  {new Date(v.created_at).toLocaleDateString()}
                </span>
              </div>
              {!v.is_active && (
                <button
                  onClick={() => handleRollback(v.id)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Rollback
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      {versions.find((v) => v.version === selectedVersion) && (
        <div className="mt-4">
          {/* <button
            onClick={() => setShowContent(!showContent)}
            className="text-sm text-blue-600 hover:underline"
          >
            {showContent ? "Hide" : "View"} Active Prompt Content
          </button> */}
          {true && (
            <pre className="mt-2 p-4 bg-gray-900 text-green-400 rounded-md text-xs overflow-x-auto max-h-96">
              {versions.find((v) => v.version === selectedVersion)?.content}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
