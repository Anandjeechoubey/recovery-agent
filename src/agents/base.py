from __future__ import annotations

from openai import AsyncOpenAI

from src.config import settings
from src.context.token_budget import count_tokens, enforce_budget
from src.models.borrower import Borrower
from src.models.conversation import Conversation, HandoffSummary, Message


class BaseAgent:
    agent_type: str = ""
    default_system_prompt: str = ""

    def __init__(self, system_prompt: str | None = None):
        self.system_prompt = system_prompt or self.default_system_prompt
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    def build_messages(
        self,
        conversation: Conversation,
        borrower: Borrower,
        handoff: HandoffSummary | None = None,
    ) -> list[dict]:
        """Build OpenAI messages with token budget enforcement."""
        prompt = self._render_system_prompt(borrower)

        handoff_text = handoff.content if handoff else None
        prompt, handoff_text = enforce_budget(
            prompt,
            handoff_text,
            max_total=settings.max_total_tokens,
            max_handoff=settings.max_handoff_tokens,
        )

        messages: list[dict] = []

        # System prompt
        system_content = prompt
        if handoff_text:
            system_content += f"\n\n## CONTEXT FROM PRIOR STAGES\n{handoff_text}"
        messages.append({"role": "system", "content": system_content})

        # Conversation history
        for msg in conversation.messages:
            role = "assistant" if msg.role == "agent" else "user"
            messages.append({"role": role, "content": msg.content})

        return messages

    def _render_system_prompt(self, borrower: Borrower) -> str:
        """Inject borrower details into system prompt template."""
        return self.system_prompt.format(
            borrower_name=borrower.name,
            account_last4=borrower.account_last4,
            total_debt=f"${borrower.total_debt:,.2f}",
            debt_type=borrower.debt_type.replace("_", " "),
            days_past_due=borrower.days_past_due,
            min_settlement_pct=int(borrower.policy.min_settlement_pct * 100),
            max_settlement_pct=int(borrower.policy.max_settlement_pct * 100),
            max_installments=borrower.policy.max_installments,
        )

    async def respond(
        self,
        conversation: Conversation,
        borrower: Borrower,
        handoff: HandoffSummary | None = None,
    ) -> Message:
        messages = self.build_messages(conversation, borrower, handoff)

        response = await self.client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )

        content = response.choices[0].message.content or ""
        token_count = count_tokens(content)
        return conversation.add_message("agent", content, token_count)

    async def generate_opening(
        self,
        conversation: Conversation,
        borrower: Borrower,
        handoff: HandoffSummary | None = None,
    ) -> Message:
        """Generate the agent's first message."""
        return await self.respond(conversation, borrower, handoff)
