import { useState, useCallback } from "react";
import { startWorkflow } from "../../api/client";
import type { StartWorkflowRequest } from "../../api/types";

interface Props {
  onSuccess: () => void;
}

const INITIAL: StartWorkflowRequest = {
  borrower_id: "",
  name: "",
  account_last4: "",
  total_debt: 0,
  debt_type: "credit_card",
  days_past_due: 90,
  phone_number: "",
  email: "",
};

export default function AddBorrowerForm({ onSuccess }: Props) {
  const [form, setForm] = useState<StartWorkflowRequest>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const { name, value, type } = e.target;
      setForm((prev) => ({
        ...prev,
        [name]: type === "number" ? Number(value) : value,
      }));
    },
    []
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setLoading(true);
      setError(null);
      try {
        await startWorkflow(form);
        setForm(INITIAL);
        onSuccess();
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [form, onSuccess]
  );

  const inputClass =
    "w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="bg-red-50 text-red-700 text-sm p-3 rounded-md">{error}</div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Borrower ID
          </label>
          <input
            name="borrower_id"
            value={form.borrower_id}
            onChange={handleChange}
            required
            className={inputClass}
            placeholder="B001"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Full Name
          </label>
          <input
            name="name"
            value={form.name}
            onChange={handleChange}
            required
            className={inputClass}
            placeholder="John Doe"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Account Last 4
          </label>
          <input
            name="account_last4"
            value={form.account_last4}
            onChange={handleChange}
            required
            maxLength={4}
            className={inputClass}
            placeholder="4532"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Total Debt ($)
          </label>
          <input
            name="total_debt"
            type="number"
            value={form.total_debt || ""}
            onChange={handleChange}
            required
            min={0}
            step={0.01}
            className={inputClass}
            placeholder="5200.00"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Debt Type
          </label>
          <select
            name="debt_type"
            value={form.debt_type}
            onChange={handleChange}
            className={inputClass}
          >
            <option value="credit_card">Credit Card</option>
            <option value="personal_loan">Personal Loan</option>
            <option value="auto_loan">Auto Loan</option>
            <option value="medical">Medical</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Days Past Due
          </label>
          <input
            name="days_past_due"
            type="number"
            value={form.days_past_due}
            onChange={handleChange}
            min={0}
            className={inputClass}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Phone Number
          </label>
          <input
            name="phone_number"
            value={form.phone_number}
            onChange={handleChange}
            className={inputClass}
            placeholder="+15551234567"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            className={inputClass}
            placeholder="john@example.com"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300"
      >
        {loading ? "Starting Workflow..." : "Add Borrower & Start Workflow"}
      </button>
    </form>
  );
}
