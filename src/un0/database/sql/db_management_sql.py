# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from un0.database.sql.sql_emitter import SQLEmitter
from un0.config import settings


#################
# SQL CONSTANTS #
#################
"""
    NOTE - The use of f strings to provide the schema_name name and database name DOES NOT 
    provide any protection against SQL injection. 
    
    You cannot paramaterize postgres DDL statements.
    The names are defined in the .env file or are derived from the mapped classes.
    They are not user input, and are only used to create or update the db during
    developement, testing, and deployment.

    DON'T ALLOW UNTRUSTED USERS TO EDIT THE .env FILEs!
    
"""


class DropDatabaseEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Drop the database if it exists
            DROP DATABASE IF EXISTS {settings.DB_NAME} WITH (FORCE);
            """
        )


class DropRolesEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Drop the roles if they exist
            DROP ROLE IF EXISTS {settings.DB_NAME}_admin;
            DROP ROLE IF EXISTS {settings.DB_NAME}_writer;
            DROP ROLE IF EXISTS {settings.DB_NAME}_reader;
            DROP ROLE IF EXISTS {settings.DB_NAME}_login;
            DROP ROLE IF EXISTS {settings.DB_NAME}_base_role;
            """
        )


class CreateRolesEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
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
                GRANT {settings.DB_NAME}_reader, {settings.DB_NAME}_writer, {settings.DB_NAME}_admin TO
                    {settings.DB_NAME}_login;
            END $$;
            """
        )


class CreateDatabaseEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Create the database
            CREATE DATABASE {settings.DB_NAME} WITH OWNER = {settings.DB_NAME}_admin;
            """
        )


class CreateSchemasAndExtensionsEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return "\n".join(
            [
                self.emit_create_schemas_sql(),
                self.emit_create_extensions_sql(),
            ]
        )

    def emit_create_schemas_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Create the un0 schemas
            CREATE SCHEMA IF NOT EXISTS un0 AUTHORIZATION {settings.DB_NAME}_admin;
            CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA} AUTHORIZATION {settings.DB_NAME}_admin;
            """
        )

    def emit_create_extensions_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Create the extensions
            SET search_path TO un0;

            -- Creating the btree_gist extension
            CREATE EXTENSION IF NOT EXISTS btree_gist;

            -- Creating the supa_audit extension
            CREATE EXTENSION IF NOT EXISTS supa_audit CASCADE;

            -- Set the pgmeta configuration for supa_audit
            SET pgmeta.log = 'all';
            SET pgmeta.log_relation = on;
            SET pgmeta.log_line_prefix = '%m %u %d [%p]: ';

            -- Creating the pgcrypto extension
            CREATE EXTENSION IF NOT EXISTS pgcrypto;

            -- Creating the pgjwt extension
            CREATE EXTENSION IF NOT EXISTS pgjwt;

            -- Creating the age extension
            CREATE EXTENSION IF NOT EXISTS age;

            -- Configuring the age extension
            GRANT USAGE ON SCHEMA ag_catalog TO
                {settings.DB_NAME}_admin,
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer;
            ALTER SCHEMA ag_catalog OWNER TO {settings.DB_NAME}_admin;
            SELECT * FROM ag_catalog.create_graph('graph');
            ALTER TABLE ag_catalog.ag_graph OWNER TO {settings.DB_NAME}_admin;
            ALTER TABLE ag_catalog.ag_label OWNER TO {settings.DB_NAME}_admin;
            ALTER TABLE graph._ag_label_edge OWNER TO {settings.DB_NAME}_admin;
            ALTER TABLE graph._ag_label_vertex OWNER TO {settings.DB_NAME}_admin;
            ALTER SEQUENCE graph._ag_label_edge_id_seq OWNER TO {settings.DB_NAME}_admin;
            ALTER SEQUENCE graph._ag_label_vertex_id_seq OWNER TO {settings.DB_NAME}_admin;
            ALTER SEQUENCE graph._label_id_seq OWNER TO {settings.DB_NAME}_admin;
            """
        )


class PrivilegeAndSearchPathEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return "\n".join(
            [
                self.emit_revoke_access_sql(),
                self.emit_set_search_paths_sql(),
                self.emit_grant_schema_privileges_sql(),
            ]
        )

    def emit_revoke_access_sql(self) -> str:
        return textwrap.dedent(
            f"""
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
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer,
                {settings.DB_NAME}_admin;

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
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer,
                {settings.DB_NAME}_admin;

            REVOKE CONNECT ON DATABASE {settings.DB_NAME} FROM
                public,
                {settings.DB_NAME}_base_role,
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer,
                {settings.DB_NAME}_admin;
            """
        )

    def emit_set_search_paths_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Set the search paths for the roles
            ALTER ROLE
                {settings.DB_NAME}_base_role
            SET search_path TO
                ag_catalog,
                un0,
                audit,
                graph,
                {settings.DB_SCHEMA};

            ALTER ROLE
                {settings.DB_NAME}_login
            SET search_path TO
                ag_catalog,
                un0,
                audit,
                graph,
                {settings.DB_SCHEMA};


            ALTER ROLE
                {settings.DB_NAME}_reader
            SET search_path TO
                ag_catalog,
                un0,
                audit,
                graph,
                {settings.DB_SCHEMA};

            ALTER ROLE
                {settings.DB_NAME}_writer 
            SET search_path TO
                ag_catalog,
                un0,
                audit,
                graph,
                {settings.DB_SCHEMA};

            ALTER ROLE
                {settings.DB_NAME}_admin
            SET search_path TO
                ag_catalog,
                un0,
                audit,
                graph,
                {settings.DB_SCHEMA};
            """
        )

    def emit_grant_schema_privileges_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Grant ownership of the un0 schemas to the DB admin role
            ALTER SCHEMA audit OWNER TO {settings.DB_NAME}_admin;
            ALTER SCHEMA un0 OWNER TO {settings.DB_NAME}_admin;
            ALTER SCHEMA graph OWNER TO {settings.DB_NAME}_admin;
            ALTER SCHEMA ag_catalog OWNER TO {settings.DB_NAME}_admin;

            ALTER SCHEMA {settings.DB_SCHEMA} OWNER TO {settings.DB_NAME}_admin;
            ALTER TABLE audit.record_version OWNER TO {settings.DB_NAME}_admin;

            -- Grant connect privileges to the DB login role
            GRANT CONNECT ON DATABASE {settings.DB_NAME} TO {settings.DB_NAME}_login;

            -- Grant usage privileges for users to created schemas
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

            GRANT {settings.DB_NAME}_admin TO {settings.DB_NAME}_login WITH INHERIT FALSE, SET TRUE;
            GRANT {settings.DB_NAME}_writer TO {settings.DB_NAME}_login WITH INHERIT FALSE, SET TRUE;
            GRANT {settings.DB_NAME}_reader TO {settings.DB_NAME}_login WITH INHERIT FALSE, SET TRUE;
            """
        )


class TablePrivilegeEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Grant table privileges to the roles
            SET ROLE {settings.DB_NAME}_admin;
            GRANT SELECT ON ALL TABLES IN SCHEMA
                un0,
                audit,
                graph,
                ag_catalog,
                {settings.DB_SCHEMA}
            TO
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer;

            GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, TRIGGER ON ALL TABLES IN SCHEMA
                un0,
                audit,
                graph,
                {settings.DB_SCHEMA} 
            TO
                {settings.DB_NAME}_writer,
                {settings.DB_NAME}_admin;

            REVOKE SELECT, INSERT, UPDATE (id) ON un0.user FROM 
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer;

            GRANT ALL ON ALL TABLES IN SCHEMA
                audit,
                graph,
                ag_catalog
            TO
                {settings.DB_NAME}_admin;
            """
        )


class PGULIDSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            """
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
        )


class CreateTokenSecretEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""

            /* creating the token_secret table in database: {settings.DB_NAME} */
            SET ROLE {settings.DB_NAME}_admin;
            CREATE TABLE un0.token_secret (
                token_secret TEXT PRIMARY KEY
            );

            CREATE OR REPLACE FUNCTION un0.set_token_secret()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            AS $$
            BEGIN
                /* 
                Delete the existing Token Secret
                Before returing the new token secret
                This ensures we only have one token secret at a time
                We only store this in the database as it is 
                more secure there than in the environment variables
                */
                DELETE FROM un0.token_secret;
                RETURN NEW;
            END;
            $$;

            CREATE TRIGGER set_token_secret_trigger
            BEFORE INSERT ON un0.token_secret
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_token_secret();
            """
        )


CREATE_INSERT_GROUP_CONSTRAINT = f"""
/* database: {settings.DB_NAME} */
ALTER TABLE un0.group ADD CONSTRAINT ck_can_insert_group
    CHECK (un0.can_insert_group(tenant_id) = true);
"""


CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER = f"""
/* database: {settings.DB_NAME} */
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
