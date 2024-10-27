# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

import datetime

from enum import Enum
from decimal import Decimal
from typing import Annotated, Optional, ClassVar, Type, Any, Callable

from sqlalchemy import (
    MetaData,
    text,
    TextClause,
    func,
    ForeignKey,
    Column,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    registry,
    declared_attr,
    mapped_column,
)
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.postgresql import (
    BIGINT,
    TIMESTAMP,
    DATE,
    TIME,
    VARCHAR,
    BOOLEAN,
    ENUM,
    NUMERIC,
    ARRAY,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
    model_validator,
)

from un0.db.management.db_manager_sql import CREATE_VALIDATE_DELETE_FUNCTION
from un0.config import settings as sttngs

# configures the naming convention for the database implicit constraints and indexes
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

# Creates the metadata object, used to define the database tables
meta_data = MetaData(
    naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION,
    schema=sttngs.DB_NAME,
)

str_26 = Annotated[VARCHAR, 26]
str_64 = Annotated[VARCHAR, 64]
str_128 = Annotated[VARCHAR, 128]
str_255 = Annotated[VARCHAR, 255]
decimal = Annotated[Decimal, 19]


class Base(AsyncAttrs, DeclarativeBase):
    registry = registry(
        type_annotation_map=(
            {
                int: BIGINT,
                datetime.datetime: TIMESTAMP(timezone=True),
                datetime.date: DATE,
                datetime.time: TIME,
                str: VARCHAR,
                Enum: ENUM,
                bool: BOOLEAN,
                list: ARRAY,
                str_26: VARCHAR(26),
                str_64: VARCHAR(64),
                str_128: VARCHAR(128),
                str_255: VARCHAR(255),
                decimal: NUMERIC,
            }
        )
    )
    metadata = meta_data


class AuditEnum(Enum):
    DEFAULT = "default"
    NONE = "none"
    HISTORY = "history"


class DBObjectBase(BaseModel):
    doc: Optional[str] = ""
    info: Optional[dict[str, str]] = {}
    comment: Optional[str] = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DBTableBase(DBObjectBase):
    # table: Base <- computed_column
    db_schema: str = "un0"

    @computed_field
    def table(self) -> Base:
        table = type(
            self.name,
            (Base,),
            {
                "__tablename__": self.name.lower(),
                "__table_args__": {
                    "schema": self.db_schema.value,
                    "comment": self.comment,
                },
            },
        )
        for field_name, field in self.model_fields.items():
            setattr(table, field_name, field.column)


class ModelBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Model(ModelBase):
    # db_table: ClassVar[Type[Base]] <- computed_column

    db_schema_name: ClassVar[str]
    db_table_name: ClassVar[str]

    verbose_name: ClassVar[str]
    verbose_name_plural: ClassVar[str]

    unique_together: ClassVar[list[str]] = []
    indexes: ClassVar[list[Index]] = []
    unique_constraints: ClassVar[list[UniqueConstraint]] = []
    check_constraints: ClassVar[list[CheckConstraint]] = []

    auditing: ClassVar[AuditEnum] = AuditEnum.DEFAULT

    include_in_graph: ClassVar[bool] = True
    vertex: ClassVar[str | bool] = True

    rls_policy: ClassVar[str | bool] = "default"
    force_rls: ClassVar[bool] = True

    def emit_sql(self) -> str:
        sql = ""
        for cls in type(self).__mro__:
            if cls is Model:
                sql += f"{self.emit_change_table_owner_and_set_privileges_sql()}\n"
                sql += f"{self.emit_create_tabletype_record_sql()}\n"
                if self.rls_policy:
                    sql += f"{self.emit_enable_rls_sql()}\n"
                if self.force_rls:
                    sql += f"{self.emit_force_rls_sql()}\n"
                if self.auditing == AuditEnum.HISTORY:
                    sql += f"{self.emit_create_history_table_sql()}\n"
                    sql += f"{self.emit_create_history_table_trigger_sql()}\n"
                elif self.auditing == AuditEnum.DEFAULT:
                    sql += f"{self.emit_enable_auditing_sql()}\n"
            elif hasattr(cls, "emit_sql"):
                sql += f"{cls.emit_sql(self)}\n"
        return sql

    def emit_sql_old(self) -> str:
        sql = ""
        for cls in type(self).__mro__:
            if cls is Model:
                sql += f"{self.emit_change_table_owner_and_set_privileges_sql()}\n"
                sql += f"{self.emit_create_tabletype_record_sql()}\n"
                if self.rls_policy:
                    sql += f"{self.emit_enable_rls_sql()}\n"
                if self.force_rls:
                    sql += f"{self.emit_force_rls_sql()}\n"
                if self.auditing == AuditEnum.HISTORY:
                    sql += f"{self.emit_create_history_table_sql()}\n"
                    sql += f"{self.emit_create_history_table_trigger_sql()}\n"
                elif self.auditing == AuditEnum.DEFAULT:
                    sql += f"{self.emit_enable_auditing_sql()}\n"
            elif hasattr(cls, "emit_sql"):
                sql += f"{cls.emit_sql(self)}\n"
        return sql

    def emit_change_table_owner_and_set_privileges_sql(self) -> str:
        """
        Generates a SQL command to change the owner of a table and set privileges.

        The generated SQL command will:
        - Change the owner of the table to the admin user of the database.
        - Grant SELECT privileges to the reader and writer roles.
        - Grant INSERT, UPDATE, and DELETE privileges to the writer role.

        Returns:
            str: A formatted SQL command string.
        """
        return textwrap.dedent(
            f"""
            ALTER TABLE {self.db_schema_name}.{self.db_table_name} OWNER TO {sttngs.DB_NAME}_admin;
            GRANT SELECT ON {self.db_schema_name}.{self.db_table_name} TO
                {sttngs.DB_NAME}_reader,
                {sttngs.DB_NAME}_writer;
            GRANT INSERT, UPDATE, DELETE ON {self.db_schema_name}.{self.db_table_name} TO
                {sttngs.DB_NAME}_writer;
            """
        )

    def emit_create_tabletype_record_sql(self) -> str:
        """
        Emits the SQL statement to insert a record into the `un0.tabletype` table.

        This method creates a SQL INSERT statement that adds a new record to the
        `un0.tabletype` table with the schema and name provided by the instance's
        `table_schema` and `table_name` attributes.

        Returns:
            str: A formatted SQL INSERT statement as a string.
        """
        return textwrap.dedent(
            f"""
            -- Create the tabletype record
            INSERT INTO un0.tabletype (schema, name)
            VALUES ('{self.db_schema_name}', '{self.db_table_name}');
            """
        )

    def emit_enable_rls_sql(self) -> str:
        """
        Emits the SQL statements to enable Row Level Security (RLS)
        on a specified table.

        Returns:
            str: A string containing the SQL statements to enable RLS for the table.
        """
        return textwrap.dedent(
            f"""
            -- Enable RLS for the table
            ALTER TABLE {self.db_schema_name}.{self.db_table_name} ENABLE ROW LEVEL SECURITY;
            """
        )

    def emit_force_rls_sql(self) -> str:
        """
        Emits the SQL statements to force Row Level Security (RLS)
        on a specified table even for table owners and db superusers.

        Returns:
            str: A string containing the SQL statements to force RLS for the table.
        """
        return textwrap.dedent(
            f"""
            -- FORCE RLS for the table
            ALTER TABLE {self.db_schema_name}.{self.db_table_name} FORCE ROW LEVEL SECURITY;
            """
        )

    def emit_enable_auditing_sql(self) -> str:
        """
        Generates a SQL query to enable auditing for the specified table.

        Returns:
            str: A SQL query string that enables auditing for the table.
        """
        if self.auditing == AuditEnum.NONE:
            return ""
        if self.auditing == AuditEnum.HISTORY:
            return f"{self.emit_create_history_table_sql()}\n{self.emit_create_history_table_trigger_sql()}"
        return textwrap.dedent(
            f"""
            -- Enable auditing for the table
            SELECT audit.enable_tracking('{self.db_schema_name}.{self.db_table_name}'::regclass);
            """
        )

    def emit_create_history_table_sql(self) -> str:
        """
        Creates a SQL statement to generate a history table for auditing purposes.

        The history table will be created in the 'audit' schema and will have the same structure
        as the original table, but without any data. Additionally, it will have an auto-incrementing
        primary key column and two indexes: one on the primary key and another on the combination
        of 'id' and 'modified_at' columns.

        Returns:
            str: A SQL statement to create the history table.
        """
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

    def emit_create_history_table_trigger_sql(self) -> str:
        """
        Generates a SQL trigger function and trigger for auditing changes to a table.

        This method creates a PostgreSQL function and trigger that logs changes to a specified table
        into an audit table. The function and trigger are created within the same schema as the target table.

        Returns:
            str: A string containing the SQL statements to create the audit function and trigger.
        """
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


class FieldBase(DBObjectBase):
    # table: Table <- computed_column
    # column: mapped_column <- computed_column

    value: ClassVar[Any | None] = None

    name: str
    type: Any

    required: bool = False
    constraint: str | None = None
    default: Any = None
    server_default: Any = None
    server_onupdate: Any = None
    server_ondelete: Any = None
    foreign_key: ForeignKey | None = None
    related_name: str | None = None
    many_to_many: list["FieldBase"] | None = None
    index: bool = False
    autoincrement: bool = False
    nullable: bool = False
    primary_key: bool = False
    unique: bool = False
    include_in_masks: list[str] = ["insert", "update", "select", "list"]
    exclude_in_masks: list[str] = []
    exclude_from_graph: bool = False
    forward_edge_name: str | None = None
    reverse_edge_name: str | None = None
    editable: bool = True

    @computed_field
    def column(self) -> Column:
        return mapped_column(
            name=self.name,
            type_=self.type,
            nullable=self.nullable,
            primary_key=self.primary_key,
            unique=self.unique,
            autoincrement=self.autoincrement,
            server_default=self.server_default,
            server_onupdate=self.server_onupdate,
            server_ondelete=self.server_ondelete,
            comment=self.comment,
        )


class RelatedObjectMixin(ModelBase):
    id: FieldBase = FieldBase(
        name="id",
        type=str_26,
        primary_key=True,
        index=True,
        unique=True,
        nullable=False,
        foreign_key=ForeignKey("un0.relatedobject.id", ondelete="CASCADE"),
        related_name="relatedobject",
        server_default=func.un0.insert_relatedobject("un0", "user"),
        doc="Primary Key",
        forward_edge_name="HAS_ID",
        reverse_edge_name="IS_ID_OF",
    )


class ActiveMixin(ModelBase):
    is_active: FieldBase = FieldBase(
        name="is_active",
        type=BOOLEAN,
        server_default=text("true"),
        doc="Indicates if the record is active",
    )


class DeleteMixin(ModelBase):
    is_deleted: FieldBase = FieldBase(
        name="is_deleted",
        type=BOOLEAN,
        server_default=text("false"),
        doc="Indicates if the record is deleted",
    )
    deleted_at: FieldBase = FieldBase(
        name="deleted_at",
        type=TIMESTAMP(timezone=True),
        required=False,
        editable=False,
        doc="Time at which the record was deleted",
    )
    deleted_by: FieldBase = FieldBase(
        name="deleted_by",
        type=str_26,
        required=False,
        foreign_key=ForeignKey("un0.user.id", ondelete="CASCADE"),
        related_name="deleted",
        index=True,
        doc="User that deleted the record",
        forward_edge_name="WAS_DELETED_BY",
        reverse_edge_name="DELETED",
    )

    def emit_sql(self) -> str:
        """
        Generates a SQL trigger creation statement for validating deletions.

        This method creates a SQL trigger named `validate_delete_trigger` that is
        executed before a delete operation on the specified table. The trigger
        calls the `un0.validate_delete()` function to perform validation.

        Returns:
            str: A SQL statement for creating the `validate_delete_trigger`.
        """
        return textwrap.dedent(
            f"""
            CREATE TRIGGER validate_delete_trigger 
            BEFORE DELETE ON {self.db_schema_name}.{self.db_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.validate_delete();
            """
        )


class CreatedModifiedMixin(ModelBase):
    created_at: FieldBase = FieldBase(
        name="created_at",
        type=TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        doc="Time the record was created",
        editable=False,
    )
    owned_by: FieldBase = FieldBase(
        name="owned_by",
        type=str_26,
        foreign_key=ForeignKey("un0.user.id", ondelete="CASCADE"),
        related_name="owned",
        index=True,
        doc="User that owns the record",
        forward_edge_name="IS_OWNED_BY",
        reverse_edge_name="OWNS",
    )
    modified_at: FieldBase = FieldBase(
        name="modified_at",
        type=TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        doc="Time the record was modified_at",
        editable=False,
    )
    modified_by: FieldBase = FieldBase(
        name="modified_by",
        type=str_26,
        foreign_key=ForeignKey("un0.user.id", ondelete="CASCADE"),
        related_name="modified",
        index=True,
        doc="User that last modified the record",
        forward_edge_name="WAS_LAST_MODIFIED_BY",
        reverse_edge_name="LAST_MODIFIED",
    )

    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            CREATE TRIGGER set_owner_and_modified_trigger
            BEFORE INSERT OR UPDATE ON {self.db_schema_name}.{self.db_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_owner_and_modified();
            """
        )


class ImportMixin(ModelBase):
    import_id: FieldBase = FieldBase(
        name="import_id",
        type=int,
        doc="Primary Key of the original system of the record",
    )
    import_key: FieldBase = FieldBase(
        name="import_key",
        type=str_26,
        doc="Unique identifier of the original system of the record",
    )


class NameDescriptionMixin(ModelBase):
    name: FieldBase = FieldBase(
        name="name",
        type=str_128,
        doc="Name of the record",
    )
    description: FieldBase = FieldBase(
        name="description",
        type=str_255,
        doc="Description of the record",
    )


class TenantMixin(ModelBase):
    tenant: FieldBase = FieldBase(
        name="tenant",
        type=str_26,
        foreign_key=ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
