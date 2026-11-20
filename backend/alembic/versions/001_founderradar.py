"""Evidence, sources, scans and human review."""

from pathlib import Path
from alembic import op
from sqlalchemy import inspect

revision = "001_founderradar"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if "ventures" in inspect(connection).get_table_names():
        return
    sql = (
        Path(__file__).resolve().parents[2] / "migrations" / "001_initial.sql"
    ).read_text()
    for stmt in sql.split(";"):
        if stmt.strip():
            connection.exec_driver_sql(stmt)
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY)"
    )
    connection.exec_driver_sql("INSERT OR IGNORE INTO schema_version VALUES(1)")


def downgrade():
    raise RuntimeError(
        "Restoring a backed-up database is required for a destructive downgrade."
    )
