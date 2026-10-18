"""speaking recordings: the Realtime-era speaking tables (never used) give way to recorded answers

Revision ID: ed0866d15c7e
Revises: fea556145ed9
Create Date: 2026-10-18 17:57:52.534606
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'ed0866d15c7e'
down_revision: str | None = 'fea556145ed9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.drop_table('speaking_evaluations')
    op.drop_table('speaking_sessions')
    op.drop_table('speaking_prompt_tags')
    op.drop_table('speaking_prompts')
    op.add_column('parts', sa.Column('cue_card', JSONB, nullable=True))
    op.create_table('speaking_answers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('attempt_section_id', sa.Integer(), nullable=False),
    sa.Column('part_number', sa.SmallInteger(), nullable=False),
    sa.Column('line_no', sa.SmallInteger(), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('audio', sa.LargeBinary(), nullable=False),
    sa.Column('mime', sa.String(length=60), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('transcript', JSONB, nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['attempt_section_id'], ['attempt_sections.id'], name=op.f('fk_speaking_answers_attempt_section_id_attempt_sections'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_speaking_answers')),
    sa.UniqueConstraint('attempt_section_id', 'part_number', 'line_no', name=op.f('uq_speaking_answers_attempt_section_id'))
    )
    op.create_table('speaking_evaluations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('attempt_section_id', sa.Integer(), nullable=False),
    sa.Column('run_no', sa.SmallInteger(), nullable=False),
    sa.Column('model', sa.String(length=60), nullable=False),
    sa.Column('criteria', JSONB, nullable=False),
    sa.Column('task_band', sa.Numeric(precision=3, scale=2, asdecimal=False), nullable=False),
    sa.Column('errors', JSONB, nullable=False),
    sa.Column('weakness_tags', JSONB, nullable=False),
    sa.Column('raw', JSONB, nullable=False),
    sa.Column('inconsistent', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['attempt_section_id'], ['attempt_sections.id'], name=op.f('fk_speaking_evaluations_attempt_section_id_attempt_sections'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_speaking_evaluations'))
    )
    op.create_index(op.f('ix_speaking_evaluations_attempt_section_id'), 'speaking_evaluations', ['attempt_section_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_speaking_evaluations_attempt_section_id'), table_name='speaking_evaluations')
    op.drop_table('speaking_evaluations')
    op.drop_table('speaking_answers')
    op.drop_column('parts', 'cue_card')
    op.create_table('speaking_prompts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('part_number', sa.SmallInteger(), nullable=False),
    sa.Column('topic', sa.String(length=120), nullable=False),
    sa.Column('content', JSONB, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_speaking_prompts')),
    sa.UniqueConstraint('slug', name=op.f('uq_speaking_prompts_slug'))
    )
    op.create_table('speaking_prompt_tags',
    sa.Column('speaking_prompt_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['speaking_prompt_id'], ['speaking_prompts.id'], name=op.f('fk_speaking_prompt_tags_speaking_prompt_id_speaking_prompts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], name=op.f('fk_speaking_prompt_tags_tag_id_tags'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('speaking_prompt_id', 'tag_id', name=op.f('pk_speaking_prompt_tags'))
    )
    op.create_table('speaking_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('attempt_section_id', sa.Integer(), nullable=False),
    sa.Column('prompt_ids', JSONB, nullable=False),
    sa.Column('model', sa.String(length=60), nullable=False),
    sa.Column('transcript', JSONB, nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['attempt_section_id'], ['attempt_sections.id'], name=op.f('fk_speaking_sessions_attempt_section_id_attempt_sections'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_speaking_sessions'))
    )
    op.create_table('speaking_evaluations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('model', sa.String(length=60), nullable=False),
    sa.Column('criteria', JSONB, nullable=False),
    sa.Column('band', sa.Numeric(precision=2, scale=1, asdecimal=False), nullable=False),
    sa.Column('pronunciation_is_estimate', sa.Boolean(), nullable=False),
    sa.Column('errors', JSONB, nullable=False),
    sa.Column('raw', JSONB, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['speaking_sessions.id'], name=op.f('fk_speaking_evaluations_session_id_speaking_sessions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_speaking_evaluations'))
    )
    op.create_index(op.f('ix_speaking_evaluations_session_id'), 'speaking_evaluations', ['session_id'], unique=False)
