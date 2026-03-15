import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import BorrowerTable from "../components/admin/BorrowerTable";

export default function BorrowersPage() {
  const [refreshTrigger] = useState(0);
  const navigate = useNavigate();

  const handleSelectBorrower = useCallback(
    (id: string) => {
      navigate(`/borrower?id=${id}`);
    },
    [navigate]
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Borrowers</h1>
          <p className="text-sm text-gray-500 mt-1">
            Monitor active workflows and borrower interactions
          </p>
        </div>
        <button
          onClick={() => navigate("/dashboard/add-borrower")}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add Borrower
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900">Active Workflows</h2>
            <span className="text-xs text-gray-400">Auto-refreshes every 10s</span>
          </div>
        </div>
        <BorrowerTable
          refreshTrigger={refreshTrigger}
          onSelectBorrower={handleSelectBorrower}
        />
      </div>
    </div>
  );
}
