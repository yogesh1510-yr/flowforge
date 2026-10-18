"""create the shared analytics order projection

Revision ID: 35a4c91f72de
Revises: 8dce30b345a5
Create Date: 2026-10-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "35a4c91f72de"
down_revision: Union[str, Sequence[str], None] = "8dce30b345a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    op.create_table(
        "order_state",
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(50), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("shipping_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("order_age_seconds", sa.Numeric(14, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_lsn", sa.BigInteger(), nullable=False),
        sa.Column("source_txid", sa.BigInteger(), nullable=True),
        sa.Column("source_topic", sa.String(249), nullable=False),
        sa.Column("source_partition", sa.Integer(), nullable=False),
        sa.Column("source_offset", sa.BigInteger(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "projected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("subtotal >= 0", name="ck_order_state_subtotal_nonnegative"),
        sa.CheckConstraint("tax_amount >= 0", name="ck_order_state_tax_nonnegative"),
        sa.CheckConstraint("shipping_amount >= 0", name="ck_order_state_shipping_nonnegative"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_order_state_discount_nonnegative"),
        sa.CheckConstraint("total_amount >= 0", name="ck_order_state_total_nonnegative"),
        sa.PrimaryKeyConstraint("order_id"),
        sa.UniqueConstraint("order_number", name="uq_order_state_order_number"),
        schema="analytics",
    )
    op.create_index(
        "ix_order_state_updated_at",
        "order_state",
        ["updated_at"],
        schema="analytics",
    )
    op.create_index(
        "ix_order_state_status_currency",
        "order_state",
        ["status", "currency"],
        schema="analytics",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_order_state_status_currency", table_name="order_state", schema="analytics"
    )
    op.drop_index(
        "ix_order_state_updated_at", table_name="order_state", schema="analytics"
    )
    op.drop_table("order_state", schema="analytics")
