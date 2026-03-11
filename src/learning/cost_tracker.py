from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path("data/reports")

# Approximate costs per 1M tokens (GPT-4o-mini, as of 2024)
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60

# GPT-4o costs
COST_PER_1M_INPUT_4O = 2.50
COST_PER_1M_OUTPUT_4O = 10.00


@dataclass
class CostTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_input_tokens_4o: int = 0
    total_output_tokens_4o: int = 0
    breakdown: list[dict] = field(default_factory=list)
    budget_usd: float = 20.0

    @property
    def total_cost_usd(self) -> float:
        mini_cost = (
            self.total_input_tokens * COST_PER_1M_INPUT / 1_000_000
            + self.total_output_tokens * COST_PER_1M_OUTPUT / 1_000_000
        )
        four_o_cost = (
            self.total_input_tokens_4o * COST_PER_1M_INPUT_4O / 1_000_000
            + self.total_output_tokens_4o * COST_PER_1M_OUTPUT_4O / 1_000_000
        )
        return mini_cost + four_o_cost

    @property
    def budget_remaining(self) -> float:
        return self.budget_usd - self.total_cost_usd

    @property
    def budget_exceeded(self) -> bool:
        return self.total_cost_usd >= self.budget_usd

    def record(
        self,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-4o-mini",
    ) -> None:
        if "4o-mini" in model:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
        else:
            self.total_input_tokens_4o += input_tokens
            self.total_output_tokens_4o += output_tokens

        self.breakdown.append({
            "operation": operation,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": self._calc_cost(input_tokens, output_tokens, model),
        })

    def _calc_cost(self, inp: int, out: int, model: str) -> float:
        if "4o-mini" in model:
            return inp * COST_PER_1M_INPUT / 1_000_000 + out * COST_PER_1M_OUTPUT / 1_000_000
        return inp * COST_PER_1M_INPUT_4O / 1_000_000 + out * COST_PER_1M_OUTPUT_4O / 1_000_000

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = DATA_DIR / "cost_report.json"
        with open(path, "w") as f:
            json.dump({
                "total_cost_usd": round(self.total_cost_usd, 4),
                "budget_usd": self.budget_usd,
                "budget_remaining_usd": round(self.budget_remaining, 4),
                "mini_input_tokens": self.total_input_tokens,
                "mini_output_tokens": self.total_output_tokens,
                "4o_input_tokens": self.total_input_tokens_4o,
                "4o_output_tokens": self.total_output_tokens_4o,
                "breakdown": self.breakdown,
            }, f, indent=2)

    def summary(self) -> str:
        return (
            f"Cost: ${self.total_cost_usd:.4f} / ${self.budget_usd:.2f} "
            f"({self.total_cost_usd / self.budget_usd * 100:.1f}% used)"
        )
