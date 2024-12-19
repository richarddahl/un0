# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from pydantic.dataclasses import dataclass

from un0.database.sql_emitters import SQLEmitter
from un0.config import settings


@dataclass
class UserRecordFieldAuditSQL(SQLEmitter):
    """ """

    def emit_sql(self) -> str:
        function_string = """
            DECLARE
                user_id TEXT := current_setting('rls_var.user_id', true);
                estimate INT4;
            BEGIN
                SELECT current_setting('rls_var.user_id', true) INTO user_id;

                IF user_id IS NULL THEN
                    /*
                    This should only happen when the very first user is created
                    and therefore a user_id cannot be set in the session variables
                    */
                    SELECT reltuples AS estimate FROM PG_CLASS WHERE relname = TG_TABLE_NAME INTO estimate;
                    IF TG_TABLE_NAME = 'user' AND estimate < 1 THEN
                    /*
                         NEW.modified_at := NOW();

                        IF TG_OP = 'INSERT' THEN
                            NEW.created_at := NOW();
                        END IF;

                        IF TG_OP = 'DELETE' THEN
                            NEW.deleted_at = NOW();
                        END IF;
                        */
                    ELSE
                        RAISE EXCEPTION 'user_id is NULL';
                    END IF;
                END IF;

                NEW.modified_at := NOW();
                NEW.modified_by_id = user_id;

                IF TG_OP = 'INSERT' THEN
                    NEW.created_at := NOW();
                    NEW.owned_by_id = user_id;
                END IF;

                IF TG_OP = 'DELETE' THEN
                    NEW.deleted_at = NOW();
                    NEW.deleted_by_id = user_id;
                END IF;
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "set_owner_and_modified",
            function_string,
            timing="BEFORE",
            operation="INSERT OR UPDATE OR DELETE",
            include_trigger=True,
            db_function=False,
        )


# UNVERIFIED


class RecordFieldAuditSQL(SQLEmitter):
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

                NEW.modified_at := NOW();
                NEW.modified_by_id = user_id;

                IF TG_OP = 'INSERT' THEN
                    NEW.created_at := NOW();
                    NEW.owned_by_id = user_id;
                END IF;

                IF TG_OP = 'DELETE' THEN
                    NEW.deleted_at = NOW();
                    NEW.deleted_by_id = user_id;
                END IF;

                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "record_audit",
            function_string,
            timing="BEFORE",
            operation="INSERT OR UPDATE OR DELETE",
            include_trigger=True,
        )


@dataclass
class InsertTableOperation(SQLEmitter):
    def emit_sql(self) -> str:
        return f"{self.emit_create_table_record_sql()}\n{self.emit_get_permissions_function_sql()}"

    def emit_create_table_record_sql(self) -> str:
        function_string = """
            BEGIN
                /*
                Function to create a new TableOperation record when a new TableType is inserted.
                Records are created for each table_type with the following combinations of permissions:
                    [SELECT]
                    [SELECT, INSERT]
                    [SELECT, UPDATE]
                    [SELECT, INSERT, UPDATE]
                    [SELECT, INSERT, UPDATE, DELETE]
                Deleted automatically by the DB via the FKDefinition Constraints ondelete when a table_type is deleted.
                */
                INSERT INTO un0.table_operation(table_type_id, operations)
                    VALUES (NEW.id, ARRAY['SELECT']::un0.sqloperation[]);
                INSERT INTO un0.table_operation(table_type_id, operations)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT']::un0.sqloperation[]);
                INSERT INTO un0.table_operation(table_type_id, operations)
                    VALUES (NEW.id, ARRAY['SELECT', 'UPDATE']::un0.sqloperation[]);
                INSERT INTO un0.table_operation(table_type_id, operations)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE']::un0.sqloperation[]);
                INSERT INTO un0.table_operation(table_type_id, operations)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']::un0.sqloperation[]);
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "create_table_operations",
            function_string,
            timing="AFTER",
            operation="INSERT",
            include_trigger=True,
            db_function=True,
        )

    def emit_get_permissions_function_sql(self) -> str:
        function_string = """
            DECLARE
                user_id TEXT := current_setting('rls_var.user_id', true)::TEXT;
                permissible_groups VARCHAR(26)[];
            BEGIN
                SELECT id
                FROM un0.group g
                JOIN un0.user_group_role ugr ON ugr.group_id = g.id AND ugr.user_id = user_id
                JOIN un0.role on ugr.role_id = role.id
                JOIN un0.role_table_operation rto ON rto.role_id = role.id
                JOIN un0.table_operation tp ON tp.id = rto.table_operation_id
                JOIN un0.table_type tt ON tt.id = tp.table_type_id
                WHERE tt.name = table_type
                INTO permissible_groups;
                RETURN permissible_groups;
            END;
            """

        return self.create_sql_function(
            "get_permissible_groups",
            function_string,
            return_type="VARCHAR[]",
            function_args="table_type TEXT",
        )


class ValidateGroupInsert(SQLEmitter):
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


# class InsertGroupConstraint(SQLEmitter):
#    def emit_sql(self) -> str:
#        return """ALTER TABLE un0.group ADD CONSTRAINT ck_can_insert_group
#            CHECK (un0.validate_group_insert(tenant_id) = true);
#            """


class InsertGroupForTenant(SQLEmitter):
    def emit_sql(self) -> str:
        return """CREATE OR REPLACE FUNCTION un0.insert_group_for_tenant()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            AS $$
            BEGIN
                INSERT INTO un0.group(tenant_id, name) VALUES (NEW.id, NEW.name);
                RETURN NEW;
            END;
            $$;

            CREATE OR REPLACE TRIGGER insert_group_for_tenant_trigger
            -- The trigger to call the function
            AFTER INSERT ON un0.tenant
            FOR EACH ROW
            EXECUTE FUNCTION un0.insert_group_for_tenant();
            """


class DefaultGroupTenant(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = textwrap.dedent(
            """
            DECLARE
                tenant_id TEXT := current_setting('rls_var.tenant_id', true);
            BEGIN
                IF tenant_id IS NULL THEN
                    RAISE EXCEPTION 'tenant_id is NULL';
                END IF;

                NEW.tenant_id := tenant_id;

                RETURN NEW;
            END;
            """
        )
        return self.create_sql_function(
            "set_tenant_id",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )
