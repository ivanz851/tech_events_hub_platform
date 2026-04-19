from __future__ import annotations
import uuid
from typing import Any

from sqlalchemy import ARRAY, BigInteger, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = ("Base", "User", "UserIdentity", "UserSettings", "Link", "LinkUserMapping", "EventData")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(Text)
    identities: Mapped[list[UserIdentity]] = relationship(
        "UserIdentity",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    settings: Mapped[UserSettings | None] = relationship(
        "UserSettings",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    mappings: Mapped[list[LinkUserMapping]] = relationship(
        "LinkUserMapping",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="user_identities_provider_unique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="identities")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    notify_email: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    notify_telegram: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    user: Mapped[User] = relationship("User", back_populates="settings")


class Link(Base):
    __tablename__ = "link"
    __table_args__ = (UniqueConstraint("url", name="link_url_unique"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    mappings: Mapped[list[LinkUserMapping]] = relationship(
        "LinkUserMapping",
        back_populates="link",
        cascade="all, delete-orphan",
    )
    events: Mapped[list[EventData]] = relationship(
        "EventData",
        back_populates="link",
        cascade="all, delete-orphan",
    )


class LinkUserMapping(Base):
    __tablename__ = "link_user_mapping"

    link_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("link.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="'{}'",
    )

    link: Mapped[Link] = relationship("Link", back_populates="mappings")
    user: Mapped[User] = relationship("User", back_populates="mappings")


class EventData(Base):
    __tablename__ = "event_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    link_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("link.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    price: Mapped[str | None] = mapped_column(Text)
    registration_url: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    organizer: Mapped[str | None] = mapped_column(Text)

    link: Mapped[Link] = relationship("Link", back_populates="events")
