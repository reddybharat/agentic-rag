"""scope documents and chunks to the owner instead of a session

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("owner_id", sa.String(64), nullable=True))
    op.add_column("chunks", sa.Column("owner_id", sa.String(64), nullable=True))
    op.execute(
        "UPDATE documents SET owner_id = sessions.owner_id "
        "FROM sessions WHERE sessions.id = documents.session_id"
    )
    # The same PDF may have been uploaded to several sessions; keep the earliest copy per owner.
    op.execute(
        "DELETE FROM documents d USING documents keep "
        "WHERE d.owner_id = keep.owner_id AND d.sha256 = keep.sha256 "
        "AND (d.created_at, d.id) > (keep.created_at, keep.id)"
    )
    op.execute(
        "UPDATE chunks SET owner_id = documents.owner_id "
        "FROM documents WHERE documents.id = chunks.document_id"
    )
    op.alter_column("documents", "owner_id", nullable=False)
    op.alter_column("chunks", "owner_id", nullable=False)
    # Dropping the column also drops its indexes and the (session_id, sha256) unique constraint.
    op.drop_column("documents", "session_id")
    op.drop_column("chunks", "session_id")
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_chunks_owner_id", "chunks", ["owner_id"])
    op.create_unique_constraint("uq_documents_owner_id_sha256", "documents", ["owner_id", "sha256"])


def downgrade() -> None:
    # Library documents belong to no session, so they cannot be mapped back and are removed.
    op.execute("DELETE FROM documents")
    op.drop_constraint("uq_documents_owner_id_sha256", "documents")
    op.drop_column("documents", "owner_id")
    op.drop_column("chunks", "owner_id")
    op.add_column(
        "documents",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.add_column("chunks", sa.Column("session_id", sa.Uuid(), nullable=False))
    op.create_index("ix_documents_session_id", "documents", ["session_id"])
    op.create_index("ix_chunks_session_id", "chunks", ["session_id"])
    op.create_unique_constraint(
        "uq_documents_session_id_sha256", "documents", ["session_id", "sha256"]
    )
