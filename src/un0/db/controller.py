# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import sys
import io
import textwrap

from sqlalchemy import text, create_engine, Engine

from un0.db.controller_sql import (
    CREATE_ROLES,
    SET_PGMETA_CONFIG,
    CREATE_DATABASE,
    CREATE_SCHEMAS,
    CREATE_EXTENSIONS,
    CONFIGURE_AGE_EXTENSION,
    REVOKE_ACCESS,
    CONFIGURE_ROLE_SCHEMA_PRIVILEGES,
    SET_SEARCH_PATHS,
    CREATE_TOKEN_SECRET_TABLE,
    CREATE_TOKEN_SECRET,
    CREATE_INSERT_RELATED_OBJECT_FUNCTION,
    CREATE_SET_OWNER_AND_MODIFIED_FUNCTION,
    CREATE_VALIDATE_DELETE_FUNCTION,
    CREATE_PGULID,
    CONFIGURE_ROLE_TABLE_PRIVILEGES,
    CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER,
    CREATE_INSERT_TABLEPERMISSION_FUNCTION_AND_TRIGGER,
    CREATE_AUTHORIZE_USER_FUNCTION,
    CREATE_USER_TABLE_RLS_SELECT_POLICY,
    DROP_DATABASE,
    DROP_ROLES,
)
from un0.db.base import Base
import un0.auth.models as auth_models  # noqa
import un0.fltr.models as fltr_models  # noqa
import un0.msg.models as msg_models  # noqa
import un0.rltd.models as rltd_models  # noqa
import un0.rprt.models as rprt_models  # noqa
import un0.wkflw.models as wkflw_models  # noqa
from un0.schemas import TableSchema
from un0.config import settings as sttngs


class DBController:
    def engine(
        self,
        db_role: str,
        db_name: str = sttngs.DB_NAME,
        db_driver: str = sttngs.DB_DRIVER,
    ) -> Engine:
        return create_engine(f"{db_driver}://{db_role}@/{db_name}")

    def initial_creation_steps(self) -> None:
        """
        Create the database and its schema, owner, and API user.
        Intentially not using the async engine as we need to create the database and users.
        """

        eng = self.engine(db_role="postgres", db_name="postgres")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print(
                f"\nCreating the db: {sttngs.DB_NAME}, and roles, users, and app schema.\n"
            )
            # Create the roles
            print("Creating the roles\n")
            conn.execute(text(CREATE_ROLES))

            # Set the PGMeta config
            print("Set PGMeta config\n")
            conn.execute(text(SET_PGMETA_CONFIG))

            # Create the database
            print("Creating the database\n")
            conn.execute(text(CREATE_DATABASE))

            conn.close()
        eng.dispose()

    def create_schemas_extensions_and_tables(self) -> None:
        # Connect to the new database as the postgres user
        print("Connect to new db")
        print("Create schemas, fncts, and trgrs, and set privs and paths.\n")
        eng = self.engine(db_role="postgres")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print("Creating the schemas\n")
            conn.execute(text(CREATE_SCHEMAS))

            print("Creating the extensions\n")
            conn.execute(text(CREATE_EXTENSIONS))

            print("Configuring the Age extension\n")
            conn.execute(text(CONFIGURE_AGE_EXTENSION))

            print("Revoking public access to schemas\n")
            conn.execute(text(REVOKE_ACCESS))

            print("Configuring the privileges for the schemas\n")
            conn.execute(text(CONFIGURE_ROLE_SCHEMA_PRIVILEGES))

            print("Setting role search paths\n")
            conn.execute(text(SET_SEARCH_PATHS))

            conn.close()
        eng.dispose()

    def create_auth_functions_and_triggers(self) -> None:
        # Connect to the new database to create the Auth functions and triggers
        eng = self.engine(db_role=f"{sttngs.DB_NAME}_login")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))

            print("Creating the token_secret table\n")
            conn.execute(text(CREATE_TOKEN_SECRET_TABLE))
            conn.execute(text(CREATE_TOKEN_SECRET))

            print("Creating the insert related object function\n")
            conn.execute(text(CREATE_INSERT_RELATED_OBJECT_FUNCTION))

            print("Creating the set users before insert or update function\n")
            conn.execute(text(CREATE_SET_OWNER_AND_MODIFIED_FUNCTION))

            print("Creating the validate delete function\n")
            conn.execute(text(CREATE_VALIDATE_DELETE_FUNCTION))

            print("Creating the pgulid function\n")
            conn.execute(text(CREATE_PGULID))

            # Create the tables
            print("Creating the database tables\n")
            Base.metadata.create_all(bind=conn)

            print("Configuring the privileges for the tables\n")
            conn.execute(text(CONFIGURE_ROLE_TABLE_PRIVILEGES))

            print("Creating auth functions and triggers\n")
            conn.execute(text(CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER))
            conn.execute(text(CREATE_INSERT_TABLEPERMISSION_FUNCTION_AND_TRIGGER))
            conn.execute(text(CREATE_AUTHORIZE_USER_FUNCTION))

            conn.close()
        eng.dispose()

    def create_db(self) -> None:
        """
        Create the database, schemas, extensions, tables, and functions
        Configure the basic privileges for the tables
        Enable auditing for the tables
        Create the graph functions and triggers
        Turn on the RLS and create the policies

        Print statements are not displayed when called by pytest.
        """
        # Redirect the stdout stream to a StringIO object when running tests
        # to prevent the print statements from being displayed in the test output.
        if sttngs.ENV == "test":
            output_stream = io.StringIO()
            sys.stdout = output_stream

        self.initial_creation_steps()
        self.create_schemas_extensions_and_tables()
        self.create_auth_functions_and_triggers()

        # Connect to the new database to create the Graph functions and triggers
        eng = self.engine(db_role=f"{sttngs.DB_NAME}_login")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for table in Base.metadata.tables.values():
                table_schema = TableSchema(table=table)
                conn.execute(text(table_schema.configuration_sql()))

            conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))
            conn.execute(text(CREATE_USER_TABLE_RLS_SELECT_POLICY))
            conn.commit()
            conn.close()
        eng.dispose()

        print(f"Database created: {sttngs.DB_NAME}\n")
        print("Default Admin User created\n")

        # Reset the stdout stream
        if sttngs.ENV == "test":
            sys.stdout = sys.__stdout__

    def drop_db(self) -> None:
        """Delete the database and its asociated roles."""
        # Connect to the postgres database as the postgres user

        eng = self.engine(db_role="postgres", db_name="postgres")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print(
                f"\nDropping the db: {sttngs.DB_NAME} and all the roles for the application\n"
            )
            # Drop the Database
            conn.execute(text(DROP_DATABASE))
            # Drop the roles
            conn.execute(text(DROP_ROLES))
            conn.close()
            print(f"Database dropped: {sttngs.DB_NAME} \n")
        eng.dispose()

    def create_user_sql(
        self,
        email: str,
        handle: str,
        full_name: str,
        is_superuser: bool,
        is_tenant_admin: bool,
    ) -> str:
        return textwrap.dedent(
            f"""
            /*
            Creates the superuser for the application.
            */
            INSERT INTO un0.user (email, handle, full_name, is_superuser, is_tenant_admin)
            VALUES('{email}', '{handle}', '{full_name}', '{is_superuser}', '{is_tenant_admin}')
            RETURNING id;
            """
        )

    def create_user(
        self,
        email: str = sttngs.SUPERUSER_EMAIL,
        handle: str = sttngs.SUPERUSER_HANDLE,
        full_name: str = sttngs.SUPERUSER_FULL_NAME,
        is_superuser: bool = False,
        is_tenant_admin: bool = False,
    ) -> str:
        """ """
        eng = self.engine(db_role=f"{sttngs.DB_NAME}_login")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))
            conn.execute(text("ALTER TABLE un0.user DISABLE ROW LEVEL SECURITY;"))
            superuser = conn.execute(
                text(
                    self.create_user_sql(
                        email, handle, full_name, is_superuser, is_tenant_admin
                    )
                )
            )
            superuser_id = superuser.scalar()
            conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))
            conn.execute(text("ALTER TABLE un0.user ENABLE ROW LEVEL SECURITY;"))
            conn.execute(text("ALTER TABLE un0.user FORCE ROW LEVEL SECURITY;"))
            conn.close()
        eng.dispose()

        return superuser_id
