import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import AddBorrowerForm from "../components/admin/AddBorrowerForm";
import BorrowerTable from "../components/admin/BorrowerTable";
import PromptManager from "../components/admin/PromptManager";
import Modal from "../components/shared/Modal";

export default function AdminPage() {
  const [showAddForm, setShowAddForm] = useState(false);
  const [showPrompts, setShowPrompts] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const navigate = useNavigate();

  const handleBorrowerAdded = useCallback(() => {
    setShowAddForm(false);
    setRefreshTrigger((prev) => prev + 1);
  }, []);

  const handleSelectBorrower = useCallback(
    (id: string) => {
      navigate(`/borrower?id=${id}`);
    },
    [navigate]
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        <div className="flex gap-3">
          <button
            onClick={() => setShowPrompts(true)}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-200"
          >
            Manage Prompts
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
          >
            + Add Borrower
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Active Borrowers</h2>
        </div>
        <BorrowerTable
          refreshTrigger={refreshTrigger}
          onSelectBorrower={handleSelectBorrower}
        />
      </div>

      <Modal
        open={showAddForm}
        onClose={() => setShowAddForm(false)}
        title="Add New Borrower"
      >
        <AddBorrowerForm onSuccess={handleBorrowerAdded} />
      </Modal>

      <Modal
        open={showPrompts}
        onClose={() => setShowPrompts(false)}
        title="Prompt Management"
      >
        <PromptManager />
      </Modal>
    </div>
  );
}
