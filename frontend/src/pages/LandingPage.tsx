import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

const PIPELINE_STAGES = [
  {
    number: "01",
    badge: "Chat Agent",
    badgeColor: "bg-blue-600/20 border-blue-500/30 text-blue-400",
    icon: "💬",
    title: "Assessment",
    subtitle: "Identity & Financial Discovery",
    description:
      "Verifies borrower identity via secure chat, gathers employment status, income, hardship circumstances, and determines the appropriate resolution path.",
    details: [
      "Identity verification",
      "Financial situation analysis",
      "Hardship detection",
      "Resolution routing",
    ],
    borderColor: "border-blue-500/40",
  },
  {
    number: "02",
    badge: "Voice Agent",
    badgeColor: "bg-yellow-600/20 border-yellow-500/30 text-yellow-400",
    icon: "📞",
    title: "Resolution",
    subtitle: "AI Voice Negotiation",
    description:
      "Places an outbound voice call to negotiate settlement. Offers lump-sum discounts, structured payment plans, or hardship deferrals based on assessment data.",
    details: [
      "Outbound voice calls",
      "Lump-sum negotiation",
      "Payment plan structuring",
      "Hardship accommodations",
    ],
    borderColor: "border-yellow-500/40",
  },
  {
    number: "03",
    badge: "Chat Agent",
    badgeColor: "bg-red-600/20 border-red-500/30 text-red-400",
    icon: "⚠️",
    title: "Final Notice",
    subtitle: "Hard Deadline, Last Offer",
    description:
      "FDCPA-compliant final communication with a firm deadline. Consequence-driven messaging presenting the last available settlement offer before escalation.",
    details: [
      "Hard deadline enforcement",
      "Consequence messaging",
      "Last offer presentation",
      "FDCPA compliance",
    ],
    borderColor: "border-red-500/40",
  },
];

const FEATURES = [
  {
    icon: "🧬",
    title: "Self-Learning Agents",
    subtitle: "Darwin Godel Machine",
    description:
      "Agents autonomously evaluate their own performance and propose improved prompts after every batch of cases. The best-performing versions are activated automatically. The meta-evaluator even improves the evaluation methodology itself.",
    highlight: "Agents improve without human intervention",
    tag: "Autonomous Improvement",
    tagColor: "bg-purple-600/20 border-purple-500/30 text-purple-400",
    details: [
      "Automated prompt evaluation & scoring",
      "Meta-evaluator validates improvements",
      "Full version history with rollback",
      "Performance tracked across simulated cases",
    ],
  },
  {
    icon: "⚖️",
    title: "FDCPA Compliance Built-In",
    subtitle: "Regulatory Protection",
    description:
      "Every agent operates within hard-coded FDCPA rules. No false threats, no harassment, no misrepresentation. Compliance is not a setting — it's architectural. Every prompt update is validated before deployment.",
    highlight: "Compliance as code, not configuration",
    tag: "Compliance",
    tagColor: "bg-green-600/20 border-green-500/30 text-green-400",
    details: [
      "FDCPA guardrails at agent level",
      "No harassment or false threats",
      "Validation layer on every response",
      "Audit-ready conversation logs",
    ],
  },
  {
    icon: "📋",
    title: "Full Audit Trail",
    subtitle: "Prompt Evolution History",
    description:
      "Every prompt version, every activation, every rollback is logged. Know exactly which agent version spoke to which borrower on which date. One-click rollback to any prior version.",
    highlight: "Version-controlled AI behavior",
    tag: "Observability",
    tagColor: "bg-blue-600/20 border-blue-500/30 text-blue-400",
    details: [
      "Prompt version history for all agents",
      "Rollback to any previous version",
      "Per-case agent version attribution",
      "Regulator-ready export",
    ],
  },
  {
    icon: "💰",
    title: "Cost & Resolution Tracking",
    subtitle: "Operational Intelligence",
    description:
      "Track token spend per agent, resolution rates by stage, and cost-per-recovered-dollar. Full visibility into the economics of your AI collections floor.",
    highlight: "Know your ROI down to the case",
    tag: "Analytics",
    tagColor: "bg-yellow-600/20 border-yellow-500/30 text-yellow-400",
    details: [
      "Token cost tracking per agent",
      "Resolution rate by stage",
      "Cost-per-case breakdown",
      "Agreement vs. escalation rates",
    ],
  },
];

const INTEGRATION_METHODS = [
  {
    icon: "🔌",
    title: "REST API",
    description:
      "POST /api/borrowers to kick off a workflow. GET /api/workflows to list active cases. Full OpenAPI spec included.",
  },
  {
    icon: "⚙️",
    title: "Temporal Worker",
    description:
      "Drop the Python worker into your infrastructure. Connects to your Temporal server. Stateful, retryable workflows out of the box.",
  },
  {
    icon: "🐳",
    title: "Docker Compose",
    description:
      "Full stack in one command. Includes the FastAPI backend, React frontend, and Temporal server. Ready in under 5 minutes.",
  },
];

const STATS = [
  {
    value: "3×",
    label: "More cases per agent vs. human collectors",
    sublabel: "at scale",
  },
  {
    value: "72%",
    label: "Average first-contact resolution rate",
    sublabel: "assessment stage",
  },
  {
    value: "< 5min",
    label: "Workflow launch to first contact",
    sublabel: "zero manual steps",
  },
  {
    value: "100%",
    label: "FDCPA compliant interactions",
    sublabel: "guaranteed by architecture",
  },
];

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Navbar */}
      <nav
        className={`fixed top-0 w-full z-50 transition-all duration-300 ${
          scrolled ? "bg-slate-950/95 backdrop-blur-md" : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-white font-bold text-xl">ApexAI</span>
            <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wide">
              BETA
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a
              href="#how-it-works"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              How It Works
            </a>
            <a
              href="#features"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Features
            </a>
            <a
              href="#integration"
              className="text-sm text-slate-400 hover:text-white transition-colors"
            >
              Integration
            </a>
          </div>
          <Link to="/dashboard/borrowers">
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors">
              Dashboard →
            </button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center justify-center px-6 pt-16 pb-24 overflow-hidden">
        {/* Glow background */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-3xl" />
        </div>
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-600/20 border border-blue-500/30 text-blue-400 text-xs font-medium uppercase tracking-wider mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            AI-Powered Collections Automation
          </span>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05]">
            <span className="text-white">Recover More</span>
            <span className="text-blue-500">.</span>
            <br />
            <span className="text-white">Work Less</span>
            <span className="text-blue-500">.</span>
            <br />
            <span className="text-blue-400">Stay Compliant.</span>
          </h1>
          <p className="mt-6 text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Three AI agents orchestrate your entire collections workflow — from
            initial assessment to voice negotiation to final notice — while
            learning and improving with every case.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="https://cal.com/anand-jee-choubey/demo-apex-recovery">
              <button className="px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-base transition-all shadow-lg shadow-blue-600/25">
                Book a demo →
              </button>
            </a>
            <a href="#how-it-works">
              <button className="px-8 py-4 border border-slate-700 hover:border-slate-500 text-slate-300 hover:text-white font-semibold rounded-xl text-base transition-all">
                See How It Works
              </button>
            </a>
          </div>
          <div className="mt-16 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-slate-500 text-sm">
            <span>✓ FDCPA Compliant</span>
            <span className="text-slate-700 hidden sm:inline">|</span>
            <span>✓ Full Audit Trail</span>
            <span className="text-slate-700 hidden sm:inline">|</span>
            <span>✓ REST API + Docker</span>
            <span className="text-slate-700 hidden sm:inline">|</span>
            <span>✓ Self-Learning Agents</span>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 px-6 bg-slate-900">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-blue-400 text-sm font-semibold uppercase tracking-wider mb-3">
              The Pipeline
            </p>
            <h2 className="text-4xl font-bold text-white">
              Three Agents. One Workflow.
            </h2>
            <p className="mt-4 text-slate-400 text-lg max-w-2xl mx-auto">
              Temporal orchestrates each stage automatically. Agents hand off
              with full context. No manual intervention required.
            </p>
          </div>

          {/* Desktop: flex row with arrows */}
          <div className="hidden md:flex items-start gap-0">
            {PIPELINE_STAGES.map((stage, idx) => (
              <>
                <div
                  key={stage.number}
                  className={`flex-1 relative bg-slate-800/50 rounded-2xl p-6 border ${stage.borderColor} shadow-xl`}
                >
                  <div className="absolute top-4 right-4 text-slate-700 font-bold text-4xl font-mono select-none">
                    {stage.number}
                  </div>
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${stage.badgeColor}`}
                  >
                    {stage.badge}
                  </span>
                  <div className="mt-4 text-3xl">{stage.icon}</div>
                  <h3 className="mt-3 text-xl font-bold text-white">
                    {stage.title}
                  </h3>
                  <p className="text-sm text-slate-400 font-medium mt-0.5">
                    {stage.subtitle}
                  </p>
                  <p className="mt-3 text-slate-400 text-sm leading-relaxed">
                    {stage.description}
                  </p>
                  <ul className="mt-4 space-y-1.5">
                    {stage.details.map((d) => (
                      <li
                        key={d}
                        className="flex items-center gap-2 text-xs text-slate-300"
                      >
                        <span className="text-green-400">✓</span>
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
                {idx < PIPELINE_STAGES.length - 1 && (
                  <div
                    key={`arrow-${idx}`}
                    className="flex items-center justify-center w-12 mt-24 text-slate-600 text-2xl flex-shrink-0"
                  >
                    →
                  </div>
                )}
              </>
            ))}
          </div>

          {/* Mobile: stacked */}
          <div className="md:hidden space-y-4">
            {PIPELINE_STAGES.map((stage, idx) => (
              <div key={stage.number}>
                <div
                  className={`bg-slate-800/50 rounded-2xl p-6 border ${stage.borderColor} shadow-xl`}
                >
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${stage.badgeColor}`}
                  >
                    {stage.badge}
                  </span>
                  <div className="mt-4 text-3xl">{stage.icon}</div>
                  <h3 className="mt-3 text-xl font-bold text-white">
                    {stage.title}
                  </h3>
                  <p className="text-sm text-slate-400 font-medium mt-0.5">
                    {stage.subtitle}
                  </p>
                  <p className="mt-3 text-slate-400 text-sm leading-relaxed">
                    {stage.description}
                  </p>
                  <ul className="mt-4 space-y-1.5">
                    {stage.details.map((d) => (
                      <li
                        key={d}
                        className="flex items-center gap-2 text-xs text-slate-300"
                      >
                        <span className="text-green-400">✓</span>
                        {d}
                      </li>
                    ))}
                  </ul>
                </div>
                {idx < PIPELINE_STAGES.length - 1 && (
                  <div className="flex items-center justify-center py-2 text-slate-600 text-xl">
                    ↓
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-10 flex items-center justify-center gap-3 p-4 bg-slate-800/30 rounded-xl border border-slate-700/50 max-w-xl mx-auto">
            <span className="text-slate-500 text-sm">Orchestrated by</span>
            <span className="font-mono font-bold text-white text-sm">
              Apex AI
            </span>
            <span className="text-slate-600 text-xs">
              — durable execution, automatic retries, full observability
            </span>
          </div>
        </div>
      </section>

      {/* Key Features */}
      <section id="features" className="py-24 px-6 bg-slate-950">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-blue-400 text-sm font-semibold uppercase tracking-wider mb-3">
              Built Different
            </p>
            <h2 className="text-4xl font-bold text-white">
              Features That Matter to Recovery Agencies
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="bg-slate-800/40 rounded-2xl p-8 border border-slate-700/50 hover:border-slate-600/60 transition-colors"
              >
                <div className="flex items-start justify-between mb-4">
                  <span className="text-4xl">{feature.icon}</span>
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full border ${feature.tagColor}`}
                  >
                    {feature.tag}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-white">
                  {feature.title}
                </h3>
                <p className="text-slate-500 text-xs font-medium mt-0.5 mb-3">
                  {feature.subtitle}
                </p>
                <p className="text-slate-400 text-sm leading-relaxed mb-4">
                  {feature.description}
                </p>
                <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/40 mb-4">
                  <p className="text-blue-400 text-xs font-medium">
                    {feature.highlight}
                  </p>
                </div>
                <ul className="space-y-1.5">
                  {feature.details.map((d) => (
                    <li
                      key={d}
                      className="flex items-center gap-2 text-xs text-slate-400"
                    >
                      <span className="text-green-400 font-bold">→</span>
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Integration */}
      <section id="integration" className="py-24 px-6 bg-slate-900">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
            {/* Left column */}
            <div>
              <p className="text-blue-400 text-sm font-semibold uppercase tracking-wider mb-3">
                Integration
              </p>
              <h2 className="text-4xl font-bold text-white">
                Drop In. Don't Rip Out.
              </h2>
              <p className="mt-4 text-slate-400 text-lg leading-relaxed">
                ApexAI connects to your existing systems via REST API. Run the
                Temporal worker alongside your existing infrastructure. One
                borrower ID is all it takes to start a workflow.
              </p>
              <div className="mt-8 space-y-4">
                {INTEGRATION_METHODS.map((method) => (
                  <div
                    key={method.title}
                    className="flex gap-4 p-4 rounded-xl bg-slate-800/30 border border-slate-700/40"
                  >
                    <span className="text-2xl mt-0.5 flex-shrink-0">
                      {method.icon}
                    </span>
                    <div>
                      <p className="font-semibold text-white text-sm">
                        {method.title}
                      </p>
                      <p className="text-slate-400 text-sm mt-1">
                        {method.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Right column - terminal mock */}
            <div className="rounded-2xl overflow-hidden border border-slate-700/60">
              <div className="flex items-center gap-2 px-4 py-3 bg-slate-800 border-b border-slate-700/60">
                <span className="w-3 h-3 rounded-full bg-red-500/80" />
                <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <span className="w-3 h-3 rounded-full bg-green-500/80" />
                <span className="ml-2 text-slate-400 text-xs font-mono">
                  ApexAI API
                </span>
              </div>
              <pre className="p-6 bg-slate-950 text-sm font-mono leading-relaxed overflow-x-auto">
                <code>
                  <span className="text-slate-500">
                    # Start a collections workflow{"\n"}
                  </span>
                  <span className="text-blue-400">curl</span>
                  <span className="text-white">
                    {" "}
                    -X POST https://api.recoverai.io
                  </span>
                  <span className="text-green-400">/api/borrowers</span>
                  <span className="text-white"> \{"\n"}</span>
                  <span className="text-white"> -H </span>
                  <span className="text-yellow-300">
                    "Content-Type: application/json"
                  </span>
                  <span className="text-white"> \{"\n"}</span>
                  <span className="text-white"> -d </span>
                  <span className="text-yellow-300">
                    {`'{\n  "borrower_id": "B001",\n  "name": "Jane Smith",\n  "total_debt": 8500.00,\n  "debt_type": "credit_card"\n}'`}
                  </span>
                  <span className="text-white">{"\n\n"}</span>
                  <span className="text-slate-500"># Response{"\n"}</span>
                  <span className="text-white">{"{\n"}</span>
                  <span className="text-green-400"> "workflow_id"</span>
                  <span className="text-white">: </span>
                  <span className="text-yellow-300">"recoverai-B001"</span>
                  <span className="text-white">{",\n"}</span>
                  <span className="text-green-400"> "status"</span>
                  <span className="text-white">: </span>
                  <span className="text-yellow-300">"started"</span>
                  <span className="text-white">{",\n"}</span>
                  <span className="text-green-400"> "stage"</span>
                  <span className="text-white">: </span>
                  <span className="text-yellow-300">"assessment"</span>
                  <span className="text-white">{",\n"}</span>
                  <span className="text-green-400"> "borrower_url"</span>
                  <span className="text-white">: </span>
                  <span className="text-yellow-300">"/borrower?id=B001"</span>
                  <span className="text-white">{"\n}"}</span>
                  <span className="text-white">{"\n\n"}</span>
                  <span className="text-slate-500">
                    # Stream real-time updates{"\n"}
                  </span>
                  <span className="text-blue-400">GET</span>
                  <span className="text-green-400">
                    {" "}
                    /api/borrowers/B001/stream
                  </span>
                  <span className="text-slate-500"> (SSE)</span>
                </code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 px-6 bg-blue-600">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {STATS.map((stat) => (
              <div key={stat.value}>
                <p className="text-4xl md:text-5xl font-bold text-white">
                  {stat.value}
                </p>
                <p className="mt-2 text-blue-100 text-sm font-medium">
                  {stat.label}
                </p>
                <p className="text-blue-200/60 text-xs mt-1">{stat.sublabel}</p>
              </div>
            ))}
          </div>
          <p className="text-center text-blue-200/50 text-xs mt-10">
            * Metrics based on internal benchmarks and simulated evaluation
            runs. Production results may vary.
          </p>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-24 px-6 bg-slate-950">
        <div className="max-w-3xl mx-auto text-center">
          <div className="p-12 rounded-3xl bg-slate-900 border border-slate-700/60 shadow-2xl shadow-blue-600/5 relative overflow-hidden">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />
            <div className="relative">
              <span className="text-blue-400 text-sm font-semibold uppercase tracking-wider">
                Ready to Automate Collections?
              </span>
              <h2 className="mt-4 text-4xl font-bold text-white">
                Start recovering more.
                <br />
                <span className="text-blue-400">Today.</span>
              </h2>
              <p className="mt-4 text-slate-400 text-lg max-w-xl mx-auto">
                Open the agency dashboard, add your first borrower, and let
                ApexAI handle the rest. Full workflow in minutes.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/dashboard/borrowers">
                  <button className="px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-base transition-all shadow-lg shadow-blue-600/30">
                    Try it out →
                  </button>
                </Link>
              </div>
              <p className="mt-6 text-slate-600 text-sm">
                No signup required · Self-hosted · Docker Compose ready
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 bg-slate-950 border-t border-slate-800/60">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-slate-600 text-sm">
          <span className="font-bold text-slate-400">ApexAI</span>
          <div className="flex gap-6">
            <a
              href="#how-it-works"
              className="hover:text-slate-300 transition-colors"
            >
              How It Works
            </a>
            <a
              href="#features"
              className="hover:text-slate-300 transition-colors"
            >
              Features
            </a>
            <a
              href="#integration"
              className="hover:text-slate-300 transition-colors"
            >
              Integration
            </a>
            <Link
              to="/dashboard/borrowers"
              className="hover:text-slate-300 transition-colors"
            >
              Dashboard
            </Link>
          </div>
          <span>© 2026 ApexAI · FDCPA Compliant</span>
        </div>
      </footer>
    </div>
  );
}
