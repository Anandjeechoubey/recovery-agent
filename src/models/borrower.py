from dataclasses import dataclass, field


@dataclass
class PolicyRanges:
    min_settlement_pct: float = 0.40
    max_settlement_pct: float = 0.80
    max_installments: int = 12
    hardship_program: bool = True


@dataclass
class Borrower:
    id: str
    name: str
    account_last4: str
    total_debt: float
    debt_type: str  # "credit_card", "personal_loan", "auto_loan"
    days_past_due: int
    phone_number: str
    email: str
    policy: PolicyRanges = field(default_factory=PolicyRanges)
