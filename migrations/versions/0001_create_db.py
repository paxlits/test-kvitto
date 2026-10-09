"""create tariffs and payments tables

Revision ID: 0001
Revises:
Create Date: 2026-10-09

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False, unique=True),
        sa.Column("price", sa.Integer(), nullable=False),  # в копейках
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tariff_id",
            sa.Integer(),
            sa.ForeignKey("tariffs.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("installment_months", sa.Integer(), nullable=True),
        sa.Column("promo_code", sa.String(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),  # в копейках
        sa.Column("discount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("schedule", sa.JSON(), nullable=True),
        sa.Column("idempotency_key", sa.String(), unique=True, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("tariffs")