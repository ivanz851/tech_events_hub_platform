from __future__ import annotations

from sqlalchemy import ARRAY, BigInteger, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = ("Base", "TgChat", "Link", "LinkUserMapping", "EventData")


class Base(DeclarativeBase):
    pass


class TgChat(Base):
    __tablename__ = "tg_chat"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mappings: Mapped[list[LinkUserMapping]] = relationship(
        "LinkUserMapping",
        back_populates="chat",
        cascade="all, delete-orphan",
    )


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
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tg_chat.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    filters: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")

    link: Mapped[Link] = relationship("Link", back_populates="mappings")
    chat: Mapped[TgChat] = relationship("TgChat", back_populates="mappings")


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
