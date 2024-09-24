# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import sys
import io

import sqlalchemy as sa

from un0.cmd.sql import (
    CREATE_ROLES,
    SET_PGMETA_CONFIG,
    CREATE_DATABASE,
    CREATE_SCHEMAS,
    REVOKE_ACCESS,
    CONFIGURE_BASIC_PRIVILEGES,
    SET_SEARCH_PATHS,
    CREATE_EXTENSIONS,
    CONFIGURING_AGE_EXTENSION,
    CREATE_PGULID,
    change_table_owner_and_set_privileges,
    create_table_type_record,
    enable_auditing,
)

from un0.grph.sql import (
    create_vlabel,
    create_elabel,
    insert_vertex_functions_and_triggers,
    update_vertex_functions_and_triggers,
    delete_vertex_functions_and_triggers,
    truncate_vertex_functions_and_triggers,
    insert_edge_w_props_functions_and_triggers,
    delete_edge_w_props_functions_and_triggers,
    truncate_edge_w_props_functions_and_triggers,
)

from un0.auth.sql import (
    CREATE_INSERT_GROUP_FOR_CUSTOMER_FUNCTION,
    CREATE_INSERT_GROUP_FOR_CUSTOMER_TRIGGER,
    CREATE_INSERT_TABLE_PERMISSION_FUNCTION,
    CREATE_INSERT_TABLE_PERMISSION_TRIGGER,
    CREATE_USER_TABLE_RLS_SELECT_POLICY,
    CREATE_VERIFY_JWT_AND_SET_VARS_FUNCTION,
    CREATE_LIST_SESSION_VARIABLES_FUNCTION,
    # CREATE_SET_USER_OWNER_FUNCTION_AND_TRIGGER,
    # CREATE_GET_PERMISSIBLE_TABLE_PERMISSIONS_FUNCTION,
    # CREATE_CAN_INSERT_GROUP_FUNCTION,
    # CREATE_INSERT_GROUP_CHECK_CONSTRAINT,
)

from un0.db import Base
import un0.auth.models as auth_models  # noqa
import un0.fltr.models as fltr_models  # noqa
import un0.msg.models as msg_models  # noqa
import un0.rltd.models as rltd_models  # noqa
import un0.rprt.models as rprt_models  # noqa
import un0.wkflw.models as wkflw_models  # noqa
from un0.config import settings


def initial_creation_steps() -> None:
    """
    Create the database and its schema, owner, and API user.
    Intentially not using the async engine as we need to create the database and users.
    """

    eng = sa.create_engine(f"{settings.DB_DRIVER}://postgres@/postgres")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print(
            f"\nCreating the db: {settings.DB_NAME}, and all the roles, users, and schema for the application.\n"
        )
        # Create the roles
        print("Creating the roles\n")
        conn.execute(sa.text(CREATE_ROLES))

        # Set the PGMeta config
        print("Set PGMeta config\n")
        conn.execute(sa.text(SET_PGMETA_CONFIG))

        # Create the database
        print("Creating the database\n")
        conn.execute(sa.text(CREATE_DATABASE))

        conn.close()
    eng.dispose()


def create_schemas_extensions_and_tables() -> None:
    # Connect to the new database as the postgres user
    print("Connect to new db")
    print("Create schemas, fncts, and trgrs, and set privs and paths.\n")
    eng = sa.create_engine(f"{settings.DB_DRIVER}://postgres@/{settings.DB_NAME}")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("Creating the schemas\n")
        conn.execute(sa.text(CREATE_SCHEMAS))

        print("Creating the extensions\n")
        conn.execute(sa.text(CREATE_EXTENSIONS))

        print("Configuring the Age extension\n")
        conn.execute(sa.text(CONFIGURING_AGE_EXTENSION))

        print("Creating the pgulid function\n")
        conn.execute(sa.text(CREATE_PGULID))

        print("Revoking public access to schemas\n")
        conn.execute(sa.text(REVOKE_ACCESS))

        print("Setting role search paths\n")
        conn.execute(sa.text(SET_SEARCH_PATHS))

        # Create the tables
        print("Creating the database tables\n")
        Base.metadata.create_all(eng)

        print("Configuring the privileges for the tables\n")
        conn.execute(sa.text(CONFIGURE_BASIC_PRIVILEGES))
        for schema_table_name in Base.metadata.tables.keys():
            table = Base.metadata.tables[schema_table_name]
            conn.execute(sa.text(change_table_owner_and_set_privileges(table)))
    eng.dispose()


def create_auth_functions_and_triggers() -> None:
    # Connect to the new database to create the Auth functions and triggers
    eng = sa.create_engine(
        f"{settings.DB_DRIVER}://{settings.DB_NAME}_login@/{settings.DB_NAME}"
    )
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(sa.text(f"SET ROLE {settings.DB_NAME}_admin;"))

        print("Creating the can_insert_group function and check constraint\n")
        # conn.execute(sa.text(CREATE_INSERT_GROUP_CHECK_CONSTRAINT))

        print("Creating auth functions and triggers\n")
        conn.execute(sa.text(CREATE_INSERT_GROUP_FOR_CUSTOMER_FUNCTION))
        conn.execute(sa.text(CREATE_INSERT_GROUP_FOR_CUSTOMER_TRIGGER))
        conn.execute(sa.text(CREATE_INSERT_TABLE_PERMISSION_FUNCTION))
        conn.execute(sa.text(CREATE_INSERT_TABLE_PERMISSION_TRIGGER))
        conn.execute(sa.text(CREATE_VERIFY_JWT_AND_SET_VARS_FUNCTION))
        conn.execute(sa.text(CREATE_LIST_SESSION_VARIABLES_FUNCTION))
        # conn.execute(sa.text(CREATE_GET_PERMISSIBLE_TABLE_PERMISSIONS_FUNCTION))

    conn.close()
    eng.dispose()


def create_graph_functions_and_triggers(conn: sa.Connection) -> None:
    vertices = []  # List of tables that are vertices, to ensure we only create them once
    edges = []  # List of tables or table columns that are edges, to ensure we only create them once
    for schema_table_name in Base.metadata.tables.keys():
        table = Base.metadata.tables[schema_table_name]
        table_name: str = schema_table_name.split(".")[1]
        table_info = getattr(table, "info", {})

        # The following code is used to create the graph functions and triggers for the tables.
        # Generally, the tables will have a vertex key in the table.info dictionary.
        # This is indicated by the tables info dictionary having a key of "vertex", and the value will be True.

        # TRYING TO CREATE VERTEXES FOR ALL TABLES
        # A Vertex is a node in a graph, and it is created from a table in the database.
        # An Edge is a relationship between two vertices, and it is created from a
        # column in a table that is a foreign key to another table.
        table_is_edge = table_info.get("edge", False)
        table_is_vertex = table_info.get("vertex", True)
        if not isinstance(table_is_edge, str) and table_is_vertex is True:
            # Create the vertex label for the table
            if table_name in vertices:
                continue
            print(f"\nCreating Vertices for {schema_table_name}\n")
            vertices.append(table_name)
            conn.execute(sa.text(create_vlabel(table_name)))
            print(
                f"Creating Insert Vertex Function and Trigger for Table: {schema_table_name}\n"
            )
            conn.execute(sa.text(insert_vertex_functions_and_triggers(table)))
            conn.execute(sa.text(update_vertex_functions_and_triggers(table)))
            conn.execute(sa.text(delete_vertex_functions_and_triggers(table)))
            conn.execute(sa.text(truncate_vertex_functions_and_triggers(table)))

            # Create the edge labels for the columns that are FKs.
            for column in table.columns:
                column_edge = column.info.get("edge", False)
                if column_edge is not False:
                    if column_edge not in edges:
                        edges.append(column_edge)
                        print(f"Creating Graph Edge Label for Column: {column.name}")
                        conn.execute(sa.text(create_elabel(column_edge)))
            continue
        # Association tables will not be created as vertices, but as edges.
        # The tables info dictionary will reflect this with a key of "edge", and the value will be the edge name.
        # The vertices identified by the FKs within the association table will be used as the start
        # and end points for the edge and the edge name will be used to create the edge label.
        table_edge = table.info.get("edge", False)
        if table_edge is False or table_edge in edges:
            continue
        edges.append(table_edge)
        print(
            f"Creating Graph Edge with Properties Label for Association Table: {schema_table_name}"
        )
        conn.execute(sa.text(create_elabel(table_edge)))
        print(
            f"Creating Insert Edge with Properties Function for Association Table: {schema_table_name}"
        )
        conn.execute(sa.text(insert_edge_w_props_functions_and_triggers(table)))
        conn.execute(sa.text(delete_edge_w_props_functions_and_triggers(table)))
        conn.execute(sa.text(truncate_edge_w_props_functions_and_triggers(table)))
    conn.commit()


def create_table_type_for_table(table: sa.Table, conn: sa.Connection) -> None:
    table_name = table.name
    table_schema = table.schema
    table_info = getattr(table, "info", {})
    # Dont create any records in the database until the graph functions and triggers are created.
    # Create the table_type record for each table created.
    if table_info.get("edge", False) is False:
        # Do not create a table_type record for the edge (association) tables.
        print(f"Creating TableType record for {table_name}\n")
        conn.execute(sa.text(create_table_type_record(table_schema, table_name)))
        conn.commit()


def enable_auditing_for_table(schema_table_name, conn: sa.Connection) -> None:
    # audited = table_info.get("audited", False)
    # Create the audit trigger for all tables that have the info dictionary set to audited.
    # if audited is True:
    print(f"Enabling auditing for {schema_table_name}\n")
    conn.execute(sa.text(enable_auditing(schema_table_name)))
    conn.commit()


# Create the get_permissable_groups function
# conn.execute(sa.text(CREATE_GROUP_PERMISSION_FUNCTION))


def create_database() -> None:
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
    eng = sa.create_engine(
        f"{settings.DB_DRIVER}://{settings.DB_NAME}_login@/{settings.DB_NAME}",
        echo=False,
    )
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(sa.text(f"SET ROLE {settings.DB_NAME}_admin;"))
        conn.execute(
            sa.text(
                f"SET search_path TO ag_catalog, graph, un0, audit, {settings.DB_NAME};"
            )
        )
        create_graph_functions_and_triggers(conn)
        for schema_table_name in Base.metadata.tables.keys():
            table = Base.metadata.tables[schema_table_name]
            enable_auditing_for_table(schema_table_name, conn)
            create_table_type_for_table(table, conn)
        conn.execute(
            sa.text(
                f"""
                INSERT INTO un0.user(email, handle, full_name, is_superuser)
                VALUES(
                    '{settings.SUPERUSER_EMAIL}',
                    '{settings.SUPERUSER_HANDLE}',
                    '{settings.SUPERUSER_FULL_NAME}',
                    true
                );
                """
            )
        )
        conn.execute(sa.text(CREATE_USER_TABLE_RLS_SELECT_POLICY))
        conn.commit()

    print(f"Database created: {settings.DB_NAME}\n")
    print("Default Admin User created\n")

    # Reset the stdout stream
    if settings.ENV == "test":
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    create_database()
