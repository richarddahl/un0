# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import (
    ENUM,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from un0.msg.enums import (  # type: ignore
    MessageImportance,
)
from un0.db import Base, BaseMixin, RBACMixin, str_26, str_255  # type: ignore
from un0.rltd.models import RelatedObject, TableType


class Message(Base, BaseMixin, RBACMixin):
    __tablename__ = "message"
    __table_args__ = {
        "schema": "un0",
        "comment": "Messages are used to communicate between users",
    }

    # Columns
    id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=sa.func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_RELATED_OBJECT"},
    )
    sender_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WAS_SENT_BY"},
    )
    previous_message_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.message.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "HAS_PREVIOUS_MESSAGE"},
    )
    flag: Mapped[MessageImportance] = mapped_column(
        ENUM(MessageImportance, name="importance_enum", create_type=True, schema="un0"),
        doc="Importance of the message",
    )
    subject: Mapped[str_255] = mapped_column(doc="Subject of the message")
    body: Mapped[str_255] = mapped_column(doc="Body of the message")
    sent_at: Mapped[datetime.datetime] = mapped_column(
        server_default=sa.func.current_timestamp(),
        doc="Time the message was sent",
    )

    # Relationships


class MessageAddressedTo(Base):
    __tablename__ = "message_addressed_to"
    __table_args__ = {
        "schema": "un0",
        "comment": "Messages addressed to users",
        "info": {"edge": "WAS_SENT", "rls_policy": "none"},
    }

    # Columns
    message_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.message.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "WAS_ADDRESSED"},
    )
    addressed_to_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "WAS_ADDRESSED_TO"},
    )
    read: Mapped[bool] = mapped_column(
        server_default=sa.text("false"),
        nullable=False,
    )
    read_at: Mapped[datetime.datetime] = mapped_column()

    # Relationships


class MessageCopiedTo(Base):
    __tablename__ = "message_copied_to"
    __table_args__ = {
        "schema": "un0",
        "comment": "Messages copied to users",
        "info": {"edge": "WAS_CCD", "rls_policy": "none"},
    }

    # Columns
    message_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.message.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "WAS_SENT_CC"},
    )
    copied_to_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "WAS_CCD_ON"},
    )
    read: Mapped[bool] = mapped_column(
        server_default=sa.text("false"),
        nullable=False,
    )
    read_at: Mapped[datetime.datetime] = mapped_column()

    # Relationships


class MessageAttachment(Base):
    __tablename__ = "message_attachment"
    __table_args__ = {
        "schema": "un0",
        "comment": "Attachments to messages",
        "info": {"edge": "HAS_ATTACHMENTS", "rls_policy": "none"},
    }

    # Columns
    message_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.message.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "IS_ATTACHED_TO"},
    )
    attachment_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.attachment.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "HAS_ATTACHMENT"},
    )

    # Relationships


class Attachment(Base, BaseMixin):
    __tablename__ = "attachment"
    __table_args__ = {
        "schema": "un0",
        "comment": "Files attached to db objects",
    }

    # Columns
    id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=sa.func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_RELATED_OBJECT"},
    )
    name: Mapped[str_255] = mapped_column(unique=True, doc="Name of the file")
    file: Mapped[str_255] = mapped_column(doc="Path to the file")

    # Relationships
