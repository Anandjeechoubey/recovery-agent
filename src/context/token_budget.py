import tiktoken

_encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    tokens = _encoder.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return _encoder.decode(tokens[:max_tokens])


def enforce_budget(
    system_prompt: str,
    handoff_summary: str | None = None,
    max_total: int = 2000,
    max_handoff: int = 500,
) -> tuple[str, str | None]:
    """Enforce token budget constraints.

    Returns (system_prompt, handoff_summary) with handoff truncated if needed.
    Raises ValueError if system_prompt alone exceeds its allowed budget.
    """
    if handoff_summary:
        handoff_summary = truncate_to_tokens(handoff_summary, max_handoff)
        handoff_tokens = count_tokens(handoff_summary)
        prompt_budget = max_total - handoff_tokens
    else:
        handoff_tokens = 0
        prompt_budget = max_total

    prompt_tokens = count_tokens(system_prompt)
    if prompt_tokens > prompt_budget:
        raise ValueError(
            f"System prompt ({prompt_tokens} tokens) exceeds budget "
            f"({prompt_budget} tokens available after {handoff_tokens} token handoff)"
        )

    return system_prompt, handoff_summary
