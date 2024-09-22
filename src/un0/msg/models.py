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
    """
    addressed_to: Mapped[list["User"]] = relationship(
        back_populates="addressed_to",
        secondary="message_addressed_to",
        doc="Users the message is addressed to",
    )
    copied_to: Mapped[list["User"]] = relationship(
        back_populates="copied_to",
        secondary="message_copied_to",
        doc="Users the message is copied to",
    )
    message_attachment: Mapped[list["Attachment"]] = relationship(
        back_populates="message",
        secondary="message_attachment",
        doc="Attachments to the message",
    )
    previous_message: Mapped["Message"] = relationship(
        back_populates="next_message",
        foreign_keys=[previous_message_id],
        doc="Previous message in the conversation",
    )
    next_message: Mapped["Message"] = relationship(
        back_populates="previous_message",
        uselist=False,
        remote_side="Message.id",
        doc="Next message in the conversation",
    )
    message_objects: Mapped[list[RelatedObject]] = relationship(
        back_populates="message_objects",
        secondary="message_object.message_id",
        doc="Objects associated with the message",
    )
    """


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
    """
    message: Mapped["Message"] = relationship(
        back_populates="addressed_to",
        foreign_keys=[message_id],
        doc="Message addressed to the user",
    )
    addressed_to: Mapped["User"] = relationship(
        back_populates="addressed_to",
        foreign_keys=[addressed_to_id],
        doc="User the message is addressed to",
    )
    """


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
    """
    message: Mapped["Message"] = relationship(
        back_populates="copied_to",
        foreign_keys=[message_id],
        doc="Message copied to the user",
    )
    copied_to: Mapped["User"] = relationship(
        back_populates="copied_to",
        foreign_keys=[copied_to_id],
        doc="User the message is copied to",
    )
    """


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
    """
    message: Mapped["Message"] = relationship(
        back_populates="message_attachment",
        foreign_keys=[message_id],
        doc="Message the attachment is associated with",
    )
    attachment: Mapped["Attachment"] = relationship(
        back_populates="message_attachment",
        foreign_keys=[attachment_id],
        doc="Attachment associated with the message",
    )
    """


message_object = sa.Table(
    "message_object",
    Base.metadata,
    sa.Column(
        "message_id",
        sa.String(26),
        sa.ForeignKey("un0.message.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "HAS_OBJECT"},
    ),
    sa.Column(
        "object_id",
        sa.String(26),
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        nullable=False,
        info={"edge": "HAS_MESSAGE"},
    ),
    schema="un0",
    comment="Objects associated with messages",
    info={"edge": "HAS_OBJECTS", "rls_policy": "none"},
)


# class MessageObject(Base):
#    __tablename__ = "message_object"
#    __table_args__ = {
#        "schema": "un0",
#        "comment": "Objects associated with messages",
#        "info": {"edge": "HAS_OBJECTS", "rls_policy": "none"},
#    }
#
#    # Columns
#    message_id: Mapped[str_26] = mapped_column(
#        sa.ForeignKey("un0.message.id", ondelete="CASCADE"),
#        index=True,
#        primary_key=True,
#        nullable=False,
#        info={"edge": "HAS_OBJECT"},
#    )
#    object_id: Mapped[str_26] = mapped_column(
#        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
#        index=True,
#        primary_key=True,
#        nullable=False,
#        info={"edge": "HAS_MESSAGE"},
#    )
#
#    # Relationships
##    message: Mapped["Message"] = relationship(
#        back_populates="message",
#        foreign_keys=[message_id],
#        doc="Message the object is associated with",
#    )
#    object: Mapped["RelatedObject"] = relationship(
#        back_populates="object",
#        foreign_keys=[object_id],
#        doc="Object associated with the message",
#    )


class Attachment(Base, BaseMixin):
    __tablename__ = "attachment"
    __table_args__ = {
        "schema": "un0",
        "comment": "Files attached to db objects",
    }

    # Columns
    name: Mapped[str_255] = mapped_column(unique=True, doc="Name of the file")
    file: Mapped[str_255] = mapped_column(doc="Path to the file")

    # Relationships
    """
    messages: Mapped[list["Message"]] = relationship(
        back_populates="attachment",
        secondary="message_attachment",
    )
    """
