# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
"""
    NOTE - The use of f strings to provide the schema name and database name DOES NOT 
    provide any protection against SQL injection. You cannot paramaterize postgres DDL 
    statements. The names are defined in the .env file, are not user input, and are only
    used at the beginning of projects to create the initial db.  
    
    That said, Don't inject SQL into your own database!
"""
import textwrap

from un0.config import settings


CREATE_USER_TABLE_RLS_POLICY = """
ALTER TABLE un0.user ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_select_policy
ON un0.user FOR SELECT
USING (un0.is_superuser());
"""

CREATE_IS_SUPERUSER_FUNCTION = """
/* simple function to check if a user is a superuser */

CREATE OR REPLACE FUNCTION un0.is_superuser()
    RETURNS BOOLEAN
    LANGUAGE plpgsql
AS $$
DECLARE 
    is_superuser BOOLEAN;
    current_user_email VARCHAR(26) := current_setting('app.user_email'::VARCHAR, true);
BEGIN
    /* Avoid a query if the current user is the app superuser as defined in the environement settings*/
    IF current_setting('app.superuser_email', true) = current_user_email THEN
        RETURN TRUE;
    END IF;

    SELECT is_superuser
    INTO is_superuser
    FROM un0.user
    WHERE email = current_user_email;
    RETURN is_superuser;
END;
$$;
"""


CREATE_IS_CUSTOMER_ADMIN_FUNCTION = """
/* simple function to check if a user is a customer_admin */
CREATE OR REPLACE FUNCTION un0.is_customer_admin()
    RETURNS BOOLEAN
    LANGUAGE plpgsql
AS $$
DECLARE
    is_customer_admin BOOLEAN;
    user_email VARCHAR(26) := current_setting('app.user_email', true);
BEGIN
    EXECUTE 'SELECT is_customer_admin
    FROM un0.user 
    WHERE email = $1' 
    INTO is_customer_admin 
    USING app_user_id;
    RETURN is_customer_admin;
END;
$$;
"""

CREATE_CAN_INSERT_GROUP_FUNCTION = f"""
CREATE OR REPLACE FUNCTION un0.can_insert_group(customerid VARCHAR(26))
    RETURNS BOOLEAN
    LANGUAGE plpgsql
AS $$
DECLARE
    group_count INT4;
    customertype un0.customertype;
BEGIN
    SELECT customer_type INTO customertype
    from customer
    WHERE id = customerid;

    SELECT COUNT(*) INTO group_count
    from group
    WHERE customer_id = customerid;

    IF customertype = 'INDIVIDUAL' AND
        {settings.MAX_INDIVIDUAL_GROUPS} > 0 AND
        group_count >= {settings.MAX_INDIVIDUAL_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        customertype = 'SMALL_BUSINESS' AND
        {settings.MAX_SMALL_BUSINESS_GROUPS} > 0 AND
        group_count >= {settings.MAX_SMALL_BUSINESS_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        customertype = 'CORPORATE' AND
        {settings.MAX_CORPORATE_GROUPS} > 0 AND
        group_count >= {settings.MAX_CORPORATE_GROUPS} THEN
            RETURN false;
    END IF;
    IF
        customertype = 'ENTERPRISE' AND
        {settings.MAX_ENTERPRISE_GROUPS} > 0 AND
        group_count >= {settings.MAX_ENTERPRISE_GROUPS} THEN
            RETURN false;
    END IF;
    RETURN true;
END
$$;
"""

CREATE_INSERT_GROUP_CHECK_CONSTRAINT = f"""
SET ROLE {settings.DB_NAME}_admin;
ALTER TABLE {settings.DB_NAME}.group ADD CONSTRAINT ck_can_insert_group
    CHECK (un0.can_insert_group(customer_id) = true);
"""

CREATE_INSERT_GROUP_FOR_CUSTOMER_FUNCTION = """
CREATE OR REPLACE FUNCTION un0.insert_group_for_customer()
    RETURNS TRIGGER
    LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO un0.group(customer_id, name) VALUES (NEW.id, NEW.name);
    RETURN NEW;
END;
$$;
"""


CREATE_INSERT_GROUP_FOR_CUSTOMER_TRIGGER = """
-- The trigger to call the function: AFTER INSERT
CREATE OR REPLACE TRIGGER insert_group_for_customer_trigger
    AFTER INSERT ON un0.customer
    FOR EACH ROW
    EXECUTE FUNCTION un0.insert_group_for_customer();
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
    INSERT INTO un0.table_permission(table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT']::un0.permission_name[]);
    INSERT INTO un0.table_permission(table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT']::un0.permission_name[]);
    INSERT INTO un0.table_permission(table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'UPDATE']::un0.permission_name[]);
    INSERT INTO un0.table_permission(table_type_id, actions)
        VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE']::un0.permission_name[]);
    INSERT INTO un0.table_permission(table_type_id, actions)
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
:param user_id: The ID of the user.
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
    JOIN un0.user u ON u.id = ugr.user_id
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
