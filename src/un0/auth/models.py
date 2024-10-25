# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.db.models import Un0Obj, Un0ModelDef, Un0Model, Un0RouterDef, Un0Router
from un0.auth.tables import (
    User,
    Tenant,
    Role,
    Group,
)


class TenantModel(Un0Model):
    def process_app_logic(self) -> bool:
        super().process_app_logic()
        return True


class TenantObj(
    Un0Obj,
    table_name="un0.tenant",
    table=Tenant,
    module_name="auth",
    obj_name="Tenant",
    path_objs="tenants",
    model_base=TenantModel,
):
    un0_model_defs: dict[str, TenantModel] = {
        "ListTenant": Un0ModelDef(
            table=Tenant,
            field_includes=[
                "id",
                "name",
                "tenant_type",
            ],
        ),
    }


class UserModel(Un0Model):
    def process_app_logic(self) -> bool:
        super().process_app_logic()
        return True


class UserObj(
    Un0Obj,
    table_name="un0.user",
    table=User,
    module_name="auth",
    obj_name="User",
    path_objs="users",
    model_base=UserModel,
):
    un0_model_defs: dict[str, UserModel] = {
        "ListUser": Un0ModelDef(
            table=User,
            field_includes=[
                "id",
                "handle",
                "email",
                "full_name",
            ],
        ),
    }


class RoleModel(Un0Model):
    def process_app_logic(self) -> bool:
        super().process_app_logic()
        return True


class RoleObj(
    Un0Obj,
    table_name="un0.role",
    table=Role,
    module_name="auth",
    obj_name="Role",
    path_objs="roles",
    model_base=RoleModel,
):
    un0_model_defs: dict[str, UserModel] = {
        "ListRole": Un0ModelDef(
            table=Role,
            field_includes=[
                "id",
                "tenant_id",
                "name",
            ],
        ),
    }


class GroupModel(Un0Model):
    def process_app_logic(self) -> bool:
        super().process_app_logic()
        return True


class GroupObj(
    Un0Obj,
    table_name="un0.group",
    table=Group,
    module_name="auth",
    obj_name="Group",
    path_objs="groups",
    model_base=GroupModel,
):
    un0_model_defs: dict[str, UserModel] = {
        "ListGroup": Un0ModelDef(
            table=Group,
            field_includes=[
                "id",
                "tenant_id",
                "name",
            ],
        ),
    }
