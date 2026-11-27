"""durable ingestion: job queue, progress columns, idempotent chunk inserts

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-27

- documents: processed_chunks, total_chunks, error_message
- chunks: UNIQUE (document_id, chunk_index); drops the now-redundant
  ix_chunks_document_id (the unique index's leading column covers it)
- ingestion_jobs: Postgres-backed queue claimed with FOR UPDATE SKIP LOCKED
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_job_status = sa.Enum("queued", "running", "succeeded", "failed", name="ingestion_job_status")


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("processed_chunks", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("documents", sa.Column("total_chunks", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))

    # Backfill progress for documents ingested before v2.
    op.execute(
        sa.text(
            """
            UPDATE documents d
            SET processed_chunks = c.n, total_chunks = c.n
            FROM (SELECT document_id, count(*) AS n FROM chunks GROUP BY document_id) c
            WHERE c.document_id = d.id
            """
        )
    )
    # Pre-v2 in-flight uploads lived only in process memory; their bytes are gone.
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET status = 'failed',
                error_message = 'Processing was interrupted. Please upload the file again.'
            WHERE status = 'processing'
            """
        )
    )

    op.create_unique_constraint(
        op.f("uq_chunks_document_id"), "chunks", ["document_id", "chunk_index"]
    )
    op.drop_index(op.f("ix_chunks_document_id"), table_name="chunks")

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", _job_status, server_default="queued", nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("lease_owner", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_ingestion_jobs_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_jobs")),
        sa.UniqueConstraint("document_id", name=op.f("uq_ingestion_jobs_document_id")),
    )
    op.create_index(
        "ix_ingestion_jobs_status_next_run_at",
        "ingestion_jobs",
        ["status", "next_run_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_status_next_run_at", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.execute("DROP TYPE IF EXISTS ingestion_job_status")
    op.create_index(op.f("ix_chunks_document_id"), "chunks", ["document_id"])
    op.drop_constraint(op.f("uq_chunks_document_id"), "chunks", type_="unique")
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "total_chunks")
    op.drop_column("documents", "processed_chunks")
