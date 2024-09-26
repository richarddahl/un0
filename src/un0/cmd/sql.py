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
import sqlalchemy as sa

from un0.config import settings


def set_role_login(db_name: str = settings.DB_NAME):
    return f"SET ROLE {db_name}_login;"


def set_role_reader(db_name: str = settings.DB_NAME):
    return f"SET ROLE {db_name}_reader;"


def set_role_writer(db_name: str = settings.DB_NAME):
    return f"SET ROLE {db_name}_writer;"


def set_role_admin(db_name: str = settings.DB_NAME):
    return f"SET ROLE {db_name}_admin;"


def drop_database(db_name: str = settings.DB_NAME):
    return f"""
        -- Drop the database if it exists
        DROP DATABASE IF EXISTS {db_name} WITH (FORCE);
    """


def drop_roles(db_name: str = settings.DB_NAME):
    return f"""
        -- Drop the roles if they exist
        DROP ROLE IF EXISTS {db_name}_writer;
        DROP ROLE IF EXISTS {db_name}_reader;
        DROP ROLE IF EXISTS {db_name}_admin;
        DROP ROLE IF EXISTS {db_name}_login;
        DROP ROLE IF EXISTS {db_name}_base_role;
    """


def create_roles(db_name: str = settings.DB_NAME):
    return f"""
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
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_admin') THEN
                CREATE ROLE {db_name}_admin INHERIT IN ROLE {db_name}_base_role;
            END IF;

            -- Create the authentication role
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{db_name}_login') THEN
                CREATE ROLE {db_name}_login NOINHERIT LOGIN PASSWORD '{settings.DB_USER_PW}' IN ROLE
                    {db_name}_base_role;
            END IF;

            -- Grant the reader, writer, and admin roles to the authentication role
            -- Allows the login role to SET ROLE to any of the other roles
            GRANT {db_name}_reader,  {db_name}_writer, {db_name}_admin TO
                {db_name}_login;
        END $$;
    """


SET_PGMETA_CONFIG = """
SET pgmeta.log = 'all';
SET pgmeta.log_relation = on;
SET pgmeta.log_line_prefix = '%m %u %d [%p]: ';
"""


def create_database(db_name: str = settings.DB_NAME):
    return f"""
        -- Create the database
        CREATE DATABASE {db_name} WITH OWNER = {db_name}_admin;
    """


def create_schemas(db_name: str = settings.DB_NAME):
    return f"""
        -- Create the un0 schemas
        CREATE SCHEMA IF NOT EXISTS un0 AUTHORIZATION {db_name}_admin;
        CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA} AUTHORIZATION {db_name}_admin;
    """


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


def configuring_age_extension(db_name: str = settings.DB_NAME):
    return f"""
        -- Configuring the age extension
        GRANT USAGE ON SCHEMA ag_catalog TO
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;
        ALTER SCHEMA ag_catalog OWNER TO {db_name}_admin;
        SELECT * FROM ag_catalog.create_graph('graph');
        ALTER TABLE graph._ag_label_edge OWNER TO {db_name}_admin;
        ALTER TABLE graph._ag_label_vertex OWNER TO {db_name}_admin;
        ALTER SEQUENCE graph._ag_label_edge_id_seq OWNER TO {db_name}_admin;
        ALTER SEQUENCE graph._ag_label_vertex_id_seq OWNER TO {db_name}_admin;
        ALTER SEQUENCE graph._label_id_seq OWNER TO {db_name}_admin;
    """


def revoke_acess(db_name: str = settings.DB_NAME):
    return f"""
        -- Explicitly revoke all privileges on all schemas and tables
        REVOKE ALL ON SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {settings.DB_SCHEMA} 
        FROM
            public,
            {db_name}_base_role,
            {db_name}_login,
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;

        REVOKE ALL ON ALL TABLES IN SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {settings.DB_SCHEMA} 
        FROM
            public,
            {db_name}_base_role,
            {db_name}_login,
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;

        REVOKE CONNECT ON DATABASE {db_name} FROM
            public,
            {db_name}_base_role,
            {db_name}_reader,
            {db_name}_writer,
            {db_name}_admin;
    """


def set_search_paths(db_name: str = settings.DB_NAME):
    return f"""
        -- Set the search paths for the roles
        ALTER ROLE
            {db_name}_base_role
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {db_name};

        ALTER ROLE
            {db_name}_login
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {db_name};

        ALTER ROLE
            {db_name}_admin
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {db_name};

        ALTER ROLE
            {db_name}_reader
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {db_name};

        ALTER ROLE
            {db_name}_writer 
        SET search_path TO
            ag_catalog,
            un0,
            audit,
            graph,
            {db_name};
    """


def configure_role_privileges(db_name: str = settings.DB_NAME):
    return f"""
        -- Grant ownership of the un0 schemas to the DB admin role
        ALTER SCHEMA audit OWNER TO {db_name}_admin;
        ALTER SCHEMA un0 OWNER TO {db_name}_admin;
        ALTER SCHEMA graph OWNER TO {db_name}_admin;
        ALTER SCHEMA {settings.DB_SCHEMA} OWNER TO {db_name}_admin;

        -- Grant connect privileges to the DB login role
        GRANT CONNECT ON DATABASE {db_name} TO {db_name}_login;

        -- Grant usage privileges for users to created schemas
        GRANT USAGE ON SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {settings.DB_SCHEMA}
        TO
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;

        GRANT CREATE ON SCHEMA
            un0,
            audit,
            graph,
            {settings.DB_SCHEMA}
        TO
            {db_name}_admin;

        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {settings.DB_SCHEMA}
        TO
            {db_name}_admin,
            {db_name}_reader,
            {db_name}_writer;

        GRANT SELECT ON ALL TABLES IN SCHEMA
            un0,
            audit,
            graph,
            ag_catalog,
            {settings.DB_SCHEMA}
        TO
            {db_name}_reader,
            {db_name}_writer;

        GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA
            un0,
            audit,
            graph,
            {settings.DB_SCHEMA} 
        TO
            {db_name}_writer;

        REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA
            un0,
            {settings.DB_SCHEMA} 
        FROM
            {db_name}_admin;

        GRANT ALL ON ALL TABLES IN SCHEMA
            audit,
            graph,
            ag_catalog
        TO
            {db_name}_admin;
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


def change_table_owner_and_set_privileges(
    table: sa.Table, db_name: str = settings.DB_NAME
):
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
