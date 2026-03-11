# Recovery Agents

Self-learning AI debt collections system with three specialized agents orchestrated by Temporal.

## Overview

A post-default debt collections pipeline with three AI agents operating behind a single continuous borrower experience:

1. **Assessment Agent (Chat)** — Verifies identity, gathers financial situation. Cold and clinical.
2. **Resolution Agent (Voice)** — Negotiates settlement via phone call (Vapi). Transactional dealmaker.
3. **Final Notice Agent (Chat)** — Delivers consequences and final offer with hard deadline.

Each agent autonomously improves its own prompts through a self-learning loop with statistical rigor and compliance preservation. A meta-evaluation layer (Darwin Godel Machine) evaluates and improves the evaluation methodology itself.

## Tech Stack

- **Language:** Python 3.11+
- **LLM:** OpenAI (GPT-4o for agents, GPT-4o-mini for simulation/eval)
- **Voice:** Vapi
- **Orchestration:** Temporal
- **API:** FastAPI
- **Infrastructure:** Docker Compose

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your OPENAI_API_KEY (minimum required)

# 2. Start all services
docker compose up -d

# 3. Verify
curl http://localhost:8000/health
```

Services:
- **API:** http://localhost:8000 (Swagger docs at /docs)
- **Temporal UI:** http://localhost:8080

## Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests (28 tests)
make test

# Start Temporal infrastructure
docker compose up -d postgresql temporal temporal-ui

# Start API (terminal 1)
make dev-api

# Start worker (terminal 2)
make dev-worker
```

## Usage

```bash
# Start a collections workflow
curl -X POST http://localhost:8000/workflow/start \
  -H "Content-Type: application/json" \
  -d '{"borrower_id":"B001","name":"John Doe","account_last4":"7823","total_debt":4500,"debt_type":"credit_card","days_past_due":90}'

# Send a chat message
curl -X POST http://localhost:8000/chat/B001 \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, what is this about?"}'

# Check status
curl http://localhost:8000/workflow/B001/status
```

## Self-Learning Loop

Run the autonomous prompt optimization loop:

```bash
make learn    # Run learning loop (~$6-8 of API spend)
make report   # Generate evolution report
```

The learning loop:
- Simulates conversations with 5 borrower personas (cooperative, combative, evasive, confused, distressed)
- Evaluates with quantitative metrics (LLM-as-judge, 1-5 scale)
- Proposes targeted prompt mutations based on failure analysis
- Adopts changes only if statistically significant (Wilcoxon signed-rank, p < 0.05) with no compliance regression
- Meta-evaluates its own evaluation methodology every 2 iterations

All data saved to `data/` for reproducibility.

## Key Constraints

- **Token budget:** 2000 tokens per agent (system prompt + handoff context), 500 tokens max for handoff summaries
- **Learning budget:** $20 total LLM API spend for the entire loop
- **Compliance:** 8 rules enforced at all times, including after prompt updates

## Project Structure

```
src/
├── agents/       # 3 specialized agents + compliance checker
├── context/      # Token budget enforcement + handoff summarization
├── workflow/     # Temporal workflow + activities
├── api/          # FastAPI endpoints
├── voice/        # Vapi integration
└── learning/     # Self-learning loop, evaluation, meta-evaluation
```

## Documentation

See `knowledge/` for detailed documentation:
- [Implementation Plan](knowledge/01-implementation-plan.md)
- [Production Setup Guide](knowledge/02-production-setup.md)
- [Future Work](knowledge/03-future-work.md)
