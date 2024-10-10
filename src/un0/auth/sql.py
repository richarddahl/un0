# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from un0.config import settings as sttngs


#########################################################
# SQL FUNCTIONS THAT REQUIRE A SCHEMA AND/OR TABLE NAME #
#########################################################


def enable_rls(table_name: str):
    return textwrap.dedent(
        f"""
        -- Enable RLS for the table
        ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;
    """
    )


def create_superuser(
    email: str = sttngs.SUPERUSER_EMAIL,
    handle: str = sttngs.SUPERUSER_HANDLE,
    full_name: str = sttngs.SUPERUSER_FULL_NAME,
) -> str:
    return textwrap.dedent(
        f"""
        /*
        Creates the superuser for the application.
        */

        INSERT INTO un0.user (email, handle, full_name, is_superuser)
        VALUES('{email}', '{handle}', '{full_name}', true)
        RETURNING id;
        """
    )


def create_authorize_user_function(db_name: str = sttngs.DB_NAME):
    return textwrap.dedent(
        f"""
        CREATE OR REPLACE FUNCTION un0.authorize_user(token TEXT, role_name VARCHAR DEFAULT 'reader')
        /*
        Function to verify a JWT token and set the session variables necessary for enforcing RLS
        Ensures that:
            The token is valid or
                raises an Exception (Invalid Token)
            The token contains a sub (which is an email address) or
                raises an Exception (Token does not contain a sub)
            The email address provided in the sub is of a user in the user table or
                raises an Exception (User not found)
            The user is active or  Raises an Exception (User is not active)
            The user is not deleted or Raises an Exception (User was deleted)
        If all checks pass, returns the information necessary to enforce RLS otherwise raises an Exception

        The information for RLS is:
            user_id: The ID of the user 
            is_superuser: Whether the user is a superuser
            is_tenant_admin: Whether the user is a tenant admin
            tenant_id: The ID of the tenant to which the user is associated

        ::param token: The JWT token to verify
        ::param role_name: The role to set for the session
        */
            RETURNS BOOLEAN
            LANGUAGE plpgsql
        AS $$

        DECLARE
            token_header JSONB;
            token_payload JSONB;
            token_valid BOOLEAN;
            sub VARCHAR;
            expiration INT;
            user_email VARCHAR; 
            user_id VARCHAR(26);
            user_is_superuser VARCHAR(5);
            user_is_tenant_admin VARCHAR(5);
            user_tenant_id VARCHAR(26);
            user_is_active BOOLEAN;
            user_is_deleted BOOLEAN;
            token_secret VARCHAR;
            full_role_name VARCHAR:= '{db_name}_' || role_name;
            admin_role_name VARCHAR:= '{db_name}_' || 'admin';
        BEGIN
            -- Set the role to the admin role to read from the token_secret table
            EXECUTE 'SET ROLE ' || admin_role_name;

            -- Get the secret from the token_secret table
            SELECT secret FROM un0.token_secret INTO token_secret;

            -- Verify the token
            SELECT header, payload, valid
            FROM un0.verify(token, token_secret)
            INTO token_header, token_payload, token_valid;

            IF token_valid THEN

                -- Get the sub from the token payload
                sub := token_payload ->> 'sub';

                IF sub IS NULL THEN
                    RAISE EXCEPTION 'no sub in token';
                END IF;

                -- Get the expiration from the token payload
                expiration := token_payload ->> 'exp';
                IF expiration IS NULL THEN
                    RAISE EXCEPTION 'no exp in token';
                END IF;

                /*
                Set the session variable for the user's email so that it can be used
                in the query to get the user's information
                */
                PERFORM set_config('user_var.email', sub, true);

                -- Query the user table for the user to get the values for the session variables
                SELECT id, email, is_superuser, is_tenant_admin, tenant_id, is_active, is_deleted 
                FROM un0.user
                WHERE email = sub
                INTO
                    user_id,
                    user_email,
                    user_is_superuser,
                    user_is_tenant_admin,
                    user_tenant_id,
                    user_is_active,
                    user_is_deleted;

                IF user_id IS NULL THEN
                    RAISE EXCEPTION 'user not found';
                END IF;

                IF user_is_active = FALSE THEN 
                    RAISE EXCEPTION 'user is not active';
                END IF; 

                IF user_is_deleted = TRUE THEN
                    RAISE EXCEPTION 'user was deleted';
                END IF; 

                -- Set the session variables used for RLS
                PERFORM set_config('user_var.email', user_email, true);
                PERFORM set_config('user_var.id', user_id, true);
                PERFORM set_config('user_var.is_superuser', user_is_superuser, true);
                PERFORM set_config('user_var.is_tenant_admin', user_is_tenant_admin, true);
                PERFORM set_config('user_var.tenant_id', user_tenant_id, true);

                --Set the role to the role passed in
                EXECUTE 'SET ROLE ' || full_role_name;

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


#################
# SQL CONSTANTS #
#################


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
        {sttngs.MAX_INDIVIDUAL_GROUPS} > 0 AND
        group_count >= {sttngs.MAX_INDIVIDUAL_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        tenanttype = 'SMALL_BUSINESS' AND
        {sttngs.MAX_SMALL_BUSINESS_GROUPS} > 0 AND
        group_count >= {sttngs.MAX_SMALL_BUSINESS_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        tenanttype = 'CORPORATE' AND
        {sttngs.MAX_CORPORATE_GROUPS} > 0 AND
        group_count >= {sttngs.MAX_CORPORATE_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        tenanttype = 'ENTERPRISE' AND
        {sttngs.MAX_ENTERPRISE_GROUPS} > 0 AND
        group_count >= {sttngs.MAX_ENTERPRISE_GROUPS} THEN
            RETURN false;
    END IF;
    RETURN true;
END
$$;
"""

CREATE_TOKEN_SECRET = (
    f"INSERT INTO un0.token_secret(secret) VALUES ('{sttngs.TOKEN_SECRET}');"
)


CREATE_TOKEN_SECRET_TABLE = """
CREATE TABLE un0.token_secret (
    secret TEXT PRIMARY KEY
);

CREATE UNIQUE INDEX token_secret_secret_idx ON un0.token_secret(secret);

CREATE OR REPLACE FUNCTION un0.set_token_secret()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM un0.token_secret;
    RETURN NEW;
END;
$$;

CREATE TRIGGER set_token_secret_trigger
BEFORE INSERT ON un0.token_secret
FOR EACH ROW
EXECUTE FUNCTION un0.set_token_secret();
"""


CREATE_USER_TABLE_RLS_SELECT_POLICY = """
/*
Enable RLS on the user table with policy
*/
ALTER TABLE un0.user ENABLE ROW LEVEL SECURITY;
ALTER TABLE un0.user FORCE ROW LEVEL SECURITY;

/* 
The policy to allow:
    Superusers to select all user records;
    All other users to select all users records associated with their tenant;
*/
CREATE POLICY user_select_policy
ON un0.user FOR SELECT
USING (
    email = current_setting('user_var.email', true)::VARCHAR OR
    current_setting('user_var.is_superuser', true)::BOOLEAN OR
    tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
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
    current_setting('user_var.is_superuser', true)::BOOLEAN OR
    email = current_setting('user_var.user_email', true)::VARCHAR(26) OR
    (
        current_setting('user_var.is_tenant_admin', true)::BOOLEAN AND
        tenant_id = current_setting('user_var.tenant_id', true)::VARCHAR(26)
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


/*
The policy to allow:
    Superusers to delete user records;
    Tenant Admins to delete user records associated with the tenant;
    Regular users cannot delete user records;
*/
CREATE POLICY user_delete_policy
ON un0.user FOR DELETE
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


CREATE_INSERT_GROUP_CONSTRAINT = """
ALTER TABLE un0.group ADD CONSTRAINT ck_can_insert_group
    CHECK (un0.can_insert_group(tenant_id) = true);
"""


CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER = """
CREATE OR REPLACE FUNCTION un0.insert_group_for_tenant()
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO un0.group(tenant_id, name) VALUES (NEW.id, NEW.name);
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER insert_group_for_tenant_trigger
    -- The trigger to call the function: AFTER INSERT
    AFTER INSERT ON un0.tenant
    FOR EACH ROW
    EXECUTE FUNCTION un0.insert_group_for_tenant();
"""


CREATE_INSERT_tablepermission_FUNCTION_AND_TRIGGER = """
CREATE OR REPLACE FUNCTION un0.insert_tablepermissions()
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    /*
    Function to create a new TablePermission record when a new TableType is inserted.
    Records are created for each tabletype with the following combinations of permissions:
        [SELECT]
        [SELECT, INSERT]
        [SELECT, UPDATE]
        [SELECT, INSERT, UPDATE]
        [SELECT, INSERT, UPDATE, DELETE]
    Deleted automatically by the DB via the FK Constraints ondelete when a tabletype is deleted.
    */
    INSERT INTO un0.tablepermission(tabletype_id, actions)
        VALUES (NEW.id, ARRAY['SELECT']::un0.permission_name[]);
    INSERT INTO un0.tablepermission(tabletype_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT']::un0.permission_name[]);
    INSERT INTO un0.tablepermission(tabletype_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'UPDATE']::un0.permission_name[]);
    INSERT INTO un0.tablepermission(tabletype_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE']::un0.permission_name[]);
    INSERT INTO un0.tablepermission(tabletype_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']::un0.permission_name[]);
    RETURN NEW;
END;
$$;

-- The trigger to call the function: AFTER INSERT
CREATE OR REPLACE TRIGGER create_tablepermissions_trigger
    AFTER INSERT ON un0.tabletype
    FOR EACH ROW
    EXECUTE FUNCTION un0.insert_tablepermissions();
"""

CREATE_GET_PERMISSIBLE_tablepermissionS_FUNCTION = """
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
    JOIN un0.tablepermission tp ON ugr.role_id = tp.id
    WHERE u.id = session_user_id AND tp.is_active = TRUE
    AND tp.table_name = query_table_name;
END;
$$;

"""
