# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import sys
import io
import textwrap

from sqlalchemy import text, create_engine, Engine

from un0.database.management.sql_emitters import (
    DropDatabaseEmitter,
    DropRolesEmitter,
    CreateRolesEmitter,
    CreateDatabaseEmitter,
    CreateSchemasAndExtensionsEmitter,
    PrivilegeAndSearchPathEmitter,
    PGULIDSQLEmitter,
    CreateTokenSecretEmitter,
    TablePrivilegeEmitter,
)
from un0.database.models import Model

from un0.database.base import metadata
from un0.config import settings


class DBManager:
    """
    A class used to manage database operations such as creating and dropping databases,
    creating users, roles, schemas, extensions, tables, and authentication functions and triggers.

    Methods
    -------
    create_db() -> None
        Creates the database, roles, schemas, extensions, tables, and authentication functions and triggers.

    drop_db() -> None
        Drops the database and all roles associated with the application.

    create_user_sql(email: str, handle: str, full_name: str, is_superuser: bool, is_tenant_admin: bool) -> str
        Generates the SQL statement to create a user in the database.

    create_user(email: str = settings.SUPERUSER_EMAIL, handle: str = settings.SUPERUSER_HANDLE, full_name: str = settings.SUPERUSER_FULL_NAME, is_superuser: bool = False, is_tenant_admin: bool = False) -> str
        Creates a user in the database and returns the user ID.

    engine(db_role: str, db_driver: str = settings.DB_DRIVER, db_password: str = settings.DB_USER_PW, db_host: str = settings.DB_HOST, db_name: str = settings.DB_NAME) -> Engine
        Creates and returns a SQLAlchemy engine for the specified database role and connection parameters.

    create_roles_and_db() -> None
        Creates the roles and the database.

    create_schemas_extensions_and_tables() -> None
        Creates the schemas, extensions, tables, and sets privileges and search paths.

    create_auth_functions_and_triggers() -> None
        Creates the authentication functions and triggers in the database.
    """

    def create_db(self) -> None:
        """
        Creates the database, including roles, schemas, extensions, tables,
        authentication functions, and triggers. If the environment is set to
        "test", redirects stdout to a StringIO object to suppress print statements
        during testing.

        Steps performed:
        1. Creates roles and database.
        2. Creates schemas, extensions, and tables.
        3. Creates authentication functions and triggers.
        4. Connects to the new database to create Graph functions and triggers.
        5. Prints a confirmation message upon successful creation.

        Resets stdout to its original state if it was redirected for testing.

        Raises:
            Any exceptions raised by the underlying database operations.
        """
        # Redirect the stdout stream to a StringIO object when running tests
        # to prevent the print statements from being displayed in the test output.
        # if settings.ENV == "test":
        #    output_stream = io.StringIO()
        #    sys.stdout = output_stream

        self.create_roles_and_db()
        self.create_schemas_extensions_and_tables()
        self.create_auth_functions_and_triggers()

        # Connect to the new database to create the Graph functions and triggers
        eng = self.engine(db_role=f"{settings.DB_NAME}_login")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for model in Model.registry.values():
                print(f"Creating the {model.__name__} table\n")
                # print(f"sql_emitters: {model.sql_emitters}")
                # print("")
                conn.execute(text(model().emit_sql()))
                conn.commit()
            conn.close()
        eng.dispose()

        print(f"Database created: {settings.DB_NAME}\n")

        # Reset the stdout stream
        if settings.ENV == "test":
            sys.stdout = sys.__stdout__

    def drop_db(self) -> None:
        """
        Drops the database and all associated roles.

        This method connects to the PostgreSQL database as the 'postgres' user and
        performs the following actions:
        1. Drops the specified database.
        2. Drops all roles associated with the application.

        If the environment is set to 'test', the stdout stream is redirected to a
        StringIO object to prevent print statements from being displayed in the test
        output.

        After the operations are completed, the stdout stream is reset to its original
        state if it was redirected.

        Returns:
            None
        """
        # Redirect the stdout stream to a StringIO object when running tests
        # to prevent the print statements from being displayed in the test output.
        if settings.ENV == "test":
            output_stream = io.StringIO()
            sys.stdout = output_stream

        # Connect to the postgres database as the postgres user
        eng = self.engine(db_role="postgres", db_name="postgres")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print(
                f"\nDropping the db: {settings.DB_NAME} and all the roles for the application\n"
            )
            # Drop the Database
            conn.execute(text(DropDatabaseEmitter().emit_sql()))
            print(f"Database dropped: {settings.DB_NAME} \n")
            conn.execute(text(DropRolesEmitter().emit_sql()))
            print(f"All Roles dropped for database: {settings.DB_NAME} \n")
            conn.close()
        eng.dispose()

        # Reset the stdout stream
        if settings.ENV == "test":
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
        Generates an SQL statement to create a new user in the database.

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
        email: str = settings.SUPERUSER_EMAIL,
        handle: str = settings.SUPERUSER_HANDLE,
        full_name: str = settings.SUPERUSER_FULL_NAME,
        is_superuser: bool = False,
        is_tenant_admin: bool = False,
    ) -> str:
        """
        Creates a new user in the database with the given details.

        Args:
            email (str): The email address of the user. Defaults to settings.SUPERUSER_EMAIL.
            handle (str): The handle/username of the user. Defaults to settings.SUPERUSER_HANDLE.
            full_name (str): The full name of the user. Defaults to settings.SUPERUSER_FULL_NAME.
            is_superuser (bool): Flag indicating if the user is a superuser. Defaults to False.
            is_tenant_admin (bool): Flag indicating if the user is a tenant admin. Defaults to False.

        Returns:
            str: The ID of the created superuser.
        """

        eng = self.engine(db_role=f"{settings.DB_NAME}_login")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text(f"SET ROLE {settings.DB_NAME}_admin"))
            conn.execute(text("ALTER TABLE un0.user DISABLE ROW LEVEL SECURITY;"))
            superuser = conn.execute(
                text(
                    self.create_user_sql(
                        email, handle, full_name, is_superuser, is_tenant_admin
                    )
                )
            )
            superuser_id = superuser.scalar()
            conn.execute(text(f"SET ROLE {settings.DB_NAME}_admin"))
            conn.execute(text("ALTER TABLE un0.user ENABLE ROW LEVEL SECURITY;"))
            conn.execute(text("ALTER TABLE un0.user FORCE ROW LEVEL SECURITY;"))
            conn.close()
        eng.dispose()

        return superuser_id

    def engine(
        self,
        db_role: str,
        db_driver: str = settings.DB_DRIVER,
        db_password: str = settings.DB_USER_PW,
        db_host: str = settings.DB_HOST,
        db_name: str = settings.DB_NAME,
    ) -> Engine:
        """
        Creates a SQLAlchemy engine instance.

        Args:
            db_role (str): The role of the database user.
            db_driver (str, optional): The database driver to use. Defaults to settings.DB_DRIVER.
            db_password (str, optional): The password for the database user. Defaults to settings.DB_USER_PW.
            db_host (str, optional): The host of the database. Defaults to settings.DB_HOST.
            db_name (str, optional): The name of the database. Defaults to settings.DB_NAME.

        Returns:
            Engine: A SQLAlchemy Engine instance.
        """
        return create_engine(
            f"{db_driver}://{db_role}:{db_password}@{db_host}/{db_name}"
        )

    def create_roles_and_db(self) -> None:
        """
        Creates roles and a database.

        This method establishes a connection to the PostgreSQL database using the provided
        engine configuration. It then executes SQL commands to create roles and a database
        as specified by the `CreateRolesEmitter` and `CreateDatabaseEmitter` classes.

        Steps performed:
        1. Connects to the PostgreSQL database with the role 'postgres'.
        2. Executes SQL to create roles.
        3. Executes SQL to create the database.
        4. Closes the connection and disposes of the engine.

        Note:
            The database connection is set to use the 'AUTOCOMMIT' isolation level.

        Raises:
            SQLAlchemyError: If there is an error executing the SQL commands.
        """
        eng = self.engine(
            db_role="postgres", db_password="postgreSQLR0ck%", db_name="postgres"
        )
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print(
                f"\nCreating the db: {settings.DB_NAME}, and roles, users, and app schema_name.\n"
            )
            print("Creating the roles and the database\n")
            conn.execute(text(CreateRolesEmitter().emit_sql()))
            conn.execute(text(CreateDatabaseEmitter().emit_sql()))
            conn.close()
        eng.dispose()

    def create_schemas_extensions_and_tables(self) -> None:
        """
        Creates schemas, extensions, functions, triggers, and sets privileges and paths in the database.

        This method connects to the new database as the postgres user and performs the following actions:
        1. Creates the necessary schemas and extensions.
        2. Configures the privileges for the schemas.
        3. Sets the search paths for the schemas.

        The method uses an engine with AUTOCOMMIT isolation level to execute the SQL commands.
        """
        # Connect to the new database as the postgres user
        print("Connect to new db")
        print("Create schemas, fncts, and trgrs, and set privs and paths.\n")
        eng = self.engine(db_role="postgres")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print("Creating the schemas and extensions\n")
            conn.execute(text(CreateSchemasAndExtensionsEmitter().emit_sql()))

            print("Configuring the privileges for the schemas and setting the paths\n")
            conn.execute(text(PrivilegeAndSearchPathEmitter().emit_sql()))

            conn.close()
        eng.dispose()

    def create_auth_functions_and_triggers(self) -> None:
        """
        Creates authentication functions and triggers in the database.

        This method performs the following actions:
        1. Connects to the database using a specific role.
        2. Creates the token_secret table, function, and trigger.
        3. Creates the pgulid function.
        4. Creates the necessary database tables.
        5. Sets the table privileges.

        The connection is established with AUTOCOMMIT isolation level to ensure
        that each command is executed immediately. After all operations are
        completed, the connection and engine are properly closed and disposed.

        Returns:
            None
        """
        # Connect to the new database to create the Auth functions and triggers
        eng = self.engine(db_role=f"{settings.DB_NAME}_login")
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            print("Creating the token_secret table, function, and trigger\n")
            conn.execute(text(CreateTokenSecretEmitter().emit_sql()))

            print("Creating the pgulid function\n")
            conn.execute(text(PGULIDSQLEmitter().emit_sql()))

            # Create the tables
            print("Creating the database tables\n")
            metadata.create_all(bind=conn)

            print("Setting the table privileges\n")
            conn.execute(text(TablePrivilegeEmitter().emit_sql()))
            conn.close()
        eng.dispose()
