# Self-Learning AI Collections Agents - Implementation Plan

## Context

Building a post-default debt collections system with 3 AI agents orchestrated by Temporal, featuring a self-learning loop that autonomously improves agent prompts and a meta-evaluation layer (Darwin Godel Machine).

**Tech Stack:** Python 3.11+, OpenAI (GPT-4o + GPT-4o-mini), Vapi (voice), FastAPI, Temporal, Docker Compose

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI (port 8000)               │
│  /workflow/start  /chat/{id}  /admin/*  /webhook/*   │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              Temporal Server (port 7233)             │
│              Temporal UI (port 8080)                 │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              Temporal Worker                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │  Assessment   │ │  Resolution  │ │ Final Notice │ │
│  │  Agent (Chat) │ │ Agent (Voice)│ │  Agent (Chat)│ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
│         │    Handoff      │    Handoff     │         │
│         └──── (500tok) ───┴─── (500tok) ───┘         │
└─────────────────────────────────────────────────────┘
```

### Pipeline Flow

```
Borrower enters pipeline
    │
    ▼
Assessment Agent (Chat) ──── max 3 retries on no_response
    │
    ├── situation assessed ──► Summarize (≤500 tokens)
    │                              │
    ▼                              ▼
Resolution Agent (Voice/Vapi) ◄── handoff context
    │
    ├── deal agreed ──► EXIT: Log agreement
    │
    ├── no deal ──► Summarize full history (≤500 tokens)
    │                    │
    ▼                    ▼
Final Notice Agent (Chat) ◄── handoff context
    │
    ├── resolved ──► EXIT: Log resolution
    └── no resolution ──► EXIT: Flag for legal/write-off
```

---

## Project Structure

```
recovery-agents/
├── docker-compose.yml          # Full system orchestration
├── Dockerfile                  # Python 3.12 app image
├── Makefile                    # Common commands
├── pyproject.toml              # Dependencies and config
├── .env.example                # Required environment variables
├── .gitignore
├── README.md
├── knowledge/                  # Project documentation
├── src/
│   ├── config.py               # Pydantic Settings, env loading
│   ├── models/
│   │   ├── borrower.py         # Borrower, PolicyRanges
│   │   ├── conversation.py     # Message, Conversation, HandoffSummary
│   │   └── evaluation.py       # PromptVersion, MetricScore, EvalResult
│   ├── agents/
│   │   ├── base.py             # BaseAgent with token budget enforcement
│   │   ├── assessment.py       # Agent 1: Cold, clinical fact-gatherer
│   │   ├── resolution.py       # Agent 2: Transactional dealmaker
│   │   ├── final_notice.py     # Agent 3: Consequence-driven closer
│   │   └── compliance.py       # 8-rule compliance checker (rule-based + LLM)
│   ├── context/
│   │   ├── token_budget.py     # tiktoken-based 2000/500 budget enforcement
│   │   └── summarizer.py       # LLM summarization for handoffs
│   ├── voice/
│   │   ├── vapi_client.py      # Vapi REST API wrapper
│   │   └── webhook.py          # Vapi webhook handler
│   ├── workflow/
│   │   ├── collections_workflow.py  # Temporal workflow definition
│   │   ├── activities.py       # Temporal activities for each stage
│   │   └── worker.py           # Temporal worker process
│   ├── api/
│   │   ├── app.py              # FastAPI application
│   │   ├── dependencies.py     # Temporal client singleton
│   │   └── routes/
│   │       ├── workflow.py     # /workflow/* endpoints
│   │       ├── chat.py         # /chat/* endpoints
│   │       └── admin.py        # /admin/* prompt management
│   └── learning/
│       ├── loop.py             # Main learning loop orchestrator
│       ├── simulator.py        # Conversation simulation engine
│       ├── personas.py         # 5 borrower personas
│       ├── evaluator.py        # LLM-as-judge scoring
│       ├── metrics.py          # Metric aggregation and weighting
│       ├── statistical.py      # Wilcoxon signed-rank + bootstrap CI
│       ├── prompt_proposer.py  # Failure-analysis prompt mutation
│       ├── prompt_store.py     # Version-controlled prompt storage
│       ├── compliance_eval.py  # Fast compliance evaluation
│       ├── cost_tracker.py     # API spend tracking ($20 budget)
│       ├── meta_evaluator.py   # Darwin Godel Machine
│       └── report.py           # Evolution report generator
├── prompts/                    # Prompt version store (JSON files)
│   ├── assessment/
│   ├── resolution/
│   └── final_notice/
├── data/                       # Raw evaluation data
│   ├── conversations/
│   ├── evaluations/
│   └── reports/
└── tests/
    ├── test_context_budget.py
    ├── test_compliance.py
    ├── test_statistical.py
    └── test_models.py
```

---

## Key Design Decisions

### Token Budget Enforcement (Hard Constraint)

| Agent | System Prompt Budget | Handoff Budget | Total |
|-------|---------------------|----------------|-------|
| Assessment | 2000 tokens | 0 tokens | 2000 |
| Resolution | 1500 tokens | 500 tokens | 2000 |
| Final Notice | 1500 tokens | 500 tokens | 2000 |

- Enforced using `tiktoken` with `cl100k_base` encoding
- `enforce_budget()` raises `ValueError` if prompt exceeds available tokens
- Handoff summaries are truncated to 500 tokens if they exceed the limit
- Every agent prompt is validated in unit tests

### Cross-Modal Handoff Design

- **Chat → Voice (Agent 1 → 2):** Assessment conversation is summarized into a structured bullet-point format preserving identity verification, financial situation, and emotional state. The summary is injected into the Resolution agent's system prompt under a `## CONTEXT FROM PRIOR STAGES` section.
- **Voice → Chat (Agent 2 → 3):** Both the Assessment chat and Resolution voice transcript are summarized together into a single 500-token handoff. This forces prioritization of the most critical information.
- Summarization uses GPT-4o-mini with a structured extraction prompt that explicitly lists what must be preserved.

### Agent Personalities

- **Assessment:** Cold, clinical. One question at a time. No negotiation. Discloses AI identity and recording upfront.
- **Resolution:** Transactional. Anchors on lump-sum (lowest in range), then payment plan. Restates terms on objections. Pushes for verbal commitment.
- **Final Notice:** Consequence-driven. States credit reporting, legal referral, asset recovery. One final offer with 48-hour expiry. Does not argue.

### Compliance (8 Rules)

1. AI identity disclosure (first message)
2. No false threats (LLM-checked)
3. No harassment after stop-contact request (keyword detection)
4. No misleading terms (offers within PolicyRanges)
5. Hardship referral when distress detected (keyword detection + agent response check)
6. Recording disclosure (first message)
7. Professional composure (LLM-checked)
8. Data privacy — no full account numbers (regex patterns)

Two modes: `check_compliance()` (full, with LLM) and `check_compliance_quick()` (fast, rule-based only — used during learning loop).

---

## Self-Learning Loop

### Flow per Iteration

```
1. Load current active prompts for all 3 agents
2. Simulate 20 pipeline conversations (4 per persona × 5 personas)
3. Evaluate all conversations → baseline scores
4. For each agent:
   a. Find weakest metric
   b. Analyze failure examples
   c. Propose targeted prompt mutation (GPT-4o-mini)
   d. Simulate 20 pipeline conversations with candidate prompt
   e. Evaluate → candidate scores
   f. Wilcoxon signed-rank test (paired by persona/seed)
   g. If p < 0.05 AND effect > 0.2 AND no compliance regression → adopt
   h. Else → reject, log reason
5. Run meta-evaluation every 2 iterations
6. Save all data, update cost tracker
7. Stop if budget exceeded ($20 limit)
```

### Metrics (scored 1-5 by LLM judge)

**Assessment:** information_gathering, tone_adherence, efficiency
**Resolution:** negotiation_effectiveness, tone_adherence, context_usage
**Final Notice:** urgency_communication, tone_adherence, context_usage
**System-level:** handoff_continuity, no_repeated_questions

### Statistical Rigor

- **Test:** Wilcoxon signed-rank (non-parametric, paired)
- **Pairing:** Same persona + same seed ensures paired comparison
- **Threshold:** p < 0.05 AND mean effect > 0.2 (on 1-5 scale)
- **Bootstrap:** 95% CI for effect size (1000 resamples)
- **Guard rails:** Reject if compliance rate decreases at all

### Cost Budget

- GPT-4o-mini: $0.15/1M input, $0.60/1M output
- GPT-4o: $2.50/1M input, $10.00/1M output
- Per conversation (~10 turns): ~$0.002
- Per iteration: ~$0.50
- 8 iterations: ~$4.00
- Meta-eval + overhead: ~$2.00
- **Estimated total: $6-8** (well within $20)

---

## Meta-Evaluation (Darwin Godel Machine)

Runs every 2 learning iterations. Four checks:

1. **Metric Reliability:** Evaluates same conversation twice, checks score variance. If mean difference > 1.0, reduces metric weight by 30%.
2. **Metric-Outcome Correlation:** Detects when a metric improvement doesn't correlate with actual outcome improvement. Expected catch: `tone_adherence` rewarding verbosity that hurts `efficiency`.
3. **Threshold Calibration:** If adoption rate > 80%, tightens p-value threshold. If < 10%, relaxes effect size requirement.
4. **Compliance Blind Spots:** Generates adversarial borderline compliance cases and tests the checker.

---

## Temporal Workflow Design

- **Workflow:** `CollectionsWorkflow` — one per borrower, ID: `collections-{borrower_id}`
- **Activities:** `run_assessment`, `run_resolution`, `run_final_notice`, `create_handoff`
- **Signals:** `receive_message` — borrower chat messages delivered via signal
- **Queries:** `get_state` — current stage, outcome, attempt number
- **Timeouts:** 30 min per chat stage, 48 hours for final notice deadline
- **Retries:** Assessment retried up to 3 times on `no_response`

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/workflow/start` | Start collections pipeline for a borrower |
| GET | `/workflow/{borrower_id}/status` | Get current workflow state |
| POST | `/workflow/{borrower_id}/cancel` | Cancel workflow |
| POST | `/chat/{borrower_id}` | Send borrower message |
| GET | `/chat/{borrower_id}/history` | Get conversation history |
| GET | `/admin/prompts/{agent_type}` | List prompt versions |
| GET | `/admin/prompts/{agent_type}/active` | Get active prompt |
| POST | `/admin/prompts/{agent_type}/rollback/{id}` | Rollback prompt |
| POST | `/webhook/vapi` | Vapi call events |
| GET | `/health` | Health check |
