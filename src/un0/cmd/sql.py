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


DROP_DATABASE = f"""
-- Drop the database if it exists
DROP DATABASE IF EXISTS {settings.DB_NAME} WITH (FORCE);
"""


DROP_ROLES = f"""
-- Drop the roles if they exist
DROP ROLE IF EXISTS {settings.DB_NAME}_writer;
DROP ROLE IF EXISTS {settings.DB_NAME}_reader;
DROP ROLE IF EXISTS {settings.DB_NAME}_admin;
DROP ROLE IF EXISTS {settings.DB_NAME}_login;
DROP ROLE IF EXISTS {settings.DB_NAME}_base_role;
"""


CREATE_ROLES = f"""
-- Create the base role with permissions that all other users will inherit
DO $$
BEGIN
    -- Create the base role with permissions that all other users will inherit
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{settings.DB_NAME}_base_role') THEN
        CREATE ROLE {settings.DB_NAME}_base_role NOINHERIT;
    END IF;

    -- Create the reader role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{settings.DB_NAME}_reader') THEN
        CREATE ROLE {settings.DB_NAME}_reader INHERIT IN ROLE {settings.DB_NAME}_base_role;
    END IF;

    -- Create the writer role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{settings.DB_NAME}_writer') THEN

        CREATE ROLE {settings.DB_NAME}_writer INHERIT IN ROLE {settings.DB_NAME}_base_role;
    END IF;

    -- Create the admin role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{settings.DB_NAME}_admin') THEN
        CREATE ROLE {settings.DB_NAME}_admin INHERIT IN ROLE {settings.DB_NAME}_base_role;
    END IF;

    -- Create the authentication role
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{settings.DB_NAME}_login') THEN
        CREATE ROLE {settings.DB_NAME}_login NOINHERIT LOGIN PASSWORD '{settings.DB_USER_PW}' IN ROLE
            {settings.DB_NAME}_base_role;
    END IF;

    -- Grant the reader, writer, and admin roles to the authentication role
    -- Allows the login role to SET ROLE to any of the other roles
    GRANT {settings.DB_NAME}_reader,  {settings.DB_NAME}_writer, {settings.DB_NAME}_admin TO
        {settings.DB_NAME}_login;
END $$;
"""

SET_PGMETA_CONFIG = """
SET pgmeta.log = 'all';
SET pgmeta.log_relation = on;
SET pgmeta.log_line_prefix = '%m %u %d [%p]: ';
"""

CREATE_DATABASE = f"""
-- Create the database
CREATE DATABASE {settings.DB_NAME} WITH OWNER = {settings.DB_NAME}_admin;
"""


CREATE_SCHEMAS = f"""
-- Create the un0 schemas
--CREATE SCHEMA IF NOT EXISTS audit AUTHORIZATION {settings.DB_NAME}_admin;
CREATE SCHEMA IF NOT EXISTS un0 AUTHORIZATION {settings.DB_NAME}_admin;
CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA} AUTHORIZATION {settings.DB_NAME}_admin;
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


CONFIGURING_AGE_EXTENSION = f"""
-- Configuring the age extension
--LOAD 'age';
GRANT USAGE ON SCHEMA ag_catalog TO
    {settings.DB_NAME}_admin,
    {settings.DB_NAME}_reader,
    {settings.DB_NAME}_writer;
ALTER SCHEMA ag_catalog OWNER TO {settings.DB_NAME}_admin;
SELECT * FROM ag_catalog.create_graph('graph');
ALTER TABLE graph._ag_label_edge OWNER TO {settings.DB_NAME}_admin;
ALTER TABLE graph._ag_label_vertex OWNER TO {settings.DB_NAME}_admin;
ALTER SEQUENCE graph._ag_label_edge_id_seq OWNER TO {settings.DB_NAME}_admin;
ALTER SEQUENCE graph._ag_label_vertex_id_seq OWNER TO {settings.DB_NAME}_admin;
ALTER SEQUENCE graph._label_id_seq OWNER TO {settings.DB_NAME}_admin;
"""


REVOKE_ACCESS_FROM_PUBLIC = f"""
-- Explicitly revoke all privileges on all schemas and tables
REVOKE ALL ON SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {settings.DB_SCHEMA} 
FROM
    public,
    {settings.DB_NAME}_base_role,
    {settings.DB_NAME}_login,
    {settings.DB_NAME}_admin,
    {settings.DB_NAME}_reader,
    {settings.DB_NAME}_writer;

REVOKE ALL ON ALL TABLES IN SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {settings.DB_SCHEMA} 
FROM
    public,
    {settings.DB_NAME}_base_role,
    {settings.DB_NAME}_login,
    {settings.DB_NAME}_admin,
    {settings.DB_NAME}_reader,
    {settings.DB_NAME}_writer;
"""


SET_SEARCH_PATHS = f"""
ALTER ROLE
    {settings.DB_NAME}_base_role
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {settings.DB_NAME};
ALTER ROLE
    {settings.DB_NAME}_login
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {settings.DB_NAME};
ALTER ROLE
    {settings.DB_NAME}_admin
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {settings.DB_NAME};
ALTER ROLE
    {settings.DB_NAME}_reader
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {settings.DB_NAME};
ALTER ROLE
    {settings.DB_NAME}_writer 
SET search_path TO
    ag_catalog,
    un0,
    audit,
    graph,
    {settings.DB_NAME};

"""


CONFIGURE_BASIC_PRIVILEGES = f"""
-- Grant ownership of the un0 schemas to the application admin
ALTER SCHEMA audit OWNER TO {settings.DB_NAME}_admin;
ALTER SCHEMA un0 OWNER TO {settings.DB_NAME}_admin;
ALTER SCHEMA graph OWNER TO {settings.DB_NAME}_admin;
ALTER SCHEMA {settings.DB_SCHEMA} OWNER TO {settings.DB_NAME}_admin;

REVOKE CONNECT ON DATABASE {settings.DB_NAME} FROM
    public,
    {settings.DB_NAME}_base_role,
    {settings.DB_NAME}_reader,
    {settings.DB_NAME}_writer,
    {settings.DB_NAME}_admin;

-- Grant connect privileges to the application authenticator
GRANT CONNECT ON DATABASE {settings.DB_NAME} TO {settings.DB_NAME}_login;

-- Grant usage privileges for users to created schemas
-- authenticator needs usage as it is used by the inspector in testing
GRANT USAGE ON SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {settings.DB_SCHEMA}
TO
    {settings.DB_NAME}_login,
    {settings.DB_NAME}_admin,
    {settings.DB_NAME}_reader,
    {settings.DB_NAME}_writer;

GRANT CREATE ON SCHEMA
    un0,
    audit,
    graph,
    {settings.DB_SCHEMA}
TO
    {settings.DB_NAME}_admin;

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {settings.DB_SCHEMA}
TO
    {settings.DB_NAME}_login,
    {settings.DB_NAME}_admin,
    {settings.DB_NAME}_reader,
    {settings.DB_NAME}_writer;

GRANT SELECT ON ALL TABLES IN SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {settings.DB_SCHEMA}
TO
    {settings.DB_NAME}_reader,
    {settings.DB_NAME}_writer;


GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA
    un0,
    audit,
    graph,
    {settings.DB_SCHEMA} 
TO
    {settings.DB_NAME}_writer;

GRANT ALL ON ALL TABLES IN SCHEMA
    un0,
    audit,
    graph,
    ag_catalog,
    {settings.DB_SCHEMA} 
TO
    {settings.DB_NAME}_admin;
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


def change_table_owner_and_set_privileges(table: sa.Table):
    return f"""
    SET ROLE postgres;
    ALTER TABLE {table.schema}.{table.name} OWNER TO {settings.DB_NAME}_admin;
    SET ROLE {settings.DB_NAME}_admin;
    GRANT SELECT, INSERT, UPDATE, DELETE ON {table.schema}.{table.name} TO
        {settings.DB_NAME}_admin, {settings.DB_NAME}_writer;
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
