"""Initial schema with all models including auth.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Settings tables
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(20), nullable=False, server_default='string'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), server_default='false'),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category', 'key', name='uq_settings_category_key'),
    )
    op.create_index('idx_settings_category', 'settings', ['category'])

    op.create_table(
        'settings_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('setting_id', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('changed_by', sa.String(100), nullable=True),
        sa.Column('change_type', sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(['setting_id'], ['settings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Agent predictions
    op.create_table(
        'agent_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('outlook', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('timeframe', sa.String(20), nullable=True),
        sa.Column('specific_predictions', sa.JSON(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('key_factors', sa.JSON(), nullable=True),
        sa.Column('uncertainties', sa.JSON(), nullable=True),
        sa.Column('data_sources', sa.JSON(), nullable=True),
        sa.Column('supporting_evidence', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_agent_predictions_agent_id', 'agent_predictions', ['agent_id'])
    op.create_index('idx_agent_predictions_timestamp', 'agent_predictions', ['timestamp'])

    # Market data
    op.create_table(
        'market_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=True),
        sa.Column('indicator', sa.String(100), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('data_type', 'symbol', 'indicator', 'source', name='uq_market_data_unique'),
    )
    op.create_index('idx_market_data_type_symbol', 'market_data', ['data_type', 'symbol'])
    op.create_index('idx_market_data_expires', 'market_data', ['expires_at'])

    # Aggregated insights
    op.create_table(
        'aggregated_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('overall_outlook', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('agent_outputs', sa.JSON(), nullable=True),
        sa.Column('conflicts', sa.JSON(), nullable=True),
        sa.Column('resolution_reasoning', sa.Text(), nullable=True),
        sa.Column('final_recommendations', sa.JSON(), nullable=True),
        sa.Column('risk_assessment', sa.JSON(), nullable=True),
        sa.Column('vetoed', sa.Boolean(), server_default='false'),
        sa.Column('veto_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_aggregated_insights_timestamp', 'aggregated_insights', ['timestamp'])

    # Performance metrics
    op.create_table(
        'performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(50), nullable=False),
        sa.Column('prediction_id', sa.Integer(), nullable=True),
        sa.Column('predicted_outlook', sa.String(20), nullable=True),
        sa.Column('actual_outcome', sa.String(20), nullable=True),
        sa.Column('prediction_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('outcome_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accuracy_score', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['prediction_id'], ['agent_predictions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_performance_metrics_agent_id', 'performance_metrics', ['agent_id'])

    # Agent weights
    op.create_table(
        'agent_weights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(50), nullable=False),
        sa.Column('weight', sa.Float(), server_default='1.0'),
        sa.Column('accuracy_30d', sa.Float(), nullable=True),
        sa.Column('accuracy_90d', sa.Float(), nullable=True),
        sa.Column('accuracy_all_time', sa.Float(), nullable=True),
        sa.Column('total_predictions', sa.Integer(), server_default='0'),
        sa.Column('correct_predictions', sa.Integer(), server_default='0'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id'),
    )

    # Auth tables
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('permissions', sa.JSON(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource', sa.String(100), nullable=False),
        sa.Column('resource_id', sa.String(100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])

    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('idx_refresh_tokens_token', 'refresh_tokens', ['token'])

    # Seed default roles
    op.execute("""
        INSERT INTO roles (name, description, permissions) VALUES
        ('admin', 'Full system access', '["*"]'),
        ('user', 'Standard user access', '["read:agents", "read:insights", "read:performance", "read:settings", "write:ui_preferences"]'),
        ('readonly', 'Read-only access', '["read:agents", "read:insights", "read:performance"]')
    """)


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('audit_logs')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('agent_weights')
    op.drop_table('performance_metrics')
    op.drop_table('aggregated_insights')
    op.drop_table('market_data')
    op.drop_table('agent_predictions')
    op.drop_table('settings_history')
    op.drop_table('settings')
