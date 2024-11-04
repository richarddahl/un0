# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.database.fields import UQ
from un0.relatedobjects.models import TableType, RelatedObject
from un0.relatedobjects.sql_emitters import RelatedObjectIDFnctnSQL


class TestTableTypeModel:
    schema = "un0"

    def test_table_type_model_structure(self):
        assert TableType.__name__ == "TableType"
        assert TableType.__module__ == "un0.relatedobjects.models"
        assert TableType.schema_name == "un0"
        assert TableType.table_name == "table_type"
        assert TableType.table_name_plural == "table_types"
        assert TableType.verbose_name == "Table Type"
        assert TableType.verbose_name_plural == "Table Types"
        assert list(TableType.field_definitions.keys()) == ["id", "db_schema", "name"]
        assert TableType.constraints == [
            UQ(columns=["db_schema", "name"], name="uq_tabletype_db_schema_name")
        ]
        assert TableType.indices == []
        assert TableType.sql_emitters == []


class TestRelatedObjectModel:
    schema = "un0"

    def test_table_type_model_structure(self):
        assert RelatedObject.__name__ == "RelatedObject"
        assert RelatedObject.__module__ == "un0.relatedobjects.models"
        assert RelatedObject.schema_name == "un0"
        assert RelatedObject.table_name == "related_object"
        assert RelatedObject.table_name_plural == "related_objects"
        assert RelatedObject.verbose_name == "Related Object"
        assert RelatedObject.verbose_name_plural == "Related Objects"
        assert list(RelatedObject.field_definitions.keys()) == ["id", "table_type_id"]
        assert RelatedObject.constraints == []
        assert RelatedObject.indices == []
        assert RelatedObject.sql_emitters.__len__() == 1
        assert RelatedObjectIDFnctnSQL in RelatedObject.sql_emitters
