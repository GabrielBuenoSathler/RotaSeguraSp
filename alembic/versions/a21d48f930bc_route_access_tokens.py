"""Require a secret token to access a stored route request."""

import sqlalchemy as sa
from alembic import op

revision = "a21d48f930bc"
down_revision = "8c4b92e1a607"
branch_labels = None
depends_on = None


def upgrade():
    # Legacy routes have no token and are intentionally inaccessible through the API.
    op.add_column("route_requests", sa.Column("access_token_hash", sa.String(64)))


def downgrade():
    op.drop_column("route_requests", "access_token_hash")
