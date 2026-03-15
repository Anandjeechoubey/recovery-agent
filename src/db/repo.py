"""Database repository — query and persistence functions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.models import BorrowerRow, ConversationRow, MessageRow
from src.db.session import get_session


# ── Borrowers ──────────────────────────────────────────────────


async def upsert_borrower(
    borrower_id: str,
    name: str,
    account_last4: str,
    total_debt: float,
    debt_type: str,
    days_past_due: int,
    phone_number: str = "",
    email: str = "",
    workflow_id: str | None = None,
    current_stage: str | None = None,
    outcome: str | None = None,
) -> BorrowerRow:
    async with get_session() as session:
        result = await session.execute(
            select(BorrowerRow).where(BorrowerRow.borrower_id == borrower_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.name = name
            row.total_debt = total_debt
            row.debt_type = debt_type
            row.days_past_due = days_past_due
            row.phone_number = phone_number
            row.email = email
            if workflow_id:
                row.workflow_id = workflow_id
            if current_stage is not None:
                row.current_stage = current_stage
            if outcome is not None:
                row.outcome = outcome
        else:
            row = BorrowerRow(
                borrower_id=borrower_id,
                name=name,
                account_last4=account_last4,
                total_debt=total_debt,
                debt_type=debt_type,
                days_past_due=days_past_due,
                phone_number=phone_number,
                email=email,
                workflow_id=workflow_id,
                current_stage=current_stage,
                outcome=outcome,
            )
            session.add(row)
        await session.commit()
        return row


async def list_borrowers() -> list[dict]:
    async with get_session() as session:
        result = await session.execute(
            select(BorrowerRow).order_by(BorrowerRow.created_at.desc())
        )
        rows = result.scalars().all()
        return [
            {
                "borrower_id": r.borrower_id,
                "name": r.name,
                "total_debt": r.total_debt,
                "debt_type": r.debt_type,
                "days_past_due": r.days_past_due,
                "phone_number": r.phone_number,
                "email": r.email,
                "workflow_id": r.workflow_id,
                "current_stage": r.current_stage,
                "outcome": r.outcome,
                "started_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


async def get_borrower(borrower_id: str) -> dict | None:
    async with get_session() as session:
        result = await session.execute(
            select(BorrowerRow).where(BorrowerRow.borrower_id == borrower_id)
        )
        r = result.scalar_one_or_none()
        if not r:
            return None
        return {
            "borrower_id": r.borrower_id,
            "name": r.name,
            "total_debt": r.total_debt,
            "debt_type": r.debt_type,
            "days_past_due": r.days_past_due,
            "phone_number": r.phone_number,
            "email": r.email,
            "workflow_id": r.workflow_id,
            "current_stage": r.current_stage,
            "outcome": r.outcome,
            "started_at": r.created_at.isoformat() if r.created_at else None,
        }


async def delete_borrower(borrower_id: str) -> bool:
    """Delete a borrower and all related conversations/messages (cascade)."""
    async with get_session() as session:
        result = await session.execute(
            select(BorrowerRow).where(BorrowerRow.borrower_id == borrower_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await session.delete(row)
        await session.commit()
        return True


# ── Conversations ──────────────────────────────────────────────


async def create_conversation(
    workflow_id: str,
    borrower_id: str,
    agent_type: str,
) -> int:
    """Create a conversation row and return its id."""
    async with get_session() as session:
        row = ConversationRow(
            workflow_id=workflow_id,
            borrower_id=borrower_id,
            agent_type=agent_type,
        )
        session.add(row)
        await session.commit()
        return row.id


async def update_conversation_outcome(conversation_id: int, outcome: str) -> None:
    async with get_session() as session:
        result = await session.execute(
            select(ConversationRow).where(ConversationRow.id == conversation_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.outcome = outcome
            row.ended_at = datetime.now(timezone.utc)
            await session.commit()


# ── Messages ───────────────────────────────────────────────────


async def add_message(
    conversation_id: int,
    role: str,
    content: str,
    stage: str,
) -> int:
    """Insert a message and return its id."""
    async with get_session() as session:
        row = MessageRow(
            conversation_id=conversation_id,
            role=role,
            content=content,
            stage=stage,
        )
        session.add(row)
        await session.commit()
        return row.id


async def get_conversation_messages(workflow_id: str) -> list[dict]:
    """Get all messages for a workflow, ordered by timestamp."""
    async with get_session() as session:
        result = await session.execute(
            select(ConversationRow)
            .where(ConversationRow.workflow_id == workflow_id)
            .options(selectinload(ConversationRow.messages))
            .order_by(ConversationRow.started_at)
        )
        convs = result.scalars().all()
        messages = []
        for conv in convs:
            for msg in conv.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                    "stage": msg.stage,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                })
        return messages


async def get_borrower_conversations(borrower_id: str) -> list[dict]:
    """Get all conversations for a borrower with messages."""
    async with get_session() as session:
        result = await session.execute(
            select(ConversationRow)
            .where(ConversationRow.borrower_id == borrower_id)
            .options(selectinload(ConversationRow.messages))
            .order_by(ConversationRow.started_at)
        )
        convs = result.scalars().all()
        return [
            {
                "id": conv.id,
                "workflow_id": conv.workflow_id,
                "agent_type": conv.agent_type,
                "outcome": conv.outcome,
                "started_at": conv.started_at.isoformat() if conv.started_at else None,
                "ended_at": conv.ended_at.isoformat() if conv.ended_at else None,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "stage": m.stage,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    }
                    for m in conv.messages
                ],
            }
            for conv in convs
        ]
