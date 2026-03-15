import { useState, useEffect, useCallback } from "react";
import { listPrompts, getActivePrompt, rollbackPrompt } from "../api/client";
import type { PromptVersion } from "../api/types";

const AGENT_TYPES = ["assessment", "resolution", "final_notice"] as const;

const AGENT_META: Record<string, { color: string; description: string }> = {
  assessment: {
    color: "bg-blue-50 text-blue-700 border-blue-200",
    description: "Identity verification & financial discovery via chat",
  },
  resolution: {
    color: "bg-amber-50 text-amber-700 border-amber-200",
    description: "Outbound voice call negotiation & deal structuring",
  },
  final_notice: {
    color: "bg-red-50 text-red-700 border-red-200",
    description: "Hard deadline messaging & consequence escalation",
  },
};

export default function PromptsPage() {
  const [agentType, setAgentType] = useState<string>("assessment");
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [rolling, setRolling] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [v, a] = await Promise.all([
        listPrompts(agentType),
        getActivePrompt(agentType),
      ]);
      setVersions(v);
      setSelectedVersion(a.version);
    } catch {
      setVersions([]);
    } finally {
      setLoading(false);
    }
  }, [agentType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRollback = useCallback(
    async (versionId: string) => {
      setRolling(versionId);
      try {
        await rollbackPrompt(agentType, versionId);
        await fetchData();
      } finally {
        setRolling(null);
      }
    },
    [agentType, fetchData]
  );

  const selectedContent = versions.find((v) => v.version === selectedVersion)?.content;
  const meta = AGENT_META[agentType];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Prompt Management</h1>
        <p className="text-sm text-gray-500 mt-1">
          View, compare, and rollback prompt versions across all agent types
        </p>
      </div>

      {/* Agent type tabs */}
      <div className="flex gap-2 mb-6">
        {AGENT_TYPES.map((t) => {
          const isActive = agentType === t;
          return (
            <button
              key={t}
              onClick={() => setAgentType(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                isActive
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              {t.replace("_", " ")}
            </button>
          );
        })}
      </div>

      {/* Agent description */}
      {meta && (
        <div className={`mb-6 px-4 py-3 rounded-lg border ${meta.color}`}>
          <p className="text-sm font-medium capitalize">{agentType.replace("_", " ")} Agent</p>
          <p className="text-xs mt-0.5 opacity-80">{meta.description}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Version list */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-900">Versions</h2>
            </div>
            <div className="p-2">
              {loading ? (
                <p className="text-sm text-gray-400 p-3">Loading...</p>
              ) : versions.length === 0 ? (
                <p className="text-sm text-gray-400 p-3">No versions found.</p>
              ) : (
                <div className="space-y-1">
                  {versions.map((v) => {
                    const isSelected = v.version === selectedVersion;
                    return (
                      <button
                        key={v.id}
                        onClick={() => setSelectedVersion(v.version)}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-colors ${
                          isSelected
                            ? "bg-blue-50 border border-blue-200"
                            : "hover:bg-gray-50 border border-transparent"
                        }`}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-gray-900">
                              v{v.version}
                            </span>
                            {v.is_active && (
                              <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-[10px] font-semibold uppercase">
                                Active
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {v.token_count.toLocaleString()} tokens &middot;{" "}
                            {new Date(v.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        {!v.is_active && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRollback(v.id);
                            }}
                            disabled={rolling === v.id}
                            className="shrink-0 px-2.5 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded-md transition-colors disabled:opacity-50"
                          >
                            {rolling === v.id ? "Rolling..." : "Rollback"}
                          </button>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Prompt content */}
        <div className="lg:col-span-3">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900">
                Prompt Content
                {selectedVersion > 0 && (
                  <span className="ml-2 text-gray-400 font-normal">v{selectedVersion}</span>
                )}
              </h2>
              {selectedContent && (
                <span className="text-xs text-gray-400">
                  {selectedContent.length.toLocaleString()} chars
                </span>
              )}
            </div>
            <div className="p-4">
              {selectedContent ? (
                <pre className="p-4 bg-slate-900 text-green-400 rounded-lg text-xs font-mono overflow-x-auto max-h-[calc(100vh-24rem)] whitespace-pre-wrap leading-relaxed">
                  {selectedContent}
                </pre>
              ) : (
                <p className="text-sm text-gray-400 text-center py-12">
                  Select a version to view its prompt content
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
