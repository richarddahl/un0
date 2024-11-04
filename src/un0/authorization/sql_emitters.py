# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from pydantic.dataclasses import dataclass

from un0.database.sql_emitters import SQLEmitter
from un0.config import settings


@dataclass
class SetDefaultTenantSQL(SQLEmitter):
    def emit_sql(self) -> str:
        """ """
        return textwrap.dedent(
            f"""
            -- Change the table default for tenant_id
            ALTER TABLE {self.schema_name}.{self.table_name}
                ALTER COLUMN id SET DEFAULT current_setting('rls_var.tenant_id', true);
            """
        )


@dataclass
class CreatedModifiedFnctnSQL(SQLEmitter):
    """
    A SQL Emitter class that generates a SQL function to set the owned_by_id and
    modified_by_id fields of a table to the user_id of the user making the change.

    This sql_emitter is applied to the table (user) or tables that have
    owned_by_id, modified_by_id, fields defined in their schema that are used by fks on
    other tables.

    The tables using these fields then must have the set_owner_and_modified trigger
    function applied to them via the CreatedModifiedFieldSQLEmitter.

    Methods:
        emit_sql() -> str:
            Generates and returns the SQL function string that sets the owned_by_id
            and modified_by_id fields based on the current user_id from session
            variables. It handles both INSERT and UPDATE operations, setting the
            appropriate fields and timestamps.
    """

    def emit_sql(self) -> str:
        function_string = """
            DECLARE
                user_id TEXT := current_setting('rls_var.user_id', true);
            BEGIN
                /* 
                Function used to set the owned_by_id and modified_by_id fields
                of a table to the user_id of the user making the change. 
                */

                SELECT current_setting('rls_var.user_id', true) INTO user_id;

                IF user_id IS NULL THEN
                    RAISE EXCEPTION 'user_id is NULL';
                END IF;

                IF user_id = '' THEN
                    RAISE EXCEPTION 'user_id is an empty string';
                END IF;

                IF TG_OP = 'INSERT' THEN
                    NEW.owned_by_id = user_id;
                    NEW.modified_by_id = user_id;
                    NEW.created_at := TIMESTAMPZ();
                END IF;

                IF TG_OP = 'UPDATE' THEN
                    NEW.modified_by_id = user_id;
                END IF;

                NEW.modified_at := NOW();
                RETURN NEW;
            END;
            """

        return self.create_sql_function("set_owner_and_modified", function_string)


@dataclass
class CreatedModifiedTrggrSQL(SQLEmitter):
    """
    A SQL Emitter class that generates SQL statements for altering default values
    and creating update triggers for the fields:
        created_at
        owned_by_id
        modified_at
        modified_by_id


    Methods
    -------
    emit_sql() -> str
        Generates the complete SQL statement by combining the alter default SQL and
        the update trigger SQL.

    emit_alter_default_sql() -> str
        Generates the SQL statement to alter the default values of the specified fields.

    emit_on_update_trigger_sql() -> str
        Generates the SQL statement to create an update trigger for the specified fields.
    """

    # def emit_sql(self) -> str:
    #    return "\n".join(
    #        [self.emit_alter_default_sql(), self.emit_on_update_trigger_sql()]
    #    )

    def emit_alter_default_sql(self) -> str:
        """ """
        return textwrap.dedent(
            f"""
            -- Change the table default for created_at, modified_at, owned_by_id, and modified_by_id
            ALTER TABLE {self.schema_name}.{self.table_name}
                ALTER COLUMN created_at SET DEFAULT NOW(),
                ALTER COLUMN owned_by_id SET DEFAULT current_setting('rls_var.user_id', true),
                ALTER COLUMN modified_at SET DEFAULT NOW(),
                ALTER COLUMN modified_by_id SET DEFAULT current_setting('rls_var.user_id', true);
            """
        )

    # def emit_on_update_trigger_sql(self) -> str:
    def emit_sql(self) -> str:
        """ """
        return self.create_sql_trigger(
            "set_owner_and_modified",
            timing="BEFORE",
            operation="INSERT OR UPDATE",
        )


@dataclass
class SoftDeleteFnctnSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = """
            DECLARE
                user_id TEXT;
            BEGIN
                /* 
                Function used to validate that a record can be deleted.
                IF the record previously had is_deleted set to false the function
                returns the record, allowing the delete to proceed.
                otherwise Sets the is_deleted field to true and the deleted_by_id field to the user_id
                */

                SELECT current_setting('rls_var.user_id', true) into user_id;

                IF user_id IS NULL THEN
                    RAISE EXCEPTION 'user_id is NULL';
                END IF;

                IF OLD.is_deleted IS TRUE THEN
                    OLD.deleted_by_id = user_id;
                    OLD.deleted_at = NOW();
                    RETURN OLD;
                ELSE
                    EXECUTE format('
                        UPDATE %I 
                        SET is_deleted = true, deleted_by_id = %L , deleted_at = NOW()
                        WHERE id = %L', TG_TABLE_NAME, user_id, OLD.id
                    );
                    RETURN NULL;
                END IF;
            END;
            """

        return self.create_sql_function("validate_delete", function_string)


@dataclass
class SoftDeleteTrggrSQL(SQLEmitter):
    def emit_sql(self) -> str:
        """ """
        return self.create_sql_trigger(
            "validate_delete",
            timing="BEFORE",
            operation="DELETE",
        )


@dataclass
class InsertTablePermissionFnctnTrggrSQL(SQLEmitter):
    def emit_create_table_record_sql(self) -> str:
        function_string = """
            BEGIN
                /*
                Function to create a new TablePermission record when a new TableType is inserted.
                Records are created for each table_type with the following combinations of permissions:
                    [SELECT]
                    [SELECT, INSERT]
                    [SELECT, UPDATE]
                    [SELECT, INSERT, UPDATE]
                    [SELECT, INSERT, UPDATE, DELETE]
                Deleted automatically by the DB via the FK Constraints ondelete when a table_type is deleted.
                */
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'UPDATE']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']::un0.permission_name[]);
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "create_tablepermissions",
            function_string,
            timing="AFTER",
            operation="INSERT",
            include_trigger=True,
            db_function=True,
        )

    def emit_get_permissions_function_sql(self) -> str:
        function_string = f"""
            SET ROLE {settings.DB_NAME}_admin;
            DECLARE
                session_user_id := current_setting('session_user_id', true);
            BEGIN
                SELECT g.*
                from group g
                JOIN un0.user_group_role ugr ON ugr.group_id = g.id
                JOIN un0.user u ON u.id = ugr.user_email
                JOIN un0.tablepermission tp ON ugr.role_id = tp.id
                WHERE u.id = session_user_id AND tp.is_active = TRUE
                AND tp.table_name = query_table_name;
            END;
            """

        return self.create_sql_function("get_permissible_groups", function_string)


class ValidateGroupInsertSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                group_count INT4;
                tenanttype un0.tenanttype;
            BEGIN
                SELECT tenant_type INTO tenanttype
                FROM un0.tenant
                WHERE id = NEW.tenant_id;

                SELECT COUNT(*) INTO group_count
                FROM un0.group
                WHERE tenant_id = NEW.tenant_id;

                IF NOT {settings.ENFORCE_MAX_GROUPS} THEN
                    RETURN NEW;
                END IF;

                IF tenanttype = 'INDIVIDUAL' AND
                    {settings.MAX_INDIVIDUAL_GROUPS} > 0 AND
                    group_count >= {settings.MAX_INDIVIDUAL_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                IF
                    tenanttype = 'BUSINESS' AND
                    {settings.MAX_BUSINESS_GROUPS} > 0 AND
                    group_count >= {settings.MAX_BUSINESS_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                IF
                    tenanttype = 'CORPORATE' AND
                    {settings.MAX_CORPORATE_GROUPS} > 0 AND
                    group_count >= {settings.MAX_CORPORATE_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                IF
                    tenanttype = 'ENTERPRISE' AND
                    {settings.MAX_ENTERPRISE_GROUPS} > 0 AND
                    group_count >= {settings.MAX_ENTERPRISE_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "validate_group_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )
