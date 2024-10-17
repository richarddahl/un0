# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.config import settings as sttngs


#################
# SQL CONSTANTS #
#################
"""
    NOTE - The use of f strings to provide the schema name and database name DOES NOT 
    provide any protection against SQL injection. 
    
    You cannot paramaterize postgres DDL statements.
    The names are defined in the .env file or are derived from the mapped classes.
    They are not user input, and are only used to create or update the db during
    developement, testing, and deployment.

    DON'T ALLOW UNTRUSTED USERS TO EDIT THE .env FILEs!
    
"""


DROP_DATABASE = f"""
-- Drop the database if it exists
DROP DATABASE IF EXISTS {sttngs.DB_NAME} WITH (FORCE);
"""


DROP_ROLES = f"""
-- Drop the roles if they exist
DROP ROLE IF EXISTS {sttngs.DB_NAME}_admin;
DROP ROLE IF EXISTS {sttngs.DB_NAME}_writer;
DROP ROLE IF EXISTS {sttngs.DB_NAME}_reader;
DROP ROLE IF EXISTS {sttngs.DB_NAME}_login;
DROP ROLE IF EXISTS {sttngs.DB_NAME}_base_role;
"""


CREATE_ROLES = f"""
-- Create the base role with permissions that all other users will inherit
DO $$
BEGIN
    -- Create the base role with permissions that all other users will inherit
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{sttngs.DB_NAME}_base_role') THEN
        CREATE ROLE {sttngs.DB_NAME}_base_role NOINHERIT;
    END IF;

    -- Create the reader role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{sttngs.DB_NAME}_reader') THEN
        CREATE ROLE {sttngs.DB_NAME}_reader INHERIT IN ROLE {sttngs.DB_NAME}_base_role;
    END IF;

    -- Create the writer role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{sttngs.DB_NAME}_writer') THEN

        CREATE ROLE {sttngs.DB_NAME}_writer INHERIT IN ROLE {sttngs.DB_NAME}_base_role;
    END IF;

    -- Create the admin role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{sttngs.DB_NAME}_security') THEN
        CREATE ROLE {sttngs.DB_NAME}_security INHERIT IN ROLE {sttngs.DB_NAME}_base_role;
    END IF;

    -- Create the admin role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{sttngs.DB_NAME}_admin') THEN
        CREATE ROLE {sttngs.DB_NAME}_admin INHERIT IN ROLE {sttngs.DB_NAME}_base_role;
    END IF;

    -- Create the authentication role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{sttngs.DB_NAME}_login') THEN
        CREATE ROLE {sttngs.DB_NAME}_login NOINHERIT LOGIN PASSWORD '{sttngs.DB_USER_PW}' IN ROLE
            {sttngs.DB_NAME}_base_role;
    END IF;

    -- Grant the reader, writer, and admin roles to the authentication role
    -- Allows the login role to SET ROLE to any of the other roles
    GRANT {sttngs.DB_NAME}_reader, {sttngs.DB_NAME}_writer, {sttngs.DB_NAME}_admin TO
        {sttngs.DB_NAME}_login;
END $$;
"""


CREATE_DATABASE = f"""
-- Create the database
CREATE DATABASE {sttngs.DB_NAME} WITH OWNER = {sttngs.DB_NAME}_admin;
"""


CREATE_SCHEMAS = f"""
-- Create the un0 schemas
CREATE SCHEMA IF NOT EXISTS un0 AUTHORIZATION {sttngs.DB_NAME}_admin;
CREATE SCHEMA IF NOT EXISTS {sttngs.DB_SCHEMA} AUTHORIZATION {sttngs.DB_NAME}_admin;
"""


CONFIGURE_AGE_EXTENSION = f"""
-- Configuring the age extension
GRANT USAGE ON SCHEMA ag_catalog TO
    {sttngs.DB_NAME}_admin,
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer;
ALTER SCHEMA ag_catalog OWNER TO {sttngs.DB_NAME}_admin;
SELECT * FROM ag_catalog.create_graph('graph');
ALTER TABLE ag_catalog.ag_graph OWNER TO {sttngs.DB_NAME}_admin;
ALTER TABLE ag_catalog.ag_label OWNER TO {sttngs.DB_NAME}_admin;
ALTER TABLE graph._ag_label_edge OWNER TO {sttngs.DB_NAME}_admin;
ALTER TABLE graph._ag_label_vertex OWNER TO {sttngs.DB_NAME}_admin;
ALTER SEQUENCE graph._ag_label_edge_id_seq OWNER TO {sttngs.DB_NAME}_admin;
ALTER SEQUENCE graph._ag_label_vertex_id_seq OWNER TO {sttngs.DB_NAME}_admin;
ALTER SEQUENCE graph._label_id_seq OWNER TO {sttngs.DB_NAME}_admin;
"""


REVOKE_ACCESS = f"""
-- Explicitly revoke all privileges on all schemas and tables
REVOKE ALL ON SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {sttngs.DB_SCHEMA} 
FROM
    public,
    {sttngs.DB_NAME}_base_role,
    {sttngs.DB_NAME}_login,
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer,
    {sttngs.DB_NAME}_admin;

REVOKE ALL ON ALL TABLES IN SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {sttngs.DB_SCHEMA} 
FROM
    public,
    {sttngs.DB_NAME}_base_role,
    {sttngs.DB_NAME}_login,
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer,
    {sttngs.DB_NAME}_admin;

REVOKE CONNECT ON DATABASE {sttngs.DB_NAME} FROM
    public,
    {sttngs.DB_NAME}_base_role,
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer,
    {sttngs.DB_NAME}_admin;
"""


SET_SEARCH_PATHS = f"""
-- Set the search paths for the roles
ALTER ROLE
    {sttngs.DB_NAME}_base_role
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA};

ALTER ROLE
    {sttngs.DB_NAME}_login
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA};


ALTER ROLE
    {sttngs.DB_NAME}_reader
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA};

ALTER ROLE
    {sttngs.DB_NAME}_writer 
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA};

ALTER ROLE
    {sttngs.DB_NAME}_admin
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA}; 

ALTER ROLE
    {sttngs.DB_NAME}_security
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA};
"""


CONFIGURE_ROLE_SCHEMA_PRIVILEGES = f"""
-- Grant ownership of the un0 schemas to the DB admin role
ALTER SCHEMA audit OWNER TO {sttngs.DB_NAME}_admin;
ALTER SCHEMA un0 OWNER TO {sttngs.DB_NAME}_admin;
ALTER SCHEMA graph OWNER TO {sttngs.DB_NAME}_admin;
ALTER SCHEMA ag_catalog OWNER TO {sttngs.DB_NAME}_admin;

ALTER SCHEMA {sttngs.DB_SCHEMA} OWNER TO {sttngs.DB_NAME}_admin;
ALTER TABLE audit.record_version OWNER TO {sttngs.DB_NAME}_admin;

-- Grant connect privileges to the DB login role
GRANT CONNECT ON DATABASE {sttngs.DB_NAME} TO {sttngs.DB_NAME}_login;

-- Grant usage privileges for users to created schemas
GRANT USAGE ON SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {sttngs.DB_SCHEMA}
TO
    {sttngs.DB_NAME}_security,
    {sttngs.DB_NAME}_login,
    {sttngs.DB_NAME}_admin,
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer;

GRANT CREATE ON SCHEMA
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA}
TO
    {sttngs.DB_NAME}_security,
    {sttngs.DB_NAME}_admin;

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {sttngs.DB_SCHEMA}
TO
    {sttngs.DB_NAME}_security,
    {sttngs.DB_NAME}_login,
    {sttngs.DB_NAME}_admin,
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer;

GRANT {sttngs.DB_NAME}_admin TO {sttngs.DB_NAME}_login WITH INHERIT FALSE, SET TRUE;
GRANT {sttngs.DB_NAME}_writer TO {sttngs.DB_NAME}_login WITH INHERIT FALSE, SET TRUE;
GRANT {sttngs.DB_NAME}_reader TO {sttngs.DB_NAME}_login WITH INHERIT FALSE, SET TRUE;
GRANT {sttngs.DB_NAME}_security TO {sttngs.DB_NAME}_login WITH INHERIT FALSE, SET TRUE;
"""


CONFIGURE_ROLE_TABLE_PRIVILEGES = f"""
-- Grant table privileges to the roles
GRANT SELECT ON ALL TABLES IN SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {sttngs.DB_SCHEMA}
TO
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer;

GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, TRIGGER ON ALL TABLES IN SCHEMA
    un0,
    audit,
    graph,
    {sttngs.DB_SCHEMA} 
TO
    {sttngs.DB_NAME}_writer,
    {sttngs.DB_NAME}_admin;

REVOKE SELECT, INSERT, UPDATE (id) ON un0.user FROM 
    {sttngs.DB_NAME}_reader,
    {sttngs.DB_NAME}_writer;

GRANT ALL ON ALL TABLES IN SCHEMA
    audit,
    graph,
    ag_catalog
TO
    {sttngs.DB_NAME}_admin;
"""


CREATE_EXTENSIONS = f"""
-- Create the extensions
SET search_path TO un0;

-- Creating the btree_gist extension
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Creating the supa_audit extension
CREATE EXTENSION IF NOT EXISTS supa_audit CASCADE;

-- Creating the pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Creating the pgjwt extension
CREATE EXTENSION IF NOT EXISTS pgjwt;

-- Creating the age extension
CREATE EXTENSION IF NOT EXISTS age;
"""

SET_PGMETA_CONFIG = f"""
-- Set the pgmeta configuration for supa_audit
SET pgmeta.log = 'all';
SET pgmeta.log_relation = on;
SET pgmeta.log_line_prefix = '%m %u %d [%p]: ';
"""


CREATE_INSERT_RELATED_OBJECT_FUNCTION = f"""
CREATE OR REPLACE FUNCTION un0.insert_relatedobject(schema_name VARCHAR, table_name VARCHAR)
RETURNS VARCHAR(26)
LANGUAGE plpgsql
AS $$
DECLARE
    rel_obj_id VARCHAR(26);
    tabletype_id INT;
BEGIN
    /*
    Function used to insert a record into the relatedobject table, when a record is inserted
    into a table that has a PK that is a FK to the relatedobject table.
    */
    SELECT id
        FROM un0.tabletype
        WHERE schema = schema_name AND name = table_name
        INTO tabletype_id;

    rel_obj_id := un0.generate_ulid(); 

    INSERT INTO un0.relatedobject (id, tabletype_id)
    VALUES (rel_obj_id, tabletype_id);

    RETURN rel_obj_id;
END;
$$;
"""

CREATE_SET_OWNER_AND_MODIFIED_FUNCTION = f"""
CREATE OR REPLACE FUNCTION un0.set_owner_and_modified()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    user_id VARCHAR(26) := current_setting('user_var.id', true);
    estimate INT;
BEGIN
    /* 
    Function used to set the owner_id and modified_by_id fields
    of a table to the user_id of the user making the change. 
    */

    SELECT current_setting('user_var.id', true) INTO user_id;

    IF user_id IS NULL THEN
        /*
        This should only happen when the very first user is created
        and therefore a user_id cannot be set in the session variables
        */
        SELECT reltuples AS estimate FROM PG_CLASS WHERE relname = TG_TABLE_NAME INTO estimate;
        IF TG_TABLE_NAME = 'user' AND estimate < 1 THEN
            RETURN NEW;
        ELSE
            RAISE EXCEPTION 'user_id is NULL';
        END IF;
    END IF;

    IF user_id = '' THEN
        RAISE EXCEPTION 'user_id is an empty string';
    END IF;

    IF TG_OP = 'INSERT' THEN
        NEW.owner_id = user_id;
        NEW.modified_by_id = user_id;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        NEW.modified_by_id = user_id;
    END IF;

    RETURN NEW;
END;
$$;
"""

CREATE_VALIDATE_DELETE_FUNCTION = f"""
CREATE OR REPLACE FUNCTION un0.validate_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    user_id VARCHAR(26);
BEGIN
    /* 
    Function used to validate that a record can be deleted.
    IF the record previously had is_deleted set to false the function
    returns the record, allowing the delete to proceed.
    otherwise Sets the is_deleted field to true and the deleted_by_id field to the user_id
    */

    SELECT current_setting('user_var.id', true) into user_id;

    IF user_id IS NULL THEN
        RAISE EXCEPTION 'user_id is NULL';
    END IF;

    IF OLD.is_deleted IS TRUE THEN
        RETURN OLD;
    ELSE
        EXECUTE format('
            UPDATE %I 
            SET is_deleted = true, deleted_by_id = %L 
            WHERE id = %L', TG_TABLE_NAME, user_id, OLD.id
        );
        RETURN NULL;
    END IF;
END;
$$;
"""


CREATE_PGULID = f"""
-- pgulid is based on OK Log's Go implementation of the ULID spec
--
-- https://github.com/oklog/ulid
-- https://github.com/ulid/spec
--
-- Copyright 2016 The Oklog Authors
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
-- http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE FUNCTION un0.generate_ulid()
RETURNS TEXT
AS $$
DECLARE
  -- Crockford's Base32
  encoding   BYTEA = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  timestamp  BYTEA = '\\000\\000\\000\\000\\000\\000';
  output     TEXT = '';

  unix_time  BIGINT;
  ulid       BYTEA;
BEGIN
  -- 6 timestamp bytes
  unix_time = (EXTRACT(EPOCH FROM CLOCK_TIMESTAMP()) * 1000)::BIGINT;
  timestamp = SET_BYTE(timestamp, 0, (unix_time >> 40)::BIT(8)::INTEGER);
  timestamp = SET_BYTE(timestamp, 1, (unix_time >> 32)::BIT(8)::INTEGER);
  timestamp = SET_BYTE(timestamp, 2, (unix_time >> 24)::BIT(8)::INTEGER);
  timestamp = SET_BYTE(timestamp, 3, (unix_time >> 16)::BIT(8)::INTEGER);
  timestamp = SET_BYTE(timestamp, 4, (unix_time >> 8)::BIT(8)::INTEGER);
  timestamp = SET_BYTE(timestamp, 5, unix_time::BIT(8)::INTEGER);

  -- 10 entropy bytes
  ulid = timestamp || un0.gen_random_bytes(10);

  -- Encode the timestamp
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 0) & 224) >> 5));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 0) & 31)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 1) & 248) >> 3));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 1) & 7) << 2) | ((GET_BYTE(ulid, 2) & 192) >> 6)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 2) & 62) >> 1));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 2) & 1) << 4) | ((GET_BYTE(ulid, 3) & 240) >> 4)));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 3) & 15) << 1) | ((GET_BYTE(ulid, 4) & 128) >> 7)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 4) & 124) >> 2));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 4) & 3) << 3) | ((GET_BYTE(ulid, 5) & 224) >> 5)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 5) & 31)));

  -- Encode the entropy
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 6) & 248) >> 3));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 6) & 7) << 2) | ((GET_BYTE(ulid, 7) & 192) >> 6)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 7) & 62) >> 1));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 7) & 1) << 4) | ((GET_BYTE(ulid, 8) & 240) >> 4)));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 8) & 15) << 1) | ((GET_BYTE(ulid, 9) & 128) >> 7)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 9) & 124) >> 2));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 9) & 3) << 3) | ((GET_BYTE(ulid, 10) & 224) >> 5)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 10) & 31)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 11) & 248) >> 3));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 11) & 7) << 2) | ((GET_BYTE(ulid, 12) & 192) >> 6)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 12) & 62) >> 1));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 12) & 1) << 4) | ((GET_BYTE(ulid, 13) & 240) >> 4)));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 13) & 15) << 1) | ((GET_BYTE(ulid, 14) & 128) >> 7)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 14) & 124) >> 2));
  output = output || CHR(GET_BYTE(encoding, ((GET_BYTE(ulid, 14) & 3) << 3) | ((GET_BYTE(ulid, 15) & 224) >> 5)));
  output = output || CHR(GET_BYTE(encoding, (GET_BYTE(ulid, 15) & 31)));

  RETURN output;
END
$$
LANGUAGE plpgsql
VOLATILE;
"""


CREATE_AUTHORIZE_USER_FUNCTION = f"""
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
    full_role_name VARCHAR:= '{sttngs.DB_NAME}_' || role_name;
    admin_role_name VARCHAR:= '{sttngs.DB_NAME}_' || 'admin';
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


CREATE_TOKEN_SECRET_TABLE = f"""
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


CREATE_USER_TABLE_RLS_SELECT_POLICY = f"""
/*
Enable RLS on the user table with policy
*/
ALTER TABLE un0.user ENABLE ROW LEVEL SECURITY;
ALTER TABLE un0.user FORCE ROW LEVEL SECURITY;

/* 
The policy to allow:
    Superusers to select all user records;
    All other users to select only user records associated with their tenant;
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
Regular users cannot insert user records.
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
Regular users cannot delete user records.
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


CREATE_INSERT_GROUP_CONSTRAINT = f"""
ALTER TABLE un0.group ADD CONSTRAINT ck_can_insert_group
    CHECK (un0.can_insert_group(tenant_id) = true);
"""


CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER = f"""
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


CREATE_INSERT_TABLEPERMISSION_FUNCTION_AND_TRIGGER = f"""
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

CREATE_GET_PERMISSIBLE_TABLEPERMISSIONS_FUNCTION = f"""
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
