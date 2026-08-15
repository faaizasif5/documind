"""add documents.user_id for per-user tenancy

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-15

Wipes existing global-corpus rows (no owner) before adding NOT NULL user_id.
Chunks are removed via FK ON DELETE CASCADE.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Legacy Phase 2–6 test docs (e.g. policy.pdf) have no owner; clear before NOT NULL.
    op.execute(sa.text("DELETE FROM documents"))

    op.add_column(
        "documents",
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(op.f("ix_documents_user_id"), "documents", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_column("documents", "user_id")
