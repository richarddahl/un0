# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

from datetime import datetime, date, time
from decimal import Decimal

from pydantic import BaseModel, computed_field

from sqlalchemy import Table, Column

from un0.utilities import convert_snake_to_capital_word
from un0.fltr.enums import (  # type: ignore
    GraphType,
    Include,
    Match,
    Lookup,
    ColumnSecurity,
    related_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.config import settings as sttngs


class TableSchema(BaseModel):
    """ """

    table: Table
    # table_name: str <- computed_field
    # table_schema: str <- computed_field
    # schema_table_name: str <- computed_field
    # rls_policy: str <- computed_field
    # in_graph: bool <- computed_field
    # vertex: VertexSchema <- computed_field
    # edges: EdgeSchema <- computed_field
    # properties: PropertySchema <- computed_field

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @computed_field
    def table_schema(self) -> str:
        return self.table.schema

    @computed_field
    def table_name(self) -> str:
        return self.table.name

    @computed_field
    def schema_table_name(self) -> str:
        return f"{self.table_schema}.{self.table_name}"

    @computed_field
    def rls_policy(self) -> str:
        return self.table.info.get("rls_policy", "UserGroup")

    @computed_field
    def graph(self) -> bool:
        return self.table.info.get("in_graph", True)

    @computed_field
    def vertex(self) -> bool:
        if self.table.info.get("vertex", True) is not False:
            return VertexSchema(
                table=self.table, column=self.table.primary_key.columns[0]
            )

    @computed_field
    def edges(self) -> list["EdgeSchema"] | None:
        edges = []
        for fk in self.table.foreign_keys:
            for column in self.table.columns:
                if fk.parent.name == column.name:
                    continue
                for _fk in column.foreign_keys:
                    edges.append(
                        EdgeSchema(
                            table=self.table,
                            end_column=column,
                            start_vertex=VertexSchema(
                                table=self.table,
                                column=fk.parent,
                            ),
                            end_vertex=VertexSchema(
                                table=fk.column.table,
                                column=fk.column,
                            ),
                        )
                    )
        return edges

    @computed_field
    def properties(self) -> list["PropertySchema"] | None:
        props = []
        for column in self.table.columns:
            props.append(PropertySchema(table=self.table, column=column))
        return props

    # @computed_field
    # def filters(self) -> list[FilterSchema] | None:
    #    filters = []
    #    for column in self.table.columns:
    #        filters.append(FilterSchema(table=self.table, column=column))
    #    return filters

    # Functions to generate sql statements

    def configuration_sql(self) -> str:
        sql = textwrap.dedent(
            f"SET ROLE {sttngs.DB_NAME}_admin;"
            f"\n{self.change_table_owner_and_set_privileges()}"
            f"\n{self.create_tabletype_record()}"
        )

        if "owner_id" in self.table.columns:
            sql += f"\n{textwrap.dedent(self.create_set_owner_and_modified_trigger())}"
            sql += f"\n{textwrap.dedent(self.create_validate_delete_trigger())}"

        # Enables auditing for the table if the audit_type is not set to None in the tables info dictionary.
        # If the audit_type is set to "history", then the history table and trigger are created for the table
        #    - A duplicate of the table is created as audit.[table_schema]_[table_name]
        #    - The trigger is created to insert a duplicate record into the history table after insert or update
        #    - A function is created to restore a record from the history table to the actual table
        # If the audit_type is set to None, then no un0 auditing occurs.
        # Otherwise, the audit trigger is created as a default:
        #    - all changes will be audited in the audit.record_version table, using supabase_audit.
        audit_type = self.table.info.get("audit", "basic")
        if audit_type == "basic":
            sql += f"\n{textwrap.dedent(self.enable_auditing())}"
        elif audit_type == "history":
            sql += f"\n{textwrap.dedent(self.create_history_table())}"
            sql += f"\n{textwrap.dedent(self.create_history_table_trigger())}"

        # Create the vertex and edge triggers
        if self.vertex:
            sql += f"\n{textwrap.dedent(self.vertex.create_sql())}"
        else:
            for edge in self.edges:
                sql += f"\n{textwrap.dedent(edge.create_sql())}"

        # if self.table.info.get("rls_policy", None) is not None:
        #    sql += f"\n{textwrap.dedent(self.enable_rls())}"
        #
        return sql

    def create_tabletype_record(self):
        return textwrap.dedent(
            f"""
            -- Create the tabletype record
            INSERT INTO un0.tabletype (schema, name)
            VALUES ('{self.table_schema}', '{self.table_name}');
            """
        )

    def enable_rls(self):
        return textwrap.dedent(
            f"""
            -- Enable RLS for the table
            ALTER TABLE {self.schema_table_name} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {self.schema_table_name} FORCE ROW LEVEL SECURITY;
            """
        )

    def create_set_owner_and_modified_trigger(self):
        return textwrap.dedent(
            f"""
            CREATE TRIGGER set_owner_and_modified_trigger
            BEFORE INSERT OR UPDATE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_owner_and_modified();
            """
        )

    def create_history_table_triggercreate_set_owner_and_modified_trigger(self):
        return textwrap.dedent(
            f"""
            CREATE TRIGGER set_owner_and_modified_trigger
            BEFORE INSERT OR UPDATE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_owner_and_modified();
            """
        )

    def create_validate_delete_trigger(self):
        return textwrap.dedent(
            f"""
            CREATE TRIGGER validate_delete_trigger 
            BEFORE DELETE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.validate_delete();
            """
        )

    def change_table_owner_and_set_privileges(self):
        return textwrap.dedent(
            f"""
            ALTER TABLE {self.schema_table_name} OWNER TO {sttngs.DB_NAME}_admin;
            GRANT SELECT ON {self.schema_table_name} TO
                {sttngs.DB_NAME}_reader,
                {sttngs.DB_NAME}_writer;
            GRANT INSERT, UPDATE, DELETE ON {self.schema_table_name} TO
                {sttngs.DB_NAME}_writer;
            """
        )

    def enable_auditing(self):
        return textwrap.dedent(
            f"""
            -- Enable auditing for the table
            SELECT audit.enable_tracking('{self.schema_table_name}'::regclass);
            """
        )

    def create_history_table(self):
        return textwrap.dedent(
            f"""
            CREATE TABLE audit.{self.table_schema}_{self.table_name}
            AS (SELECT * FROM {self.table_schema}.{self.table_name})
            WITH NO DATA;

            ALTER TABLE audit.{self.table_schema}_{self.table_name}
            ADD COLUMN pk INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

            CREATE INDEX {self.table_schema}_{self.table_name}_pk_idx
            ON audit.{self.table_schema}_{self.table_name} (pk);

            CREATE INDEX {self.table_schema}_{self.table_name}_id_modified_at_idx
            ON audit.{self.table_schema}_{self.table_name} (id, modified_at);
            """
        )

    def create_history_table_trigger(self) -> str:
        return textwrap.dedent(
            f"""
            CREATE OR REPLACE FUNCTION {self.table_schema}.{self.table_name}_audit()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            SECURITY DEFINER
            AS $$
            BEGIN
                INSERT INTO audit.{self.table_schema}_{self.table_name}
                SELECT *
                FROM {self.table_schema}.{self.table_name}
                WHERE id = NEW.id;
                RETURN NEW;
            END;
            $$;

            CREATE OR REPLACE TRIGGER {self.table_name}_audit_trigger
            AFTER INSERT OR UPDATE ON {self.table_schema}.{self.table_name}
            FOR EACH ROW EXECUTE FUNCTION {self.table_schema}.{self.table_name}_audit();
            """
        )

    def create_sql_function(
        self,
        function_name: str,
        function_string: str,
        operation: str = "UPDATE",
        for_each: str = "ROW",
        include_trigger: bool = False,
    ) -> str:
        fnct_string = textwrap.dedent(
            f"CREATE OR REPLACE FUNCTION {self.schema_table_name}_{function_name}()\n"
            "RETURNS TRIGGER\n"
            "LANGUAGE plpgsql\n"
            "VOLATILE\n"
            "AS $BODY$\n"
            "BEGIN\n"
            f"  SET ROLE {sttngs.DB_NAME}_admin;\n"
            f"  {function_string}\n"
            "END;\n"
            "$BODY$;\n"
        )
        trggr_string = textwrap.dedent(
            f"CREATE OR REPLACE TRIGGER {self.table_name}_{function_name}_trigger\n"
            f"    AFTER {operation}\n"
            f"    ON {self.schema_table_name}\n"
            f"    FOR EACH {for_each}\n"
            f"    EXECUTE FUNCTION {self.schema_table_name}_{function_name}();\n"
        )
        sql_str = (
            f"{textwrap.dedent(fnct_string)}\n{textwrap.dedent(trggr_string)}"
            if include_trigger
            else fnct_string
        )
        return textwrap.dedent(sql_str)


class PropertySchema(TableSchema):
    column: Column

    # name: str <- computed_field
    # data_type: str <- computed_field
    # lookups: Lookup <- computed_field

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    def name(self) -> str:
        return self.column.name

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        return f"quote_nullable(NEW.{self.name})"

    @computed_field
    def lookups(self) -> Lookup:
        if self.column.type.python_type in [
            int,
            float,
            Decimal,
            datetime,
            date,
            time,
        ]:
            return numeric_lookups
        return string_lookups


class VertexSchema(TableSchema):
    column: Column
    # label: str <- computed_field
    # data_type: str <- computed_field
    # properties: list[PropertySchema] | None <- computed_field
    # edges: list[EdgeSchema] | None <- computed_field
    # lookups: list[Lookup] <- computed_field

    table: Table

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    def label(self) -> str:
        return convert_snake_to_capital_word(self.table.name)

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        return f"quote_nullable(NEW.{self.column.name}::{self.column.type})"

    @computed_field
    def properties(self) -> list["PropertySchema"] | None:
        props = []
        for column in self.table.columns:
            props.append(PropertySchema(table=self.table, column=column))
        return props

    @computed_field
    def edges(self) -> list["EdgeSchema"] | None:
        edges = []
        for fk in self.table.foreign_keys:
            edges.append(
                EdgeSchema(
                    table=self.table,
                    end_column=fk.parent,
                    start_vertex=self,
                    end_vertex=VertexSchema(
                        table=fk.column.table,
                        column=fk.parent,
                    ),
                )
            )
        return edges

    # Functions to generate sql statements
    def create_sql(self) -> str:
        sql = self.create_label_sql()
        sql += f"\n{self.create_insert_function_and_trigger_sql()}"
        sql += f"\n{self.create_update_function_and_trigger_sql()}"
        sql += f"\n{self.create_delete_function_and_trigger_sql()}"
        sql += f"\n{self.create_truncate_function_and_trigger_sql()}"
        return textwrap.dedent(sql)

    def create_label_sql(self):
        return textwrap.dedent(
            f"\n-- Create the vertex label and index\n"
            f"\nDO $$ \n"
            f"BEGIN\n"
            f"    IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_label\n"
            f"    WHERE name = '{self.label}') THEN\n"
            f"        PERFORM ag_catalog.create_vlabel('graph', '{self.label}');\n"
            f'        CREATE INDEX ON graph."{self.label}" (id);\n'
            f"    END IF;\n"
            f"END $$;\n"
        )

    def create_insert_function_and_trigger_sql(self) -> str:
        """Creates a new vertex record when a new relational table record is inserted"""
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_insert_function_and_trigger_sql() for edge in self.edges]
            )

        if self.properties:
            prop_key_str = ", ".join(f"{prop.name}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = textwrap.dedent(
            f"\n-- Create the insert vertex function and trigger\n"
            f"\nEXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$\n"
            f"    CREATE (v:{self.label} {{{prop_key_str}}})\n"
            f"$$) AS (a agtype);'{prop_val_str});\n"
            f"\n-- Create the edges for the vertex on insert\n"
            f"{edge_str}\n"
            f"RETURN NEW;\n"
        )
        return textwrap.dedent(
            self.create_sql_function(
                "insert_vertex",
                sql,
                operation="INSERT",
                include_trigger=True,
            )
        )

    def create_update_function_and_trigger_sql(self) -> str:
        """Updates an existing vertex record when its relational table record is updated"""
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_update_function_and_trigger_sql() for edge in self.edges]
            )
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.name} = %s" for prop in self.properties
            )
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.label} {{id: %s}})
                {prop_key_str}
            $$) AS (a agtype);', quote_nullable(NEW.id){prop_val_str});
            {edge_str}
            RETURN NEW;
            """
        )
        return textwrap.dedent(
            self.create_sql_function(
                "update_vertex",
                sql,
                include_trigger=True,
            )
        )

    def create_delete_function_and_trigger_sql(self) -> str:
        """Deleted an existing vertex record when its relational table record is deleted"""
        sql = textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.label} {{id: %s}})
                DETACH DELETE v
            $$) AS (a agtype);', quote_nullable(OLD.id));
            RETURN OLD;
            """
        )
        return textwrap.dedent(
            self.create_sql_function(
                "delete_vertex",
                sql,
                operation="DELETE",
                include_trigger=True,
            )
        )

    def create_truncate_function_and_trigger_sql(self) -> str:
        """Deletes all corresponding vertices for a relation table when the table is truncated"""
        sql = textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.label})
                DETACH DELETE v
            $$) AS (a agtype);');
            RETURN OLD;
            """
        )
        return textwrap.dedent(
            self.create_sql_function(
                "truncate_vertex",
                sql,
                operation="truncate",
                for_each="STATEMENT",
                include_trigger=True,
            )
        )


class EdgeSchema(TableSchema):
    # label: str <- computed_field
    # properties: list[PropertySchema] <- computed_field

    table: Table
    end_column: Column
    start_vertex: VertexSchema
    end_vertex: VertexSchema
    lookups: list[Lookup] = related_lookups
    in_vertex: bool = True

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    def label(self) -> str:
        return self.end_column.info.get("edge")

    @computed_field
    def properties(self) -> list["PropertySchema"]:
        """
        Retrieves a list of graph properties for the current table.
        """
        props = []
        if not self.in_vertex:
            for column in self.table.columns:
                if not column.foreign_keys:
                    props.append(PropertySchema(table=self.table, column=column))
        return props

    # Functions to generate sql statements

    def create_sql(self) -> str:
        sql = self.create_label_sql()
        sql += self.create_sql_function(
            "insert_edge",
            self.create_insert_function_and_trigger_sql(),
            operation="INSERT",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "update_edge",
            self.create_update_function_and_trigger_sql(),
            operation="UPDATE",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "delete_edge",
            self.create_delete_function_and_trigger_sql(),
            operation="DELETE",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "truncate_edge",
            self.create_truncate_function_and_trigger_sql(),
            operation="TRUNCATE",
            for_each="STATEMENT",
            include_trigger=True,
        )
        return textwrap.dedent(sql)

    def create_label_sql(self) -> str:
        return textwrap.dedent(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_label WHERE name = '{self.label}') THEN
                    PERFORM ag_catalog.create_elabel('graph', '{self.label}');
                    CREATE INDEX ON graph."{self.label}" (start_id, end_id);
                END IF;
            END $$;
            """
        )

    def create_insert_function_and_trigger_sql(self) -> str:
        """ """
        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = ", ".join(f"{prop.name}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                CREATE (v)-[e:{self.label} {{{prop_key_str}}}] ->(w)
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}{prop_val_str});
            """
        # if not self.in_vertex:
        #    sql += "\nRETURN NEW;"
        return textwrap.dedent(sql)

    def create_update_function_and_trigger_sql(self) -> str:
        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.name} = %s" for prop in self.properties
            )
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                MATCH (v)-[o:{self.label}] ->(w)
                DELETE o
                CREATE (v)-[e:{self.label}] ->(w)
                {prop_key_str}
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}{prop_val_str});
            """
        )

    def create_delete_function_and_trigger_sql(self) -> str:
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                MATCH (v)-[o:{self.label}] ->(w)
                DELETE o
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type});
            """
        )

    def create_truncate_function_and_trigger_sql(self) -> str:
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                MATCH (v)-[o:{self.label}] ->(w)
                DELETE o
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type});
            """
        )
