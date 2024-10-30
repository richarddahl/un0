# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap


def user_select_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all user records;
            All other users to select only user records associated with their tenant;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            email = current_setting('user_var.email', true)::VARCHAR OR
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
        );
        """
    )


def user_insert_policy_sql(db_schema, table_name) -> str:
    return textwrap.dedent(
        f"""
        /*
        The policy to allow:
            Superusers to insert user records;
            Tenant Admins to insert user records associated with the tenant;
        Regular users cannot insert user records.
        */
        CREATE POLICY user_insert_policy
        ON {db_schema}.{table_name} FOR INSERT
        WITH CHECK (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            email = current_setting('user_var.user_email', true)::VARCHAR(26) OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            )
        );
        """
    )


def user_update_policy_sql(db_schema, table_name) -> str:
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all user records;
            All other users to select only user records associated with their tenant;
        */
        CREATE POLICY user_update_policy
        ON {db_schema}.{table_name} FOR UPDATE
        USING (
            email = current_setting('user_var.email', true)::VARCHAR OR
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
        );
        """
    )


def user_delete_policy_sql(db_schema, table_name) -> str:
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to delete user records;
            Tenant Admins to delete user records associated with the tenant;
        Regular users cannot delete user records.
        */
        CREATE POLICY user_delete_policy
        ON {db_schema}.{table_name} FOR DELETE
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                email = current_setting('user_var.user_email', true)::VARCHAR(26) AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26) 
            ) OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN = true AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) 
        );
        """
    )


def admin_select_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'SELECT')::VARCHAR[] 
            )
        );
        """
    )


def admin_insert_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'INSERT')::VARCHAR[] 
            )
        );
        """
    )


def admin_update_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'UPDATE')::VARCHAR[] 
            )
        );
        """
    )


def admin_delete_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'DELETE')::VARCHAR[] 
            )
        );
        """
    )


def default_select_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'SELECT')::VARCHAR[] 
            )
        );
        """
    )


def default_insert_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'INSERT')::VARCHAR[] 
            )
        );
        """
    )


def default_update_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'UPDATE')::VARCHAR[] 
            )
        );
        """
    )


def default_delete_policy_sql(db_schema, table_name):
    return textwrap.dedent(
        f"""
        /* 
        The policy to allow:
            Superusers to select all records;
            Tenant Admin users to select all records associated with their tenant;
            Regular users to select only records associated with their Groups or that they own.;
        */
        CREATE POLICY user_select_policy
        ON {db_schema}.{table_name} FOR SELECT
        USING (
            current_setting('user_var.is_superuser', true)::BOOLEAN OR
            (
                current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
                tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
            ) OR
            (
                owned_by_id = current_setting('user_var.id', true)::VARCHAR OR
                group_id IN un0.permissible_group_id_list({db_schema}, {table_name}, 'DELETE')::VARCHAR[] 
            )
        );
        """
    )
