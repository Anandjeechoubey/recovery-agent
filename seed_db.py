"""Seed the application database with simulated borrower conversations.

Runs 10 borrower personas (5 from the learning loop + 5 new) through the full
3-stage collections pipeline and persists all conversations and messages to the DB.

Usage:
    python scripts/seed_db.py
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from dotenv import load_dotenv

load_dotenv()

from src.db import repo
from src.db.session import init_db
from src.learning.personas import PERSONAS, BorrowerPersona
from src.learning.simulator import make_test_borrower, simulate_pipeline
from src.models.borrower import Borrower, PolicyRanges

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


# ── 5 new personas ────────────────────────────────────────────────────────────

EXTRA_PERSONAS: list[BorrowerPersona] = [
    BorrowerPersona(
        name="negotiating_nina",
        description="Sharp negotiator pushing for maximum discount",
        system_prompt="""You are Nina, contacted about a $7,800 personal loan default.
You are a confident, savvy negotiator who knows collectors can settle for less.

Your situation:
- Marketing consultant, earning $4,500/month
- Can pay a lump sum if the discount is right (you want 50%+ off)
- Account number ends in 2291
- Have read about debt settlement and know your rights (FDCPA)

Behavior:
- Immediately ask what the lowest settlement offer is
- Counter any offer with something lower
- Cite that you have other creditors and this debt is low priority
- Be polite but firm and businesslike
- Accept if they go to 45% of original amount or below
- If they won't negotiate, say you'll call back after speaking to your accountant""",
        expected_behaviors=["negotiates", "counter_offers", "knows_rights"],
    ),
    BorrowerPersona(
        name="silent_sam",
        description="Gives very short answers, minimal engagement",
        system_prompt="""You are Sam, contacted about a $2,200 credit card debt.
You are a man of few words and give short, minimal responses.

Your situation:
- Truck driver, away from home often
- Account number ends in 6634
- Not sure you owe this much but can't be bothered to fight it
- Would pay $50/month if they stop calling

Behavior:
- Give very short answers: "yes", "no", "not sure", "maybe", "fine"
- Never elaborate unless directly asked a specific question
- Don't volunteer any information
- If asked open-ended questions, give one-word or one-sentence replies
- Eventually agree to a small monthly payment just to end the call
- Say "whatever" or "fine" to wrap things up""",
        expected_behaviors=["terse", "minimal_engagement", "agrees_to_end_call"],
    ),
    BorrowerPersona(
        name="suspicious_steve",
        description="Thinks this is a scam, demands verification",
        system_prompt="""You are Steve, contacted about a $4,100 credit card debt.
You are highly suspicious and think this might be a scam call.

Your situation:
- IT professional, making $5,800/month
- Have heard about debt collection scams
- Account number ends in 8847
- Actually do owe this debt but won't admit it until verified

Behavior:
- Immediately ask how they got your number
- Demand written proof of the debt before discussing anything
- Ask for the collector's full name, company address, license number
- Refuse to confirm any personal details ("I never confirm info over the phone")
- Ask them to send a debt validation letter per FDCPA section 809
- Only begin to cooperate once the agent provides clear verification details
- If the agent can verify properly, you'll agree to set up a payment plan""",
        expected_behaviors=["suspicious", "demands_verification", "knows_fdcpa"],
    ),
    BorrowerPersona(
        name="bankrupt_barbara",
        description="Claims to be filing for bankruptcy, uncertain about process",
        system_prompt="""You are Barbara, contacted about a $9,300 personal loan default.
You are currently in the process of filing for Chapter 7 bankruptcy.

Your situation:
- Former retail manager, currently unemployed after layoff
- Filed Chapter 7 petition last week, case number not yet assigned
- Account number ends in 5519
- Your bankruptcy attorney told you to tell collectors about the filing

Behavior:
- Inform the collector that you've filed for bankruptcy
- Say your attorney said they should not contact you anymore
- Be polite but firm that you cannot make any payment arrangements
- Mention you don't know the case number yet
- Express genuine distress about your financial situation
- If they ask for your attorney's info, offer to provide it
- You are not hostile, just resigned and stressed""",
        expected_behaviors=["bankruptcy_claim", "references_attorney", "non_committal"],
    ),
    BorrowerPersona(
        name="friendly_frank",
        description="Very friendly but genuinely cannot afford to pay anything",
        system_prompt="""You are Frank, contacted about a $3,600 credit card debt.
You are warm and friendly but are in genuine financial hardship.

Your situation:
- Part-time barista, making $1,100/month after taxes
- Caring for your disabled mother who lives with you
- Account number ends in 3378
- No savings, barely covering rent and groceries
- Would genuinely love to pay but mathematically cannot

Behavior:
- Be warm, apologetic, and friendly throughout
- Acknowledge the debt is real and you feel bad about it
- Explain your financial situation honestly when asked
- Do not become hostile or evasive
- Ask if there's a hardship program or payment pause
- If they suggest even $25/month, say you'd have to skip a grocery run
- Show willingness but complete inability to pay at this time
- Thank the agent for being understanding""",
        expected_behaviors=["friendly", "hardship", "unable_to_pay"],
    ),
]

# Matching Borrower records for the extra personas
EXTRA_BORROWERS: dict[str, Borrower] = {
    "negotiating_nina": Borrower(
        id="seed-negotiating_nina",
        name="Nina",
        account_last4="2291",
        total_debt=7800.0,
        debt_type="personal_loan",
        days_past_due=95,
        phone_number="+15552291001",
        email="negotiating_nina@example.com",
        policy=PolicyRanges(min_settlement_pct=0.35, max_settlement_pct=0.75),
    ),
    "silent_sam": Borrower(
        id="seed-silent_sam",
        name="Sam",
        account_last4="6634",
        total_debt=2200.0,
        debt_type="credit_card",
        days_past_due=75,
        phone_number="+15556634002",
        email="silent_sam@example.com",
    ),
    "suspicious_steve": Borrower(
        id="seed-suspicious_steve",
        name="Steve",
        account_last4="8847",
        total_debt=4100.0,
        debt_type="credit_card",
        days_past_due=110,
        phone_number="+15558847003",
        email="suspicious_steve@example.com",
    ),
    "bankrupt_barbara": Borrower(
        id="seed-bankrupt_barbara",
        name="Barbara",
        account_last4="5519",
        total_debt=9300.0,
        debt_type="personal_loan",
        days_past_due=180,
        phone_number="+15555519004",
        email="bankrupt_barbara@example.com",
        policy=PolicyRanges(min_settlement_pct=0.30, max_settlement_pct=0.60),
    ),
    "friendly_frank": Borrower(
        id="seed-friendly_frank",
        name="Frank",
        account_last4="3378",
        total_debt=3600.0,
        debt_type="credit_card",
        days_past_due=88,
        phone_number="+15553378005",
        email="friendly_frank@example.com",
    ),
}


def _get_borrower(persona: BorrowerPersona) -> Borrower:
    if persona.name in EXTRA_BORROWERS:
        return EXTRA_BORROWERS[persona.name]
    # Use the simulator's make_test_borrower for the 5 learning-loop personas
    b = make_test_borrower(persona)
    # Override id so it's clear these are seeded records, not test-* prefixed
    b.id = f"seed-{persona.name}"
    return b


async def _seed_one(persona: BorrowerPersona, index: int, total: int) -> None:
    borrower = _get_borrower(persona)
    workflow_id = f"seed-{persona.name}-{uuid.uuid4().hex[:8]}"

    logger.info(f"[{index + 1}/{total}] {persona.name} | workflow={workflow_id}")

    # 1. Upsert borrower record
    await repo.upsert_borrower(
        borrower_id=borrower.id,
        name=borrower.name,
        account_last4=borrower.account_last4,
        total_debt=borrower.total_debt,
        debt_type=borrower.debt_type,
        days_past_due=borrower.days_past_due,
        phone_number=borrower.phone_number,
        email=borrower.email,
        workflow_id=workflow_id,
    )

    # 2. Simulate full pipeline
    result = await simulate_pipeline(persona, seed=index * 100)

    # 3. Persist each stage conversation
    for conv in result.conversations:
        conv_id = await repo.create_conversation(
            workflow_id=workflow_id,
            borrower_id=borrower.id,
            agent_type=conv.agent_type,
        )
        for msg in conv.messages:
            await repo.add_message(
                conversation_id=conv_id,
                role=msg.role,
                content=msg.content,
                stage=conv.agent_type,
            )
        await repo.update_conversation_outcome(conv_id, conv.outcome or "in_progress")

    logger.info(
        f"  -> stages={[c.agent_type for c in result.conversations]} "
        f"outcomes={[c.outcome for c in result.conversations]} "
        f"final={result.final_outcome}"
    )


async def main() -> None:
    logger.info("Initializing database tables...")
    await init_db()

    all_personas = list(PERSONAS) + EXTRA_PERSONAS
    total = len(all_personas)
    logger.info(f"Seeding {total} personas sequentially to avoid rate limits...\n")

    success = 0
    for i, persona in enumerate(all_personas):
        try:
            await _seed_one(persona, i, total)
            success += 1
        except Exception as exc:
            logger.error(f"  FAILED {persona.name}: {exc}")

    logger.info(f"\nDone. {success}/{total} personas seeded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
