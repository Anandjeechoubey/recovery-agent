import { useEffect, useState, useCallback } from "react";
import { listWorkflows } from "../../api/client";
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

interface Props {
  refreshTrigger: number;
  onSelectBorrower?: (id: string) => void;
}

export default function BorrowerTable({ refreshTrigger, onSelectBorrower }: Props) {
  const [borrowers, setBorrowers] = useState<BorrowerWorkflow[]>([]);
  const [loading, setLoading] = useState(true);

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
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-3 px-4 font-medium text-gray-600">Name</th>
            <th className="text-left py-3 px-4 font-medium text-gray-600">ID</th>
            <th className="text-right py-3 px-4 font-medium text-gray-600">Total Debt</th>
            <th className="text-left py-3 px-4 font-medium text-gray-600">Type</th>
            <th className="text-center py-3 px-4 font-medium text-gray-600">Stage</th>
            <th className="text-center py-3 px-4 font-medium text-gray-600">Outcome</th>
          </tr>
        </thead>
        <tbody>
          {borrowers.map((b) => (
            <tr
              key={b.borrower_id}
              onClick={() => onSelectBorrower?.(b.borrower_id)}
              className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
