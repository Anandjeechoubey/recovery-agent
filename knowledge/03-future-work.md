# Future Work and Possibilities

## What Needs to Be Incorporated

### 1. Persistent Conversation Storage

Currently conversations live in-memory during workflow execution. For production:

- Add a database (PostgreSQL or SQLite) to persist all conversation messages
- Store conversation history per borrower with timestamps
- Enable the `/chat/{borrower_id}/history` endpoint to return real historical data
- Required for audit trail and regulatory compliance

### 2. Real-Time Chat Response Delivery

The current chat flow sends a signal to the Temporal workflow and returns immediately. The borrower doesn't get the agent's response in the same HTTP request.

Options to implement:
- **WebSocket endpoint** — bidirectional real-time messaging
- **Server-Sent Events (SSE)** — agent streams responses back
- **Polling** — client polls for new messages (simplest, worst UX)
- **Callback/webhook** — notify a client URL when agent responds

### 3. Authentication & Authorization

- API key or JWT-based auth for all endpoints
- Borrower identity verification before allowing chat access
- Admin endpoints protected separately
- Rate limiting per borrower to prevent abuse

### 4. Vapi Voice Integration Hardening

The current Vapi integration is functional but needs:
- Robust error handling for failed calls (network issues, Vapi outages)
- Call recording storage and retrieval
- Real-time transcript streaming back to the workflow (not just end-of-call)
- Fallback to simulated mode if Vapi is unavailable
- DTMF input handling for payment confirmations

### 5. Observability

- Structured logging (JSON format) with correlation IDs per borrower
- OpenTelemetry tracing across API → Temporal → OpenAI calls
- Prometheus metrics: conversation durations, resolution rates, API latencies
- Alerting on compliance violations, budget overruns, workflow failures

### 6. Multi-Borrower Concurrent Handling

The current `ConversationManager` uses in-memory queues which don't survive restarts. For production:
- Use Temporal's built-in signal mechanism end-to-end
- Or use Redis pub/sub for cross-process message passing
- Ensure the worker can handle hundreds of concurrent workflows

---

## Improvements to the Learning Loop

### 7. More Sophisticated Borrower Simulator

Current personas are static. Improvements:
- **Dynamic personas** — sample financial situations from distributions (income, debt amount, days past due)
- **Multi-turn memory** — persona that remembers what it said earlier and evolves behavior
- **Adversarial personas** — specifically designed to break agent compliance
- **Cultural/demographic variety** — different communication styles, language proficiency levels

### 8. Richer Evaluation Metrics

Current metrics are LLM-judged on a 1-5 scale. Improvements:
- **Outcome-based metrics** — actual resolution rate, time to resolution, settlement amount achieved
- **Conversation efficiency** — number of turns to reach resolution
- **Borrower satisfaction proxy** — LLM-judged from borrower perspective
- **A/B testing on live traffic** — gradually roll out new prompts to a percentage of real conversations
- **Human-in-the-loop evaluation** — periodically have humans score conversations to calibrate LLM judge

### 9. Multi-Objective Optimization

Currently optimizing one metric at a time. Better approaches:
- **Pareto optimization** — find prompt changes that improve multiple metrics without degrading any
- **Constrained optimization** — maximize resolution rate subject to compliance ≥ 95%
- **Bayesian optimization** — more sample-efficient than random mutation + evaluation

### 10. Prompt Search Strategy

Current approach: analyze weakest metric, propose one mutation. Improvements:
- **Population-based** — maintain a pool of 3-5 candidate prompts, evolve the population
- **Crossover** — combine good sections from multiple high-performing prompts
- **Fine-grained mutations** — modify specific sections (opening, objection handling, closing) independently
- **Template-based prompts** — separate structure from content for more targeted optimization

### 11. Improved Meta-Evaluation

Current meta-eval checks 4 things. Extensions:
- **Evaluator calibration** — compare LLM judge scores with human scores, detect systematic bias
- **Metric independence** — detect and decorrelate redundant metrics
- **Evaluation prompt optimization** — the meta-evaluator could optimize the evaluation prompts themselves
- **Sample size recommendation** — dynamically adjust conversations_per_eval based on observed variance

---

## System-Level Enhancements

### 12. Non-Linear Pipeline

The PRD mentions that the 3-stage linear pipeline might be suboptimal. Alternatives:

- **Conditional routing** — skip Resolution (voice) for borrowers who prefer text, skip Final Notice if deal agreed
- **Parallel tracks** — send chat and voice simultaneously, use whichever gets engagement first
- **Adaptive escalation** — if Assessment detects high willingness, go straight to Resolution with a gentle tone
- **Re-engagement loops** — if borrower goes silent, wait N days and re-enter the pipeline

### 13. Dynamic Agent Tone

Instead of fixed personalities per agent, adjust tone based on:
- Borrower's detected emotional state
- Previous interaction outcomes
- Debt severity and borrower's payment history
- Time pressure (how close to legal escalation deadline)

### 14. Multi-Language Support

- Detect borrower's preferred language from initial messages
- Switch agent prompts to that language
- Ensure compliance rules are enforced across languages
- Vapi supports multiple languages for voice calls

### 15. Payment Processing Integration

Currently the system only negotiates — it doesn't process payments:
- Integrate with a payment gateway (Stripe, Plaid)
- Enable in-chat payment links
- Confirm payment and close workflow automatically
- Handle failed payments and retry logic

### 16. CRM Integration

- Sync borrower data from existing CRM (Salesforce, HubSpot)
- Update account status based on workflow outcomes
- Feed resolution data back for portfolio analysis
- Trigger workflows automatically based on account aging

---

## Compliance Enhancements

### 17. Regulatory Compliance

- **FDCPA compliance** — Fair Debt Collection Practices Act (US)
- **TCPA compliance** — Telephone Consumer Protection Act (calling hours, consent)
- **State-specific rules** — different states have different collection rules
- **GDPR/CCPA** — data retention, right to deletion, data portability
- **Time-of-day restrictions** — don't call before 8am or after 9pm local time

### 18. Audit and Reporting

- Full conversation audit logs exportable as CSV/JSON
- Compliance violation reports per agent, per period
- Resolution rate dashboards with breakdowns by debt type, amount, persona
- Regulatory-ready reporting for examiner requests

---

## Infrastructure

### 19. Horizontal Scaling

- Multiple Temporal workers behind a load balancer
- Stateless API servers (conversation state in Temporal, not in memory)
- Redis for cross-worker message passing
- Auto-scaling based on workflow queue depth

### 20. High Availability

- Temporal cluster mode with multiple frontend servers
- Database replication for Temporal persistence
- API server redundancy with health check routing
- Graceful degradation when OpenAI or Vapi is down

### 21. CI/CD Pipeline

- GitHub Actions for automated testing on PR
- Docker image build and push to registry
- Staging environment for testing prompt changes before production
- Canary deployments for new prompt versions

---

## Research Directions

### 22. Fine-Tuned Models

Instead of prompt engineering, fine-tune a small model on high-scoring conversations:
- Collect best conversations from the learning loop
- Fine-tune GPT-4o-mini or an open-source model
- Dramatically reduce inference cost and latency
- Risk: less flexibility, harder to update

### 23. Reinforcement Learning from Conversation Outcomes

- Define reward = resolution amount / conversation length
- Use RLHF or DPO to train agent responses directly
- Potentially much more effective than prompt mutation
- Requires significant conversation volume

### 24. Voice Emotion Detection

- Analyze borrower's voice tone during Resolution calls
- Detect frustration, confusion, distress in real-time
- Automatically trigger hardship referral or tone adjustment
- Vapi provides some emotion detection capabilities

### 25. Conversation Branching

Instead of a single linear conversation flow:
- Agent presents multiple options and the conversation branches
- Each branch has different follow-up strategies
- Tree-of-thought approach to negotiation
- Could significantly improve resolution rates for complex cases
