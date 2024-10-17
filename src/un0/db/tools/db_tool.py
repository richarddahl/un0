# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import sys
import io
import textwrap

from sqlalchemy import text, create_engine, Engine

from un0.db.tools.db_tool_sql import (
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
import un0.auth.tables as auth_models  # noqa
import un0.fltr.tables as fltr_models  # noqa
import un0.msg.tables as msg_models  # noqa
import un0.rltd.tables as rltd_models  # noqa
import un0.rprt.tables as rprt_models  # noqa
import un0.wkflw.tables as wkflw_models  # noqa
from un0.config import settings as sttngs
from un0.db.tools.table_tools import TableTool


class DBTool:
    def engine(
        self,
        db_role: str,
        db_name: str = sttngs.DB_NAME,
        db_driver: str = sttngs.DB_DRIVER,
    ) -> Engine:
        return create_engine(f"{db_driver}://{db_role}@/{db_name}")

    def create_roles_and_db(self) -> None:
        """
        Perform initial creation steps for the database.

        This method creates the database, its schema, owner, and API user. It intentionally
        does not use the async engine because the database and users need to be created
        synchronously.

        Steps performed:
        1. Connect to the database using the 'postgres' role and database.
        2. Create the necessary roles.
        3. Set the PGMeta configuration.
        4. Create the database.

        Note:
        - The connection is established with 'AUTOCOMMIT' isolation level to ensure
          the commands are executed immediately.
        - The connection is closed and the engine is disposed of after the operations
          are completed.
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
        """Create the schemas, extensions, and tables in the database.

        This method performs the following steps:
        1. Connects to the new database as the postgres user.
        2. Creates the necessary schemas.
        3. Creates the required extensions.
        4. Configures the Age extension.
        5. Revokes public access to schemas.
        6. Configures the privileges for the schemas.
        7. Sets the role search paths.

        The method uses an engine with AUTOCOMMIT isolation level to execute
        the SQL commands for each step.

        Returns:
            None
        """
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
        """Create the authentication functions and triggers in the database.

        This method performs the following steps:
        1. Connects to the database using a specific role.
        2. Creates the `token_secret` table and related functions.
        3. Creates various functions for handling inserts, updates, and deletions.
        4. Creates a function for generating unique identifiers (pgulid).
        5. Creates all database tables defined in the metadata.
        6. Configures role-based privileges for the tables.
        7. Creates authentication-related functions and triggers.

        The method ensures that all necessary database structures and functions
        are in place for handling authentication and authorization.
        """
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
        Create the database, schemas, extensions, tables, and functions.

        This method performs the following steps:
        - Creates the database, schemas, extensions, tables, and functions.
        - Configures the basic privileges for the tables.
        - Enables auditing for the tables.
        - Creates the graph functions and triggers.
        - Turns on the Row-Level Security (RLS) and creates the policies.

        Note:
        - Print statements are not displayed when called by pytest.
        - When running tests, the stdout stream is redirected to a StringIO object to prevent print statements from being displayed in the test output.

        Steps:
        1. Perform initial creation steps.
        2. Create schemas, extensions, and tables.
        3. Create authentication functions and triggers.
        4. Connect to the new database to create the graph functions and triggers.
        5. Configure the database with the necessary roles and policies.
        6. Print confirmation messages for database creation and default admin user creation.
        7. Reset the stdout stream if it was redirected during testing.

        Returns:
        None
        """
        # Redirect the stdout stream to a StringIO object when running tests
        # to prevent the print statements from being displayed in the test output.
        if sttngs.ENV == "test":
            output_stream = io.StringIO()
            sys.stdout = output_stream

        self.create_roles_and_db()
        self.create_schemas_extensions_and_tables()
        self.create_auth_functions_and_triggers()

        # Connect to the new database to create the Graph functions and triggers
        eng = self.engine(db_role=f"{sttngs.DB_NAME}_login")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for table in Base.metadata.tables.values():
                table_schema = TableTool(table=table)
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
        """
        Delete the database and its associated roles.

        This method connects to the PostgreSQL database as the 'postgres' user and performs the following actions:
        1. Drops the specified database.
        2. Drops all roles associated with the application.

        During testing, the stdout stream is redirected to a StringIO object to prevent print statements from being displayed in the test output.

        Returns:
            None
        """

        # Redirect the stdout stream to a StringIO object when running tests
        # to prevent the print statements from being displayed in the test output.
        if sttngs.ENV == "test":
            output_stream = io.StringIO()
            sys.stdout = output_stream

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

        # Reset the stdout stream
        if sttngs.ENV == "test":
            sys.stdout = sys.__stdout__

    def create_user_sql(
        self,
        email: str,
        handle: str,
        full_name: str,
        is_superuser: bool,
        is_tenant_admin: bool,
    ) -> str:
        """
        Generates a SQL statement to create a new user in the database.

        Args:
            email (str): The email address of the user.
            handle (str): The handle or username of the user.
            full_name (str): The full name of the user.
            is_superuser (bool): A flag indicating if the user is a superuser.
            is_tenant_admin (bool): A flag indicating if the user is a tenant admin.

        Returns:
            str: The SQL statement to insert a new user into the database.
        """
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
        """
        Creates a new user in the database with the specified attributes.

        Args:
            email (str): The email address of the user. Defaults to the superuser email from settings.
            handle (str): The handle/username of the user. Defaults to the superuser handle from settings.
            full_name (str): The full name of the user. Defaults to the superuser full name from settings.
            is_superuser (bool): Flag indicating if the user is a superuser. Defaults to False.
            is_tenant_admin (bool): Flag indicating if the user is a tenant admin. Defaults to False.

        Returns:
            str: The ID of the created user.
        """
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
