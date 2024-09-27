# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from un0.config import settings

CREATE_SUPERUSER = f"""
/*
Creates the superuser for the application 
Done before RLS is enabled on the user table
*/

INSERT INTO un0.user(email, handle, full_name, is_superuser)
VALUES('{settings.SUPERUSER_EMAIL}', '{settings.SUPERUSER_HANDLE}', '{settings.SUPERUSER_FULL_NAME}', true);
"""


CREATE_LIST_SESSION_VARIABLES_FUNCTION = """
CREATE OR REPLACE FUNCTION un0.list_session_variables()
    RETURNS JSONB
    LANGUAGE plpgsql
AS $$
BEGIN
    RETURN jsonb_build_object(
        'id', current_setting('s_var.user_id', true),
        'email', current_setting('s_var.user_email', true),
        'is_superuser', current_setting('s_var.is_superuser', true),
        'is_tenant_admin', current_setting('s_var.is_tenant_admin', true),
        'tenant_id', current_setting('s_var.tenant_id', true)
    );
END;
$$;
"""


def create_verify_jwt_and_set_vars_function(db_name: str = settings.DB_NAME):
    return textwrap.dedent(
        f"""
        CREATE OR REPLACE FUNCTION un0.verify_jwt_and_set_vars(token TEXT)
        /*
        Function to verify a JWT token and set the session variables necessary for enforcing RLS
        Ensures that:
            The token is valid or raises an Exception (Invalid Token)
            The token contains a sub (which is an email address) or raises an Exception (Token does not contain a sub)
            The email address provided in the sub is for an active user record in the user table or raises an Exception (User not found)

        If all checks pass, sets the session variables used to enforce RLS and returns True, otherwise returns False:
            user_email: The email address of the user (a natural key and the sub in the token)
            is_superuser: Whether the user is a superuser
            is_tenant_admin: Whether the user is a tenant admin
            tenant_id: The ID of the tenant to which the user is associated

        param token: The JWT token to verify
        */
            RETURNS  BOOLEAN
            LANGUAGE plpgsql
        AS $$

        DECLARE
            token_header JSONB;
            token_payload JSONB;
            token_valid BOOLEAN;
            sub VARCHAR;
            expiration INT;
            user_is_superuser VARCHAR(5);
            user_is_tenant_admin VARCHAR(5);
            user_user_id VARCHAR(26);
            user_tenant_id VARCHAR(26);
            user_is_active BOOLEAN;
            user_is_deleted BOOLEAN;
        BEGIN
            -- Verify the token
            SELECT header, payload, valid
            FROM un0.verify(token, '{settings.TOKEN_SECRET}')
            INTO token_header, token_payload, token_valid;

            IF token_valid THEN

                -- Get the sub from the token payload
                sub := token_payload ->> 'sub';

                IF sub IS NULL THEN
                    RAISE EXCEPTION 'token does not contain a sub';
                END IF;

                -- Get the expiration from the token payload
                expiration := token_payload ->> 'exp';
                IF expiration IS NULL THEN
                    RAISE EXCEPTION 'token has no expiration';
                END IF;

                -- Set the role to the admin role to query the user table bypassing the RLS policy
                SET ROLE {db_name}_admin;

                -- Query the user table for the user to get the relevant session variables
                SELECT id, is_superuser, is_tenant_admin, tenant_id, is_active, is_deleted 
                FROM un0.user
                WHERE email = sub
                INTO
                    user_user_id,
                    user_is_superuser,
                    user_is_tenant_admin,
                    user_tenant_id,
                    user_is_active,
                    user_is_deleted;

                IF user_user_id IS NULL THEN
                    RAISE EXCEPTION 'user not found';
                END IF;

                IF user_is_active = FALSE THEN 
                    RAISE EXCEPTION 'user is not active';
                END IF; 

                IF user_is_deleted = TRUE THEN
                    RAISE EXCEPTION 'user was deleted';
                END IF; 

                -- Set the role to the reader
                SET ROLE {db_name}_reader;

                -- Set the session variables used for RLS
                PERFORM set_config('s_var.user_email', sub, true);
                PERFORM set_config('s_var.user_id', user_user_id, true);
                PERFORM set_config('s_var.is_superuser', user_is_superuser, true);
                PERFORM set_config('s_var.is_tenant_admin', user_is_tenant_admin, true);
                PERFORM set_config('s_var.tenant_id', user_tenant_id, true);

            ELSE
                -- Token failed verification
                RAISE EXCEPTION 'invalid token';
            END IF;
            -- Return the validity of the token
            RETURN token_valid;
        END;
        $$
        """
    )


CREATE_USER_TABLE_RLS_SELECT_POLICY = """
/*
Enable RLS on the user table with policy
*/
ALTER TABLE un0.user ENABLE ROW LEVEL SECURITY;
ALTER TABLE un0.user FORCE ROW LEVEL SECURITY;

/* 
The policy to allow:
    Superusers to select all user records;
    All other users to select all users records associated with the tenant;
*/
CREATE POLICY user_select_policy
ON un0.user FOR SELECT
USING (
    current_setting('s_var.is_superuser', true)::BOOLEAN OR
    tenant_id = current_setting('s_var.tenant_id', true)::VARCHAR(26)
);

/*
The policy to allow:
    Superusers to insert user records;
    Tenant Admins to insert user records associated with the tenant;
    Regular users cannot insert user records;
*/
CREATE POLICY user_insert_policy
ON un0.user FOR INSERT
WITH CHECK (
    current_setting('s_var.is_superuser', true)::BOOLEAN OR
    email = current_setting('s_var.user_email', true)::VARCHAR(26) OR
    (
        current_setting('s_var.is_tenant_admin', true)::BOOLEAN AND
        tenant_id = current_setting('s_var.tenant_id', true)::VARCHAR(26)
    )
);

/* 
The policy to allow:
    Superusers to update all user records;
    Tenant Admins to update user records associated with the tenant;
    All other users to update only their own user record;
*/
CREATE POLICY user_update_policy
ON un0.user FOR UPDATE
WITH CHECK (
    current_setting('s_var.is_superuser', true)::BOOLEAN OR
    email = current_setting('s_var.user_email', true)::VARCHAR(26) OR
    (
        current_setting('s_var.is_tenant_admin', true)::BOOLEAN AND
        tenant_id = current_setting('s_var.tenant_id', true)::VARCHAR(26)
    )
);

/*
The policy to allow:
    Superusers to delete user records;
    Tenant Admins to delete user records associated with the tenant;
    Regular users cannot delete user records;
*/
CREATE POLICY user_delete_policy
ON un0.user FOR DELETE
USING (
    current_setting('s_var.is_superuser', true)::BOOLEAN OR
    email = current_setting('s_var.user_email', true)::VARCHAR(26) OR
    (
        current_setting('s_var.is_tenant_admin', true)::BOOLEAN AND
        tenant_id = current_setting('s_var.tenant_id', true)::VARCHAR(26)
    )
);
"""

CREATE_CAN_INSERT_GROUP_FUNCTION = f"""
CREATE OR REPLACE FUNCTION un0.can_insert_group(tenantid VARCHAR(26))
    RETURNS BOOLEAN
    LANGUAGE plpgsql
AS $$
DECLARE
    group_count INT4;
    tenanttype un0.tenanttype;
BEGIN
    SELECT tenant_type INTO tenanttype
    from tenant
    WHERE id = tenantid;

    SELECT COUNT(*) INTO group_count
    from group
    WHERE tenant_id = tenantid;

    IF tenanttype = 'INDIVIDUAL' AND
        {settings.MAX_INDIVIDUAL_GROUPS} > 0 AND
        group_count >= {settings.MAX_INDIVIDUAL_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        tenanttype = 'SMALL_BUSINESS' AND
        {settings.MAX_SMALL_BUSINESS_GROUPS} > 0 AND
        group_count >= {settings.MAX_SMALL_BUSINESS_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        tenanttype = 'CORPORATE' AND
        {settings.MAX_CORPORATE_GROUPS} > 0 AND
        group_count >= {settings.MAX_CORPORATE_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        tenanttype = 'ENTERPRISE' AND
        {settings.MAX_ENTERPRISE_GROUPS} > 0 AND
        group_count >= {settings.MAX_ENTERPRISE_GROUPS} THEN
            RETURN false;
    END IF;
    RETURN true;
END
$$;
"""


CREATE_SET_USER_OWNER_FUNCTION_AND_TRIGGER = """
CREATE OR REPLACE FUNCTION un0.set_user_owner_id()
    -- Function to set the owner_id of a user record to the current user, unless the user is a superuser
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.is_superuser THEN
        RETURN NEW;
    ELSE
        NEW.owner_id := current_setting('s_var.user_email', true);
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER set_user_owner_id_trigger
    BEFORE INSERT ON un0.user
    FOR EACH ROW
    EXECUTE FUNCTION un0.set_user_owner_id();
"""


def create_insert_group_check_constraint(db_name: str = settings.DB_NAME):
    return f"""
        SET ROLE {db_name}_admin;
        ALTER TABLE {db_name}.group ADD CONSTRAINT ck_can_insert_group
            CHECK (un0.can_insert_group(tenant_id) = true);
    """


CREATE_INSERT_GROUP_FOR_CUSTOMER_FUNCTION = """
CREATE OR REPLACE FUNCTION un0.insert_group_for_tenant()
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO un0.group(tenant_id, name) VALUES (NEW.id, NEW.name);
    RETURN NEW;
END;
$$;
"""


CREATE_INSERT_GROUP_FOR_CUSTOMER_TRIGGER = """
-- The trigger to call the function: AFTER INSERT
CREATE OR REPLACE TRIGGER insert_group_for_tenant_trigger
    AFTER INSERT ON un0.tenant
    FOR EACH ROW
    EXECUTE FUNCTION un0.insert_group_for_tenant();
"""


CREATE_INSERT_TABLE_PERMISSION_FUNCTION = """
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
CREATE OR REPLACE FUNCTION un0.insert_table_permissions()
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO un0.table_permission(permissive_table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT']::un0.permission_name[]);
    INSERT INTO un0.table_permission(permissive_table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT']::un0.permission_name[]);
    INSERT INTO un0.table_permission(permissive_table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'UPDATE']::un0.permission_name[]);
    INSERT INTO un0.table_permission(permissive_table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE']::un0.permission_name[]);
    INSERT INTO un0.table_permission(permissive_table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']::un0.permission_name[]);
    RETURN NEW;
END;
$$
"""

CREATE_INSERT_TABLE_PERMISSION_TRIGGER = """
-- The trigger to call the function: AFTER INSERT
CREATE OR REPLACE TRIGGER create_table_permissions_trigger
    AFTER INSERT ON un0.table_type
    FOR EACH ROW
    EXECUTE FUNCTION un0.insert_table_permissions();
"""

CREATE_GET_PERMISSIBLE_TABLE_PERMISSIONS_FUNCTION = """
/* 
Generate a SQL statement to retrieve all permissible groups for a given user.
:param user_email: The email address of the user.
:param session: The SQLAlchemy session to use for the query.
:return: A SQL statement string.
*/
CREATE OR REPLACE FUNCTION un0.get_permissible_groups(query_table_name VARCHAR(255))
    RETURNS VARCHAR[]
    LANGUAGE plpgsql
AS $$
DECLARE
    session_user_id := current_setting('session_user_id', true);
BEGIN
    SELECT g.*
    from group g
    JOIN un0.user_group_role ugr ON ugr.group_id = g.id
    JOIN un0.user u ON u.id = ugr.user_email
    JOIN un0.table_permission tp ON ugr.role_id = tp.id
    WHERE u.id = session_user_id AND tp.is_active = TRUE
    AND tp.table_name = query_table_name;
END;
$$;

"""


def enable_rls(table_name: str):
    return textwrap.dedent(
        f"""
        -- Enable RLS for the table
        ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
    """
    )
