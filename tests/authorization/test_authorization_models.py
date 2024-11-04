# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.database.fields import UQ
from un0.database.fields import (
    FK,
    UQ,
    CK,
    IX,
    FieldDefinition,
)
from un0.database.enums import SQLOperation
from un0.database.sql_emitters import EnableDefaultAuditSQL
from un0.relatedobjects.sql_emitters import SetRelatedObjectIDSQL
from un0.authorization.models import (
    Tenant,
    User,
    TablePermission,
    Role,
    RoleTablePermission,
    Group,
    UserGroupRole,
)
from un0.authorization.sql_emitters import CreatedModifiedFnctnSQL, SetDefaultTenantSQL


class TestUserModel:
    schema = "un0"

    def test_user_model_structure(self):
        assert User.__name__ == "User"
        assert User.__module__ == "un0.authorization.models"
        assert User.schema_name == "un0"
        assert User.table_name == "user"
        assert User.table_name_plural == "users"
        assert User.verbose_name == "User"
        assert User.verbose_name_plural == "Users"
        assert list(User.field_definitions.keys()) == [
            "email",
            "handle",
            "full_name",
            "default_group_id",
            "is_superuser",
            "is_tenant_admin",
            "tenant_id",
            "id",
            "is_active",
            "created_at",
            "owned_by_id",
            "modified_at",
            "modified_by_id",
            "is_deleted",
            "deleted_at",
            "deleted_by_id",
        ]
        assert User.constraints == [
            CK(
                expression="\n(is_superuser = 'false' AND default_group_id IS NOT NULL) OR\n(is_superuser = 'true' AND default_group_id IS NULL) AND\n(is_superuser = 'false' AND is_tenant_admin = 'false') OR\n(is_superuser = 'true' AND is_tenant_admin = 'false') OR\n(is_superuser = 'false' AND is_tenant_admin = 'true')\n",
                name="ck_user_is_superuser",
            )
        ]
        assert User.sql_emitters == [EnableDefaultAuditSQL, SetRelatedObjectIDSQL]


"""
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

"""
