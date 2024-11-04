# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Optional

from sqlalchemy.dialects.postgresql import VARCHAR

from un0.database.models import Model
from un0.database.mixins import FieldMixin
from un0.database.fields import FieldDefinition, FK
from un0.relatedobjects.sql_emitters import SetRelatedObjectIDSQL


class RelatedObjectIdMixin(FieldMixin):
    """ """

    sql_emitters = [SetRelatedObjectIDSQL]

    field_definitions = {
        "id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key=FK(
                target="un0.related_object.id",
                ondelete="CASCADE",
                to_edge="HAS_ID",
                from_edge="IS_ID_OF",
            ),
            primary_key=True,
            index=True,
            unique=True,
            nullable=False,
            doc="Primary Key",
        ),
    }

    id: Optional[str] = None
    related_object: Optional[Model] = None
