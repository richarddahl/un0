# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import sys
import io

from un0.cmd import drop_db
from sqlalchemy import text, create_engine
from un0.config import settings as sttngs

from un0.cmd.sql import (
    CREATE_ROLES,
    CREATE_DATABASE,
    CREATE_SCHEMAS,
    CONFIGURE_AGE_EXTENSION,
    REVOKE_ACCESS,
    CONFIGURE_ROLE_SCHEMA_PRIVILEGES,
    SET_SEARCH_PATHS,
    CONFIGURE_ROLE_TABLE_PRIVILEGES,
    CREATE_EXTENSIONS,
    SET_PGMETA_CONFIG,
    CREATE_INSERT_RELATED_OBJECT_FUNCTION,
    CREATE_SET_OWNER_AND_MODIFIED_FUNCTION,
    CREATE_VALIDATE_DELETE_FUNCTION,
    CREATE_PGULID,
)

from un0.auth.sql import (
    create_superuser,
    CREATE_AUTHORIZE_USER_FUNCTION,
    CREATE_TOKEN_SECRET,
    CREATE_TOKEN_SECRET_TABLE,
    CREATE_USER_TABLE_RLS_SELECT_POLICY,
    CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER,
    CREATE_INSERT_TABLEPERMISSION_FUNCTION_AND_TRIGGER,
)


from un0.db import Base
import un0.auth.models as auth_models  # noqa
import un0.fltr.models as fltr_models  # noqa
import un0.msg.models as msg_models  # noqa
import un0.rltd.models as rltd_models  # noqa
import un0.rprt.models as rprt_models  # noqa
import un0.wkflw.models as wkflw_models  # noqa
from un0.fltr.schemas import TableSchema
from un0.config import settings


def initial_creation_steps() -> None:
    """
    Create the database and its schema, owner, and API user.
    Intentially not using the async engine as we need to create the database and users.
    """

    eng = create_engine(f"{settings.DB_DRIVER}://postgres@/postgres")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print(
            f"\nCreating the db: {sttngs.DB_NAME}, and all the roles, users, and schema for the application.\n"
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


def create_schemas_extensions_and_tables() -> None:
    # Connect to the new database as the postgres user
    print("Connect to new db")
    print("Create schemas, fncts, and trgrs, and set privs and paths.\n")
    eng = create_engine(f"{settings.DB_DRIVER}://postgres@/{sttngs.DB_NAME}")
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

    eng = create_engine(
        f"{settings.DB_DRIVER}://{sttngs.DB_NAME}_login@/{sttngs.DB_NAME}"
    )
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

        conn.close()
    eng.dispose()


def create_auth_functions_and_triggers() -> None:
    # Connect to the new database to create the Auth functions and triggers
    eng = create_engine(
        f"{settings.DB_DRIVER}://{sttngs.DB_NAME}_login@/{sttngs.DB_NAME}"
    )
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))

        print("Creating auth functions and triggers\n")
        conn.execute(text(CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER))
        conn.execute(text(CREATE_INSERT_TABLEPERMISSION_FUNCTION_AND_TRIGGER))
        conn.execute(text(CREATE_AUTHORIZE_USER_FUNCTION))

    conn.close()
    eng.dispose()


def create() -> str:
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
    if settings.ENV == "test":
        output_stream = io.StringIO()
        sys.stdout = output_stream

    initial_creation_steps()
    create_schemas_extensions_and_tables()
    create_auth_functions_and_triggers()
    # Connect to the new database to create the Graph functions and triggers
    eng = create_engine(
        f"{settings.DB_DRIVER}://{sttngs.DB_NAME}_login@/{sttngs.DB_NAME}"
    )
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for table in Base.metadata.tables.values():
            table_schema = TableSchema(
                table=table,
            )
            conn.execute(text(table_schema.configure_table_sql()))

        conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))
        superuser = conn.execute(text(create_superuser()))
        superuser_id = superuser.scalar()

        conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))
        conn.execute(text(CREATE_USER_TABLE_RLS_SELECT_POLICY))
        conn.commit()
        conn.close()
    eng.dispose()

    print(f"Database created: {sttngs.DB_NAME}\n")
    print("Default Admin User created\n")

    # Reset the stdout stream
    if settings.ENV == "test":
        sys.stdout = sys.__stdout__

    return superuser_id


if __name__ == "__main__":
    drop_db.drop()
    create()
