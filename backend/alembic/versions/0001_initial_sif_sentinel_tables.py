"""initial_sif_sentinel_tables

Revision ID: 0001_initial_tables
Revises: 
Create Date: 2026-09-27 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = '0001_initial_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector & uuid extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # 2. Create Enums
    user_role_enum = postgresql.ENUM('hse_officer', 'site_manager', 'admin', name='user_role_enum', create_type=False)
    user_role_enum.create(op.get_bind(), checkfirst=True)

    report_type_enum = postgresql.ENUM('UA', 'UC', 'near_miss', 'incident', name='report_type_enum', create_type=False)
    report_type_enum.create(op.get_bind(), checkfirst=True)

    sif_label_enum = postgresql.ENUM('sif_potential', 'non_sif', name='sif_label_enum', create_type=False)
    sif_label_enum.create(op.get_bind(), checkfirst=True)

    report_status_enum = postgresql.ENUM('pending_review', 'reviewed', 'auto_confirmed', name='report_status_enum', create_type=False)
    report_status_enum.create(op.get_bind(), checkfirst=True)

    barrier_severity_enum = postgresql.ENUM('low', 'medium', 'high', name='barrier_severity_enum', create_type=False)
    barrier_severity_enum.create(op.get_bind(), checkfirst=True)

    pattern_trend_enum = postgresql.ENUM('rising', 'stable', 'falling', name='pattern_trend_enum', create_type=False)
    pattern_trend_enum.create(op.get_bind(), checkfirst=True)

    # 3. Create 'sites' table
    op.create_table(
        'sites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location_lat', sa.Float(), nullable=False),
        sa.Column('location_lng', sa.Float(), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('operation_type', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 4. Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('hse_officer', 'site_manager', 'admin', name='user_role_enum', create_type=False), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_site_id'), 'users', ['site_id'], unique=False)

    # 5. Create 'reports' table with pgvector column and indexes
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_type', postgresql.ENUM('UA', 'UC', 'near_miss', 'incident', name='report_type_enum', create_type=False), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('submitted_by', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('activity', sa.String(length=255), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=True),
        sa.Column('sif_label', postgresql.ENUM('sif_potential', 'non_sif', name='sif_label_enum', create_type=False), nullable=True),
        sa.Column('sif_confidence', sa.Float(), nullable=True),
        sa.Column('primary_lsr', sa.String(length=255), nullable=True),
        sa.Column('status', postgresql.ENUM('pending_review', 'reviewed', 'auto_confirmed', name='report_status_enum', create_type=False), server_default='pending_review', nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_primary_lsr'), 'reports', ['primary_lsr'], unique=False)
    op.create_index(op.f('ix_reports_site_id'), 'reports', ['site_id'], unique=False)
    op.create_index(op.f('ix_reports_submitted_at'), 'reports', ['submitted_at'], unique=False)
    op.create_index(op.f('ix_reports_sif_label'), 'reports', ['sif_label'], unique=False)
    op.create_index(op.f('ix_reports_submitted_by'), 'reports', ['submitted_by'], unique=False)
    op.create_index('ix_reports_site_submitted', 'reports', ['site_id', 'submitted_at'], unique=False)
    op.create_index('ix_reports_sif_status', 'reports', ['sif_label', 'status'], unique=False)

    # 6. Create 'report_lsr_tags' table
    op.create_table(
        'report_lsr_tags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('lsr_rule', sa.String(length=255), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_lsr_tags_report_id'), 'report_lsr_tags', ['report_id'], unique=False)

    # 7. Create 'barrier_failures' table
    op.create_table(
        'barrier_failures',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('barrier_type', sa.String(length=255), nullable=False),
        sa.Column('evidence_phrase', sa.Text(), nullable=False),
        sa.Column('severity', postgresql.ENUM('low', 'medium', 'high', name='barrier_severity_enum', create_type=False), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_barrier_failures_report_id'), 'barrier_failures', ['report_id'], unique=False)

    # 8. Create 'precursor_patterns' table
    op.create_table(
        'precursor_patterns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('activity', sa.String(length=255), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('barrier_type', sa.String(length=255), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('trend', postgresql.ENUM('rising', 'stable', 'falling', name='pattern_trend_enum', create_type=False), server_default='stable', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_precursor_patterns_activity'), 'precursor_patterns', ['activity'], unique=False)
    op.create_index(op.f('ix_precursor_patterns_location'), 'precursor_patterns', ['location'], unique=False)
    op.create_index(op.f('ix_precursor_patterns_barrier_type'), 'precursor_patterns', ['barrier_type'], unique=False)

    # 9. Create 'safety_index' table
    op.create_table(
        'safety_index',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('period', sa.Date(), nullable=False),
        sa.Column('sif_density', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('barrier_recurrence_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('sii_score', sa.Float(), server_default='0.0', nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_safety_index_site_id'), 'safety_index', ['site_id'], unique=False)
    op.create_index(op.f('ix_safety_index_period'), 'safety_index', ['period'], unique=False)
    op.create_index('ix_safety_index_site_period', 'safety_index', ['site_id', 'period'], unique=True)

    # 10. Create 'review_queue' table
    op.create_table(
        'review_queue',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('resolved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('corrected_label', sa.String(length=255), nullable=True),
        sa.Column('corrected_lsr', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_queue_report_id'), 'review_queue', ['report_id'], unique=False)
    op.create_index(op.f('ix_review_queue_assigned_to'), 'review_queue', ['assigned_to'], unique=False)
    op.create_index(op.f('ix_review_queue_resolved'), 'review_queue', ['resolved'], unique=False)

    # 11. Create 'model_feedback_log' table
    op.create_table(
        'model_feedback_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('original_label', sa.String(length=255), nullable=False),
        sa.Column('corrected_label', sa.String(length=255), nullable=False),
        sa.Column('corrected_by', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['corrected_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_model_feedback_log_report_id'), 'model_feedback_log', ['report_id'], unique=False)
    op.create_index(op.f('ix_model_feedback_log_corrected_by'), 'model_feedback_log', ['corrected_by'], unique=False)

    # 12. Create 'alerts' table
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(length=100), nullable=False),
        sa.Column('sent_to', sa.String(length=255), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_report_id'), 'alerts', ['report_id'], unique=False)
    op.create_index(op.f('ix_alerts_acknowledged'), 'alerts', ['acknowledged'], unique=False)

    # 13. Create 'audit_log' table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('actor', sa.Integer(), nullable=True),
        sa.Column('before', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('after', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['actor'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    # 14. Create 'case_library' table
    op.create_table(
        'case_library',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('incident_year', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.String(length=100), nullable=False),
        sa.Column('lsr_category', sa.String(length=150), nullable=False),
        sa.Column('failed_barriers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('root_causes', sa.Text(), nullable=False),
        sa.Column('lessons_learned', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_library_lsr_category'), 'case_library', ['lsr_category'], unique=False)


def downgrade() -> None:
    op.drop_table('case_library')
    op.drop_table('audit_log')
    op.drop_table('alerts')
    op.drop_table('model_feedback_log')
    op.drop_table('review_queue')
    op.drop_table('safety_index')
    op.drop_table('precursor_patterns')
    op.drop_table('barrier_failures')
    op.drop_table('report_lsr_tags')
    op.drop_table('reports')
    op.drop_table('users')
    op.drop_table('sites')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS pattern_trend_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS barrier_severity_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS report_status_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS sif_label_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS report_type_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS user_role_enum CASCADE;")

