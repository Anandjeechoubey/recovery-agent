from langfuse import observe

from src.config import get_openai_client, settings
from src.context.token_budget import count_tokens, truncate_to_tokens
from src.models.conversation import Conversation, HandoffSummary

SUMMARIZE_PROMPT = """Summarize this debt collections conversation for the next agent.
The summary must preserve ALL of the following if present:
- Identity verification status (verified or not, partial account info used)
- Borrower's financial situation (income, employment, assets, hardship)
- Debt details discussed (amount, type, days past due)
- Offers made and borrower's response to each
- Objections raised by the borrower
- Borrower's emotional state and tone
- Any commitments or deadlines mentioned
- Whether borrower requested to stop contact
- Any compliance-relevant statements

Be factual and concise. Use bullet points. No filler.

Conversation transcript:
{transcript}"""


@observe()
async def summarize_for_handoff(
    conversations: list[Conversation],
    max_tokens: int = 500,
) -> HandoffSummary:
    transcript_parts = []
    for conv in conversations:
        transcript_parts.append(f"[{conv.agent_type.upper()} STAGE]")
        transcript_parts.append(conv.to_transcript())

    transcript = "\n\n".join(transcript_parts)
    prompt = SUMMARIZE_PROMPT.format(transcript=transcript)

    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.azure_openai_deployment_mini,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2,
    )

    summary_text = response.choices[0].message.content or ""

    # Enforce hard token limit
    summary_text = truncate_to_tokens(summary_text, max_tokens)

    return HandoffSummary(
        content=summary_text,
        token_count=count_tokens(summary_text),
        source_agent=conversations[-1].agent_type,
    )
