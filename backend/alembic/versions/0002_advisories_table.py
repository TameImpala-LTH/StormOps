"""advisories_table

Revision ID: 0002_advisories_table
Revises: 0001_initial_schema
Create Date: 2026-09-18 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_advisories_table'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'advisories',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=255), nullable=False),
        sa.Column('authority', sa.String(length=50), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('hazard_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('official_level', sa.String(length=100), nullable=True),
        sa.Column('urgency', sa.String(length=20), nullable=True),
        sa.Column('certainty', sa.String(length=20), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('granularity', sa.String(length=20), nullable=False, server_default=sa.text("'district'")),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('subdivision', sa.String(length=100), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('radius_km', sa.Float(), nullable=True),
        sa.Column('polygon_geojson', sa.Text(), nullable=True),
        sa.Column('headline', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('action_guidance', sa.Text(), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('authority', 'source_id', name='uq_advisory_authority_source_id')
    )
    op.create_index('ix_advisories_source_id', 'advisories', ['source_id'], unique=False)
    op.create_index('ix_advisories_authority', 'advisories', ['authority'], unique=False)
    op.create_index('ix_advisories_hazard_type', 'advisories', ['hazard_type'], unique=False)
    op.create_index('ix_advisories_severity', 'advisories', ['severity'], unique=False)
    op.create_index('ix_advisories_effective_at', 'advisories', ['effective_at'], unique=False)
    op.create_index('ix_advisories_expires_at', 'advisories', ['expires_at'], unique=False)
    op.create_index('ix_advisories_is_active', 'advisories', ['is_active'], unique=False)
    op.create_index('ix_advisories_state', 'advisories', ['state'], unique=False)
    op.create_index('ix_advisories_district', 'advisories', ['district'], unique=False)
    op.create_index('ix_advisories_subdivision', 'advisories', ['subdivision'], unique=False)
    op.create_index('ix_advisories_active_expiry', 'advisories', ['is_active', 'expires_at'], unique=False)
    op.create_index('ix_advisories_geo_lookup', 'advisories', ['state', 'district', 'is_active'], unique=False)
    op.create_index('ix_advisories_severity_active', 'advisories', ['severity', 'is_active'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_advisories_severity_active', table_name='advisories')
    op.drop_index('ix_advisories_geo_lookup', table_name='advisories')
    op.drop_index('ix_advisories_active_expiry', table_name='advisories')
    op.drop_index('ix_advisories_subdivision', table_name='advisories')
    op.drop_index('ix_advisories_district', table_name='advisories')
    op.drop_index('ix_advisories_state', table_name='advisories')
    op.drop_index('ix_advisories_is_active', table_name='advisories')
    op.drop_index('ix_advisories_expires_at', table_name='advisories')
    op.drop_index('ix_advisories_effective_at', table_name='advisories')
    op.drop_index('ix_advisories_severity', table_name='advisories')
    op.drop_index('ix_advisories_hazard_type', table_name='advisories')
    op.drop_index('ix_advisories_authority', table_name='advisories')
    op.drop_index('ix_advisories_source_id', table_name='advisories')
    op.drop_table('advisories')
