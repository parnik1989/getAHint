from sqlalchemy import inspect, text

from app.db.base import Base


def ensure_database_schema(engine):
    Base.metadata.create_all(bind=engine)

    dialect_name = engine.dialect.name
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("events")}

        if dialect_name == "postgresql":
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            if "event_embedding" not in columns:
                connection.execute(text("ALTER TABLE events ADD COLUMN event_embedding vector(384)"))
        elif "embedding_json" not in columns:
            connection.execute(text("ALTER TABLE events ADD COLUMN embedding_json TEXT"))
