from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint, func

from app.db.base import Base


class EventRecord(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint(
            "event_name",
            "event_date",
            "event_address",
            name="uq_events_name_date_address",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(255), nullable=False)
    event_description = Column(Text, nullable=False)
    event_date = Column(String(50), nullable=False, index=True)
    event_address = Column(String(500), nullable=False)
    category = Column(String(50), nullable=True, index=True)
    source_name = Column(String(255), nullable=True)
    source_type = Column(String(50), nullable=True)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EventInteraction(Base):
    __tablename__ = "event_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False, index=True)
    query = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
