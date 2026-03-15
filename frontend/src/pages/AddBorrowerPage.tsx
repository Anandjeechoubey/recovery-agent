import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { startWorkflow } from "../api/client";
import type { StartWorkflowRequest } from "../api/types";

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

export default function AddBorrowerPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<StartWorkflowRequest>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

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
      setSuccess(false);
      try {
        await startWorkflow(form);
        setSuccess(true);
        setForm(INITIAL);
        setTimeout(() => navigate("/dashboard/borrowers"), 1500);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [form, navigate]
  );

  const inputClass =
    "w-full border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Add Borrower</h1>
        <p className="text-sm text-gray-500 mt-1">
          Create a new borrower profile and start their collections workflow
        </p>
      </div>

      <div className="max-w-2xl">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          {success && (
            <div className="mb-5 px-4 py-3 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Workflow started successfully. Redirecting...
            </div>
          )}

          {error && (
            <div className="mb-5 px-4 py-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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
                  placeholder="5,200.00"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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
                <label className="block text-xs font-medium text-gray-600 mb-1.5">
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

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-2 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 transition-colors shadow-sm"
              >
                {loading ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Starting Workflow...
                  </>
                ) : (
                  "Add Borrower & Start Workflow"
                )}
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard/borrowers")}
                className="px-5 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
