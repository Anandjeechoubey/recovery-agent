import { useEffect, useState, useCallback, useMemo } from "react";
import { listWorkflows, deleteBorrower } from "../../api/client";
import type { BorrowerWorkflow } from "../../api/types";

const STAGE_COLORS: Record<string, string> = {
  assessment: "bg-blue-100 text-blue-800",
  resolution: "bg-yellow-100 text-yellow-800",
  final_notice: "bg-red-100 text-red-800",
  pending: "bg-gray-100 text-gray-600",
  unknown: "bg-gray-100 text-gray-600",
};

const OUTCOME_COLORS: Record<string, string> = {
  agreement: "bg-green-100 text-green-800",
  resolved: "bg-green-100 text-green-800",
  escalate: "bg-red-100 text-red-800",
  no_response: "bg-yellow-100 text-yellow-800",
  pending: "bg-gray-100 text-gray-600",
};

type SortKey = "name" | "total_debt" | "days_past_due" | "current_stage" | "outcome";
type SortDir = "asc" | "desc";

interface Props {
  refreshTrigger: number;
  onSelectBorrower?: (id: string) => void;
}

export default function BorrowerTable({ refreshTrigger, onSelectBorrower }: Props) {
  const [borrowers, setBorrowers] = useState<BorrowerWorkflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Search, filter, sort state
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [outcomeFilter, setOutcomeFilter] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const fetchBorrowers = useCallback(async () => {
    try {
      const data = await listWorkflows();
      setBorrowers(data);
    } catch {
      // API might not be ready yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBorrowers();
    const interval = setInterval(fetchBorrowers, 10000);
    return () => clearInterval(interval);
  }, [fetchBorrowers, refreshTrigger]);

  const handleDelete = useCallback(
    async (e: React.MouseEvent, borrowerId: string) => {
      e.stopPropagation();
      if (!confirm("Delete this borrower and all their data?")) return;
      setDeletingId(borrowerId);
      try {
        await deleteBorrower(borrowerId);
        setBorrowers((prev) => prev.filter((b) => b.borrower_id !== borrowerId));
      } catch {
        alert("Failed to delete borrower");
      } finally {
        setDeletingId(null);
      }
    },
    []
  );

  // Unique values for filter dropdowns
  const stages = useMemo(
    () => [...new Set(borrowers.map((b) => b.current_stage))].sort(),
    [borrowers]
  );
  const outcomes = useMemo(
    () => [...new Set(borrowers.map((b) => b.outcome))].sort(),
    [borrowers]
  );

  // Filtered & sorted data
  const filtered = useMemo(() => {
    let result = borrowers;

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (b) =>
          b.name.toLowerCase().includes(q) ||
          b.borrower_id.toLowerCase().includes(q) ||
          b.debt_type.toLowerCase().includes(q) ||
          b.email?.toLowerCase().includes(q)
      );
    }

    if (stageFilter !== "all") {
      result = result.filter((b) => b.current_stage === stageFilter);
    }
    if (outcomeFilter !== "all") {
      result = result.filter((b) => b.outcome === outcomeFilter);
    }

    const sorted = [...result].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "total_debt" || sortKey === "days_past_due") {
        cmp = (a[sortKey] ?? 0) - (b[sortKey] ?? 0);
      } else {
        cmp = (a[sortKey] ?? "").localeCompare(b[sortKey] ?? "");
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return sorted;
  }, [borrowers, search, stageFilter, outcomeFilter, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function SortIcon({ column }: { column: SortKey }) {
    if (sortKey !== column) return <span className="text-gray-300 ml-1">&uarr;&darr;</span>;
    return <span className="text-blue-500 ml-1">{sortDir === "asc" ? "\u2191" : "\u2193"}</span>;
  }

  if (loading) {
    return <div className="text-gray-500 text-sm p-4">Loading borrowers...</div>;
  }

  if (borrowers.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg">No borrowers yet</p>
        <p className="text-sm mt-1">Add a borrower to start a collections workflow</p>
      </div>
    );
  }

  return (
    <div>
      {/* Search & Filter bar */}
      <div className="px-5 py-3 border-b border-gray-100 flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            type="text"
            placeholder="Search by name, ID, type, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Stage filter */}
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="all">All Stages</option>
          {stages.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>

        {/* Outcome filter */}
        <select
          value={outcomeFilter}
          onChange={(e) => setOutcomeFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          <option value="all">All Outcomes</option>
          {outcomes.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>

        {/* Result count */}
        <span className="text-xs text-gray-400">
          {filtered.length} of {borrowers.length}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th
                className="text-left py-3 px-4 font-medium text-gray-600 cursor-pointer select-none hover:text-gray-900"
                onClick={() => toggleSort("name")}
              >
                Name <SortIcon column="name" />
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-600">ID</th>
              <th
                className="text-right py-3 px-4 font-medium text-gray-600 cursor-pointer select-none hover:text-gray-900"
                onClick={() => toggleSort("total_debt")}
              >
                Total Debt <SortIcon column="total_debt" />
              </th>
              <th className="text-left py-3 px-4 font-medium text-gray-600">Type</th>
              <th
                className="text-center py-3 px-4 font-medium text-gray-600 cursor-pointer select-none hover:text-gray-900"
                onClick={() => toggleSort("current_stage")}
              >
                Stage <SortIcon column="current_stage" />
              </th>
              <th
                className="text-center py-3 px-4 font-medium text-gray-600 cursor-pointer select-none hover:text-gray-900"
                onClick={() => toggleSort("outcome")}
              >
                Outcome <SortIcon column="outcome" />
              </th>
              <th className="text-center py-3 px-4 font-medium text-gray-600 w-16"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((b) => (
              <tr
                key={b.borrower_id}
                onClick={() => onSelectBorrower?.(b.borrower_id)}
                className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer group"
              >
                <td className="py-3 px-4 font-medium text-gray-900">{b.name}</td>
                <td className="py-3 px-4 text-gray-500 font-mono text-xs">{b.borrower_id}</td>
                <td className="py-3 px-4 text-right font-mono">
                  ${b.total_debt.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </td>
                <td className="py-3 px-4 text-gray-500 capitalize">
                  {b.debt_type.replace("_", " ")}
                </td>
                <td className="py-3 px-4 text-center">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      STAGE_COLORS[b.current_stage] ?? STAGE_COLORS.unknown
                    }`}
                  >
                    {b.current_stage.replace("_", " ")}
                  </span>
                </td>
                <td className="py-3 px-4 text-center">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      OUTCOME_COLORS[b.outcome] ?? OUTCOME_COLORS.pending
                    }`}
                  >
                    {b.outcome}
                  </span>
                </td>
                <td className="py-3 px-4 text-center">
                  <button
                    onClick={(e) => handleDelete(e, b.borrower_id)}
                    disabled={deletingId === b.borrower_id}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-md text-gray-400 hover:text-red-600 hover:bg-red-50 disabled:opacity-50"
                    title="Delete borrower"
                  >
                    {deletingId === b.borrower_id ? (
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                      </svg>
                    )}
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-gray-400 text-sm">
                  No borrowers match your filters
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
