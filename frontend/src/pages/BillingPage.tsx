const PLANS = [
  {
    name: "Pro",
    price: "$299",
    period: "/month",
    description: "For small agencies getting started with AI collections",
    features: [
      "Up to 500 borrowers/month",
      "3 AI agent types (Assessment, Resolution, Final Notice)",
      "Email & chat channels",
      "Basic analytics dashboard",
      "FDCPA compliance checks",
      "Email support",
      "5 team seats",
    ],
    cta: "Upgrade to Pro",
    popular: false,
  },
  {
    name: "Max",
    price: "$799",
    period: "/month",
    description: "For growing agencies that need voice + self-learning",
    features: [
      "Up to 5,000 borrowers/month",
      "All Pro features",
      "Voice agent (outbound AI calls)",
      "Self-learning loop (auto prompt optimization)",
      "Advanced reporting & cost tracking",
      "Prompt version management & rollback",
      "Custom compliance rules",
      "Priority support",
      "25 team seats",
    ],
    cta: "Upgrade to Max",
    popular: true,
  },
  {
    name: "Custom",
    price: "Custom",
    period: "",
    description: "For enterprise agencies with custom requirements",
    features: [
      "Unlimited borrowers",
      "All Max features",
      "Dedicated Temporal cluster",
      "Custom AI model fine-tuning",
      "On-premise deployment option",
      "SSO & RBAC",
      "Custom API integrations",
      "Dedicated account manager",
      "SLA guarantees",
      "Unlimited seats",
    ],
    cta: "Contact Sales",
    popular: false,
  },
];

export default function BillingPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Billing & Plans</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage your subscription and billing details
        </p>
      </div>

      {/* Current plan banner */}
      <div className="mb-8 bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-5 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-lg font-semibold">Free Trial</h2>
              <span className="px-2 py-0.5 bg-white/20 text-white text-xs font-medium rounded-full">
                Active
              </span>
            </div>
            <p className="text-blue-100 text-sm mt-1">
              You're currently on the free trial. All Max features are unlocked for 14 days.
            </p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">11 days</p>
            <p className="text-blue-200 text-xs">remaining</p>
          </div>
        </div>
        <div className="mt-4 h-2 bg-white/20 rounded-full overflow-hidden">
          <div className="h-full bg-white/60 rounded-full" style={{ width: "21%" }} />
        </div>
        <p className="text-xs text-blue-200 mt-1.5">3 of 14 trial days used</p>
      </div>

      {/* Usage summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <UsageCard label="Borrowers This Month" value="23" limit="5,000" percent={0.5} />
        <UsageCard label="API Calls" value="1,847" limit="50,000" percent={3.7} />
        <UsageCard label="Voice Minutes" value="42" limit="500" percent={8.4} />
        <UsageCard label="Team Members" value="2" limit="25" percent={8} />
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`relative bg-white rounded-xl border-2 p-6 transition-shadow hover:shadow-md ${
              plan.popular
                ? "border-blue-600 shadow-sm"
                : "border-gray-200"
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="px-3 py-1 bg-blue-600 text-white text-xs font-semibold rounded-full shadow-sm">
                  Most Popular
                </span>
              </div>
            )}

            <div className="mb-5">
              <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
              <p className="text-xs text-gray-500 mt-1">{plan.description}</p>
              <div className="mt-4">
                <span className="text-3xl font-bold text-gray-900">{plan.price}</span>
                {plan.period && (
                  <span className="text-gray-500 text-sm">{plan.period}</span>
                )}
              </div>
            </div>

            <ul className="space-y-2.5 mb-6">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                  <svg className="w-4 h-4 text-green-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>

            <button
              className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-colors ${
                plan.popular
                  ? "bg-blue-600 text-white hover:bg-blue-700 shadow-sm"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {plan.cta}
            </button>
          </div>
        ))}
      </div>

      {/* Payment info */}
      <div className="mt-8 bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Payment Method</h3>
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
          <div className="w-10 h-7 bg-gradient-to-br from-slate-700 to-slate-800 rounded flex items-center justify-center">
            <span className="text-white text-[10px] font-bold">VISA</span>
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-700 font-medium">No payment method on file</p>
            <p className="text-xs text-gray-400">Add a payment method before your trial ends</p>
          </div>
          <button className="px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded-md transition-colors">
            Add Card
          </button>
        </div>
      </div>
    </div>
  );
}

function UsageCard({
  label,
  value,
  limit,
  percent,
}: {
  label: string;
  value: string;
  limit: string;
  percent: number;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 font-medium">{label}</p>
      <div className="flex items-baseline gap-1.5 mt-1">
        <span className="text-xl font-bold text-gray-900">{value}</span>
        <span className="text-xs text-gray-400">/ {limit}</span>
      </div>
      <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <p className="text-[10px] text-gray-400 mt-1">{percent}% used</p>
    </div>
  );
}
