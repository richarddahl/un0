# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
"""
    NOTE - The use of f strings to provide the schema name and database name DOES NOT 
    provide any protection against SQL injection. 
    
    You cannot paramaterize postgres DDL statements.
    The names are defined in the .env file or are derived from the mapped classes.
    They are not user input, and are only used to create or update the db during
    developement, testing, and deployment.
    
    That said, Don't inject SQL into your own database!
"""

import textwrap

from sqlalchemy import Table

from un0.config import settings as sttngs


#########################################################
# SQL FUNCTIONS THAT REQUIRE A SCHEMA AND/OR TABLE NAME #
#########################################################


def create_set_owner_and_modified_trigger(schema_table_name):
    return textwrap.dedent(
        f"""
        CREATE TRIGGER set_owner_and_modified_trigger
        BEFORE INSERT OR UPDATE ON {schema_table_name}
        FOR EACH ROW
        EXECUTE FUNCTION un0.set_owner_and_modified();
    """
    )


def create_validate_delete_trigger(schema_table_name):
    return textwrap.dedent(
        f"""
        CREATE TRIGGER validate_delete_trigger 
        BEFORE DELETE ON {schema_table_name}
        FOR EACH ROW
        EXECUTE FUNCTION un0.validate_delete();
    """
    )


def change_table_owner_and_set_privileges(table: Table, db_name: str):
    return f"""
    ALTER TABLE {table.schema}.{table.name} OWNER TO {db_name}_admin;
    GRANT SELECT ON {table.schema}.{table.name} TO
        {db_name}_reader,
        {db_name}_writer;
    GRANT INSERT, UPDATE, DELETE ON {table.schema}.{table.name} TO
        {db_name}_writer;
    """


def create_table_type_record(schema, name):
    return f"""
    -- Create the table_type record
    INSERT INTO un0.table_type (schema, name) VALUES ('{schema}', '{name}');
    """


def enable_auditing(schema_table_name):
    return f"""
    -- Enable auditing for the table
    SELECT audit.enable_tracking('{schema_table_name}'::regclass);
    """


def drop_database(db_name):
    return textwrap.dedent(
        f"""
        -- Drop the database if it exists
        DROP DATABASE IF EXISTS {db_name} WITH (FORCE);
        """
    )


def drop_roles(db_name):
    return textwrap.dedent(
        f"""
        -- Drop the roles if they exist
        DROP ROLE IF EXISTS {db_name}_admin;
        DROP ROLE IF EXISTS {db_name}_writer;
        DROP ROLE IF EXISTS {db_name}_reader;
        DROP ROLE IF EXISTS {db_name}_login;
        DROP ROLE IF EXISTS {db_name}_base_role;
        """
    )


def create_roles(db_name):
    return textwrap.dedent(
        f"""
        -- Create the base role with permissions that all other users will inherit
        DO $$
        BEGIN
            -- Create the base role with permissions that all other users will inherit
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_base_role') THEN
                CREATE ROLE {db_name}_base_role NOINHERIT;
            END IF;

            -- Create the reader role
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_reader') THEN
                CREATE ROLE {db_name}_reader INHERIT IN ROLE {db_name}_base_role;
            END IF;

            -- Create the writer role
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_writer') THEN

                CREATE ROLE {db_name}_writer INHERIT IN ROLE {db_name}_base_role;
            END IF;

            -- Create the admin role
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_security') THEN
                CREATE ROLE {db_name}_security INHERIT IN ROLE {db_name}_base_role;
            END IF;

            -- Create the admin role
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_admin') THEN
                CREATE ROLE {db_name}_admin INHERIT IN ROLE {db_name}_base_role;
            END IF;

            -- Create the authentication role
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_login') THEN
                CREATE ROLE {db_name}_login NOINHERIT LOGIN PASSWORD '{sttngs.DB_USER_PW}' IN ROLE
                    {db_name}_base_role;
            END IF;

            -- Grant the reader, writer, and admin roles to the authentication role
            -- Allows the login role to SET ROLE to any of the other roles
            GRANT {db_name}_reader, {db_name}_writer, {db_name}_admin TO
                {db_name}_login;
        END $$;
        """
    )


def create_database(db_name):
    return textwrap.dedent(
        f"""
        -- Create the database
        CREATE DATABASE {db_name} WITH OWNER = {db_name}_admin;
        """
    )


def create_schemas(db_name):
    return textwrap.dedent(
        f"""
        -- Create the un0 schemas
        CREATE SCHEMA IF NOT EXISTS un0 AUTHORIZATION {db_name}_admin;
        CREATE SCHEMA IF NOT EXISTS {sttngs.DB_SCHEMA} AUTHORIZATION {db_name}_admin;
        """
    )


def configure_age_extension(db_name):
    return textwrap.dedent(
        f"""
        -- Configuring the age extension
        GRANT USAGE ON SCHEMA ag_catalog TO
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;
        ALTER SCHEMA ag_catalog OWNER TO {db_name}_admin;
        SELECT * FROM ag_catalog.create_graph('graph');
        ALTER TABLE ag_catalog.ag_graph OWNER TO {db_name}_admin;
        ALTER TABLE ag_catalog.ag_label OWNER TO {db_name}_admin;
        ALTER TABLE graph._ag_label_edge OWNER TO {db_name}_admin;
        ALTER TABLE graph._ag_label_vertex OWNER TO {db_name}_admin;
        ALTER SEQUENCE graph._ag_label_edge_id_seq OWNER TO {db_name}_admin;
        ALTER SEQUENCE graph._ag_label_vertex_id_seq OWNER TO {db_name}_admin;
        ALTER SEQUENCE graph._label_id_seq OWNER TO {db_name}_admin;
        """
    )


def revoke_access(db_name):
    return textwrap.dedent(
        f"""
        -- Explicitly revoke all privileges on all schemas and tables
        REVOKE ALL ON SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {sttngs.DB_SCHEMA} 
        FROM
            public,
            {db_name}_base_role,
            {db_name}_login,
            {db_name}_reader,
            {db_name}_writer,
            {db_name}_admin;

        REVOKE ALL ON ALL TABLES IN SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {sttngs.DB_SCHEMA} 
        FROM
            public,
            {db_name}_base_role,
            {db_name}_login,
            {db_name}_reader,
            {db_name}_writer,
            {db_name}_admin;

        REVOKE CONNECT ON DATABASE {db_name} FROM
            public,
            {db_name}_base_role,
            {db_name}_reader,
            {db_name}_writer,
            {db_name}_admin;
        """
    )


def set_search_paths(db_name):
    return textwrap.dedent(
        f"""
        -- Set the search paths for the roles
        ALTER ROLE
            {db_name}_base_role
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA};

        ALTER ROLE
            {db_name}_login
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA};


        ALTER ROLE
            {db_name}_reader
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA};

        ALTER ROLE
            {db_name}_writer 
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA};
       
        ALTER ROLE
            {db_name}_admin
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA}; 

        ALTER ROLE
            {db_name}_security
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA};
        """
    )


def configure_role_schema_privileges(db_name):
    return textwrap.dedent(
        f"""
        -- Grant ownership of the un0 schemas to the DB admin role
        ALTER SCHEMA audit OWNER TO {db_name}_admin;
        ALTER SCHEMA un0 OWNER TO {db_name}_admin;
        ALTER SCHEMA graph OWNER TO {db_name}_admin;
        ALTER SCHEMA ag_catalog OWNER TO {db_name}_admin;

        ALTER SCHEMA {sttngs.DB_SCHEMA} OWNER TO {db_name}_admin;
        ALTER TABLE audit.record_version OWNER TO {db_name}_admin;

        -- Grant connect privileges to the DB login role
        GRANT CONNECT ON DATABASE {db_name} TO {db_name}_login;

        -- Grant usage privileges for users to created schemas
        GRANT USAGE ON SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {sttngs.DB_SCHEMA}
        TO
            {db_name}_security,
            {db_name}_login,
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;

        GRANT CREATE ON SCHEMA
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA}
        TO
            {db_name}_security,
            {db_name}_admin;

        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {sttngs.DB_SCHEMA}
        TO
            {db_name}_security,
            {db_name}_login,
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;

        GRANT {db_name}_admin TO {db_name}_login WITH INHERIT FALSE, SET TRUE;
        GRANT {db_name}_writer TO {db_name}_login WITH INHERIT FALSE, SET TRUE;
        GRANT {db_name}_reader TO {db_name}_login WITH INHERIT FALSE, SET TRUE;
        GRANT {db_name}_security TO {db_name}_login WITH INHERIT FALSE, SET TRUE;
        """
    )


def configure_role_table_privileges(db_name):
    return textwrap.dedent(
        f"""
        -- Grant table privileges to the roles
        GRANT SELECT ON ALL TABLES IN SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {sttngs.DB_SCHEMA}
        TO
            {db_name}_reader,
            {db_name}_writer;

        GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, TRIGGER ON ALL TABLES IN SCHEMA
            un0,
            audit,
            graph,
            {sttngs.DB_SCHEMA} 
        TO
            {db_name}_writer,
            {db_name}_admin;

        REVOKE SELECT, INSERT, UPDATE (id) ON un0.user FROM 
            {db_name}_reader,
            {db_name}_writer;

        GRANT ALL ON ALL TABLES IN SCHEMA
            audit,
            graph,
            ag_catalog
        TO
            {db_name}_admin;
        """
    )


def create_history_table(table_schema, table_name):
    return textwrap.dedent(
        f"""
        CREATE TABLE audit.{table_schema}_{table_name}
        AS (SELECT * FROM {table_schema}.{table_name})
        WITH NO DATA;

        ALTER TABLE audit.{table_schema}_{table_name}
        ADD COLUMN pk INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

        CREATE INDEX {table_schema}_{table_name}_pk_idx
        ON audit.{table_schema}_{table_name} (pk);

        CREATE INDEX {table_schema}_{table_name}_id_modified_at_idx
        ON audit.{table_schema}_{table_name} (id, modified_at);
        """
    )


def create_history_table_trigger(table_schema, table_name) -> str:
    return textwrap.dedent(
        f"""
        CREATE OR REPLACE FUNCTION {table_schema}.{table_name}_audit()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            INSERT INTO audit.{table_schema}_{table_name}
            SELECT *
            FROM {table_schema}.{table_name}
            WHERE id = NEW.id;
            RETURN NEW;
        END;
        $$;

        CREATE OR REPLACE TRIGGER {table_name}_audit_trigger
        AFTER INSERT OR UPDATE ON {table_schema}.{table_name}
        FOR EACH ROW EXECUTE FUNCTION {table_schema}.{table_name}_audit();
        """
    )


#################
# SQL CONSTANTS #
#################


CREATE_EXTENSIONS = """
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

SET_PGMETA_CONFIG = """
-- Set the pgmeta configuration for supa_audit
SET pgmeta.log = 'all';
SET pgmeta.log_relation = on;
SET pgmeta.log_line_prefix = '%m %u %d [%p]: ';
"""


CREATE_INSERT_RELATED_OBJECT_FUNCTION = """
CREATE OR REPLACE FUNCTION un0.insert_related_object(schema_name VARCHAR, table_name VARCHAR)
RETURNS VARCHAR(26)
LANGUAGE plpgsql
AS $$
DECLARE
    rel_obj_id VARCHAR(26);
    table_type_id INT;
BEGIN
    /*
    Function used to insert a record into the related_object table, when a record is inserted
    into a table that has a PK that is a FK to the related_object table.
    */
    SELECT id
        FROM un0.table_type
        WHERE schema = schema_name AND name = table_name
        INTO table_type_id;

    rel_obj_id := un0.generate_ulid(); 

    INSERT INTO un0.related_object (id, table_type_id)
    VALUES (rel_obj_id, table_type_id);

    RETURN rel_obj_id;
END;
$$;
"""

CREATE_SET_OWNER_AND_MODIFIED_FUNCTION = """
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

    SELECT reltuples AS estimate FROM PG_CLASS where relname = TG_TABLE_NAME INTO estimate;
    SELECT current_setting('user_var.id', true) into user_id;

    /*
    This should only happen when the very first user is created
    and therefore a user_id cannot be set in the session variables
    */
    IF user_id IS NULL THEN
        IF TG_TABLE_NAME = 'user' AND estimate < 1 THEN
            RETURN NEW;
        ELSE
            RAISE EXCEPTION 'user_id is NULL';
        END IF;
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

CREATE_VALIDATE_DELETE_FUNCTION = """
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


CREATE_PGULID: str = """
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
