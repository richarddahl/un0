# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import sys
import io

from un0.cmd import drop_db
from sqlalchemy import func, text, create_engine, Table
from sqlalchemy.engine import Connection
from un0.config import settings as sttngs

from un0.cmd.sql import (
    create_set_owner_and_modified_trigger,
    create_validate_delete_trigger,
    change_table_owner_and_set_privileges,
    create_table_type_record,
    enable_auditing,
    create_roles,
    create_database,
    create_schemas,
    configure_age_extension,
    revoke_access,
    set_search_paths,
    configure_role_schema_privileges,
    configure_role_table_privileges,
    create_history_table,
    create_history_table_trigger,
    CREATE_EXTENSIONS,
    SET_PGMETA_CONFIG,
    CREATE_INSERT_RELATED_OBJECT_FUNCTION,
    CREATE_SET_OWNER_AND_MODIFIED_FUNCTION,
    CREATE_VALIDATE_DELETE_FUNCTION,
    CREATE_PGULID,
)

from un0.auth.sql import (
    create_superuser,
    CREATE_TOKEN_SECRET,
    CREATE_TOKEN_SECRET_TABLE,
    create_authorize_user_function,
    CREATE_USER_TABLE_RLS_SELECT_POLICY,
    CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER,
    CREATE_INSERT_TABLE_PERMISSION_FUNCTION_AND_TRIGGER,
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


from un0.db import Base
import un0.auth.models as auth_models  # noqa
import un0.fltr.models as fltr_models  # noqa
import un0.msg.models as msg_models  # noqa
import un0.rltd.models as rltd_models  # noqa
import un0.rprt.models as rprt_models  # noqa
import un0.wkflw.models as wkflw_models  # noqa

from un0.config import settings


def initial_creation_steps(db_name: str = settings.DB_NAME) -> None:
    """
    Create the database and its schema, owner, and API user.
    Intentially not using the async engine as we need to create the database and users.
    """

    eng = create_engine(f"{settings.DB_DRIVER}://postgres@/postgres")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print(
            f"\nCreating the db: {db_name}, and all the roles, users, and schema for the application.\n"
        )
        # Create the roles
        print("Creating the roles\n")
        conn.execute(text(create_roles(db_name)))

        # Set the PGMeta config
        print("Set PGMeta config\n")
        conn.execute(text(SET_PGMETA_CONFIG))

        # Create the database
        print("Creating the database\n")
        conn.execute(text(create_database(db_name)))

        conn.close()
    eng.dispose()


def create_schemas_extensions_and_tables(db_name: str = settings.DB_NAME) -> None:
    # Connect to the new database as the postgres user
    print("Connect to new db")
    print("Create schemas, fncts, and trgrs, and set privs and paths.\n")
    eng = create_engine(f"{settings.DB_DRIVER}://postgres@/{db_name}")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("Creating the schemas\n")
        conn.execute(text(create_schemas(db_name)))

        print("Creating the extensions\n")
        conn.execute(text(CREATE_EXTENSIONS))

        print("Configuring the Age extension\n")
        conn.execute(text(configure_age_extension(db_name)))

        print("Revoking public access to schemas\n")
        conn.execute(text(revoke_access(db_name)))

        print("Configuring the privileges for the schemas\n")
        conn.execute(text(configure_role_schema_privileges(db_name)))

        print("Setting role search paths\n")
        conn.execute(text(set_search_paths(db_name)))

        conn.close()
    eng.dispose()

    eng = create_engine(f"{settings.DB_DRIVER}://{db_name}_login@/{db_name}")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"SET ROLE {db_name}_admin"))

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
        conn.execute(text(configure_role_table_privileges(db_name)))

        for schema_table_name in Base.metadata.tables.keys():
            table = Base.metadata.tables[schema_table_name]
            conn.execute(text(change_table_owner_and_set_privileges(table, db_name)))
        conn.close()
    eng.dispose()


def create_auth_functions_and_triggers(db_name: str = settings.DB_NAME) -> None:
    # Connect to the new database to create the Auth functions and triggers
    eng = create_engine(f"{settings.DB_DRIVER}://{db_name}_login@/{db_name}")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"SET ROLE {db_name}_admin"))

        print("Creating the can_insert_group function and check constraint\n")
        # conn.execute(text(create_insert_group_check_constraint))

        print("Creating auth functions and triggers\n")
        conn.execute(text(CREATE_INSERT_GROUP_FOR_TENANT_FUNCTION_AND_TRIGGER))
        conn.execute(text(CREATE_INSERT_TABLE_PERMISSION_FUNCTION_AND_TRIGGER))
        conn.execute(text(create_authorize_user_function(db_name=db_name)))
        # conn.execute(text(CREATE_GET_PERMISSIBLE_TABLE_PERMISSIONS_FUNCTION))

    conn.close()
    eng.dispose()


def create_graph_functions_and_triggers(
    conn: Connection, db_name: str = settings.DB_NAME
) -> None:
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
            conn.execute(text(create_vlabel(table_name)))
            print(
                f"Creating Insert Vertex Function and Trigger for Table: {schema_table_name}\n"
            )
            conn.execute(
                text(insert_vertex_functions_and_triggers(table, db_name=db_name))
            )
            conn.execute(
                text(update_vertex_functions_and_triggers(table, db_name=db_name))
            )
            conn.execute(
                text(delete_vertex_functions_and_triggers(table, db_name=db_name))
            )
            conn.execute(
                text(truncate_vertex_functions_and_triggers(table, db_name=db_name))
            )

            # Create the edge labels for the columns that are FKs.
            for column in table.columns:
                column_edge = column.info.get("edge", False)
                if column_edge is not False:
                    if column_edge not in edges:
                        edges.append(column_edge)
                        print(f"Creating Graph Edge Label for Column: {column.name}")
                        conn.execute(text(create_elabel(column_edge)))
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
        conn.execute(text(create_elabel(table_edge)))
        print(
            f"Creating Insert Edge with Properties Function for Association Table: {schema_table_name}"
        )
        conn.execute(text(insert_edge_w_props_functions_and_triggers(table)))
        conn.execute(text(delete_edge_w_props_functions_and_triggers(table)))
        conn.execute(text(truncate_edge_w_props_functions_and_triggers(table)))
    conn.commit()


def create_table_type_for_table(
    table: Table, conn: Connection, db_name: str = settings.DB_NAME
) -> None:
    table_info = getattr(table, "info", {})
    # Dont create any records in the database until the graph functions and triggers are created.
    # Create the table_type record for each table created.
    if table_info.get("edge", False) is False:
        # Do not create a table_type record for the edge (association) tables.
        print(f"Creating TableType record for {table.name}\n")
        conn.execute(text(f"SET ROLE {db_name}_writer"))
        conn.execute(text(create_table_type_record(table.schema, table.name)))
        conn.commit()


def enable_auditing_for_table(
    table: Table, schema_table_name, conn: Connection, db_name: str = settings.DB_NAME
) -> None:
    """Enables auditing for the table if the audit_type is not set to None in the tables info dictionary.

    If the audit_type is set to "history", then the history table and trigger are created for the table
        - A duplicate of the table is created as audit.[table_schema]_[table_name]
        - The trigger is created to insert a duplicate record into the history table after insert or update
        - A function is created to restore a record from the history table to the actual table

    If the audit_type is set to None, then no un0 auditing occurs.

    Otherwise, the audit trigger is created as a default:
        - all changes will be audited in the audit.record_version table, using supabase_audit.
    """
    audit_type = table.info.get("audit_type", True)
    # Create the audit trigger for all tables that have the info dictionary set to audited.
    if audit_type is True:
        conn.execute(text(f"SET ROLE {db_name}_admin"))
        print(f"Enabling auditing for {schema_table_name}\n")
        conn.execute(text(enable_auditing(schema_table_name)))
        conn.commit()
    elif audit_type == "history":
        conn.execute(text(f"SET ROLE {db_name}_admin"))
        print(f"Creating history table for {schema_table_name}\n")
        conn.execute(text(create_history_table(table.schema, table.name)))
        conn.execute(text(create_history_table_trigger(table.schema, table.name)))
        conn.commit()


# Create the get_permissable_groups function
# conn.execute(text(CREATE_GROUP_PERMISSION_FUNCTION))


def create(db_name: str = settings.DB_NAME) -> str:
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

    initial_creation_steps(db_name)
    create_schemas_extensions_and_tables(db_name)
    create_auth_functions_and_triggers(db_name)
    # Connect to the new database to create the Graph functions and triggers
    eng = create_engine(f"{settings.DB_DRIVER}://{db_name}_login@/{db_name}")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"SET ROLE {db_name}_admin"))
        create_graph_functions_and_triggers(conn, db_name)
        for schema_table_name in Base.metadata.tables.keys():
            table = Base.metadata.tables[schema_table_name]
            if "owner_id" in table.columns.keys():
                conn.execute(
                    text(create_set_owner_and_modified_trigger(schema_table_name))
                )
                conn.execute(text(create_validate_delete_trigger(schema_table_name)))
            enable_auditing_for_table(table, schema_table_name, conn, db_name)
            create_table_type_for_table(table, conn, db_name)
        superuser = conn.execute(text(create_superuser()))
        superuser_id = superuser.scalar()
        conn.execute(text(f"SET ROLE {db_name}_admin"))
        conn.execute(text(CREATE_USER_TABLE_RLS_SELECT_POLICY))
        conn.commit()
        conn.close()
    eng.dispose()

    print(f"Database created: {db_name}\n")
    print("Default Admin User created\n")

    # Reset the stdout stream
    if settings.ENV == "test":
        sys.stdout = sys.__stdout__

    return superuser_id


if __name__ == "__main__":
    drop_db.drop(db_name=sttngs.DB_NAME)
    create(db_name=sttngs.DB_NAME)
