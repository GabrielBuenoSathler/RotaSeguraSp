"""Add indexes for latest-route lookup and the risk geography expression."""

from alembic import op

revision = "8c4b92e1a607"
down_revision = "029c1f4db84a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX ix_calculated_routes_request_latest
        ON calculated_routes (route_request_id, created_at DESC, id DESC)
    """)
    # The occurrence table is imported externally, not created by Alembic.
    # Keep migrations usable before that dataset has been loaded.
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('ocorrencias_stg') IS NOT NULL THEN
                CREATE INDEX ix_ocorrencias_stg_risk_geography
                ON ocorrencias_stg
                USING gist ((COALESCE(geog, geom::geography)));
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ocorrencias_stg_risk_geography")
    op.drop_index(
        "ix_calculated_routes_request_latest", table_name="calculated_routes"
    )
