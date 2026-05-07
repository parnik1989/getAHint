from sqlalchemy import inspect, text

from app.db.base import Base


def _get_table_columns(connection, table_name: str) -> set[str]:
    if connection.dialect.name == "postgresql":
        rows = connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        )
        return {row.column_name for row in rows}

    return {column["name"] for column in inspect(connection).get_columns(table_name)}


def ensure_database_schema(engine):
    Base.metadata.create_all(bind=engine)

    dialect_name = engine.dialect.name
    with engine.begin() as connection:
        columns = _get_table_columns(connection, "events")

        if "embedding_json" not in columns:
            connection.execute(text("ALTER TABLE events ADD COLUMN embedding_json TEXT"))

        if "category" not in columns:
            connection.execute(text("ALTER TABLE events ADD COLUMN category VARCHAR(50)"))

        if dialect_name == "postgresql":
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            if "event_embedding" not in columns:
                connection.execute(text("ALTER TABLE events ADD COLUMN event_embedding vector(384)"))
