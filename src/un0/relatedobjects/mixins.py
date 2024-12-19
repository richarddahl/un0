# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Optional

from sqlalchemy.dialects.postgresql import VARCHAR
from sqlalchemy import FetchedValue

from un0.database.models import Model
from un0.database.mixins import ModelMixin
from un0.database.fields import FieldDefinition, FKDefinition
from un0.relatedobjects.sql_emitters import InsertRelatedObject


class RelatedObjectIdMixin(ModelMixin):
    """ """

    sql_emitters = [InsertRelatedObject]

    field_definitions = {
        "id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.related_object.id",
                ondelete="CASCADE",
                edge_label="HAS_ID",
                reverse_edge_labels=["IS_ID_OF"],
            ),
            primary_key=True,
            index=True,
            unique=True,
            nullable=False,
            doc="Primary Key",
            server_default=FetchedValue(),
        ),
    }

    id: Optional[str] = None
    related_object: Optional[Model] = None
