# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Optional

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import BOOLEAN, TEXT

from pydantic.dataclasses import dataclass

from un0.database.fields import FieldDefinition
from un0.database.models import ModelMixin
from un0.database.sql_emitters import SQLEmitter


class NameMixin(ModelMixin):
    """
    NameMixin is a mixin class that provides a 'name' field definition for models.

    Attributes:
        field_definitions (dict): A dictionary defining the 'name' field with its data
            type, nullability, and documentation.
        name (str): The name of the record.
    """

    field_definitions = {
        "name": FieldDefinition(
            data_type=TEXT,
            nullable=False,
            doc="Name of the record",
        ),
    }

    name: Optional[str] = None


class DescriptionMixin(ModelMixin):
    """
    DescriptionMixin is a mixin class that provides a description field for a model.

    Attributes:
        description (Optional[str]): A string field that holds the description of the record.
            It is optional and can be null.

    Field Definitions:
        field_definitions (dict): A dictionary containing the definition of the description field,
            including its data type, nullability, and documentation.
    """

    field_definitions = {
        "description": FieldDefinition(
            data_type=TEXT,
            doc="Description of the record",
        ),
    }

    description: Optional[str] = None


@dataclass
class SoftDelete(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = """
            DECLARE
                user_id TEXT:= current_setting('rls_var.user_id', true);
            BEGIN
                /* 
                */
                IF OLD.is_deleted IS TRUE THEN
                    OLD.deleted_at = now();
                    OLD.deleted_by_id = user_id;
                    OLD.modified_at = now();
                    OLD.modified_by_id = user_id;
                    RETURN OLD;
                ELSE
                    EXECUTE format('
                        UPDATE %I 
                        SET is_deleted = true,
                            is_active = false,
                            deleted_at = now(),
                            deleted_by_id = %L,
                            modified_at = now(),
                            modified_by_id = %L
                        WHERE id = %L', TG_TABLE_NAME, user_id, user_id, OLD.id
                    );
                    RETURN NULL;
                END IF;
            END;
            """

        return self.create_sql_function(
            "soft_delete",
            function_string,
            include_trigger=True,
            operation="DELETE",
            timing="BEFORE",
            db_function=True,
        )


class ActiveDeletedMixin(ModelMixin):
    """
    Mixin class that adds an 'is_active' field to a model.

    SqlEmitter:
        The ActiveFieldSQLEmitter alters the table to add the default of True to the 'is_active'
        field.

    Attributes:
        sql_emitters (list): List of SQL emitters for the mixin.
        field_definitions (dict): Dictionary defining the 'is_active' field.
        is_active (bool): Indicates if the record is active. Defaults to True.
    """

    sql_emitters = [SoftDelete]
    field_definitions = {
        "is_active": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("true"),
            doc="Indicates if the record is active",
            nullable=False,
        ),
        "is_deleted": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("false"),
            nullable=False,
            doc="Indicates if the record is deleted",
        ),
    }

    is_active: bool = True
    is_deleted: bool = False


class ImportMixin(ModelMixin):
    """
    ImportMixin is a mixin class that provides fields and field definitions for importing
    records from an external system.

    Attributes:
        field_definitions (dict): A dictionary defining the fields for import_id and import_key.
        import_id (Optional[int]): Primary Key of the original system of the record.
        import_key (Optional[str]): Unique identifier of the original system of the record.
    """

    field_definitions = {
        "import_id": FieldDefinition(
            data_type=TEXT,
            doc="Primary Key of the original system of the record",
        ),
        "import_key": FieldDefinition(
            data_type=TEXT,
            doc="Unique identifier of the original system of the record",
        ),
    }

    import_id: Optional[str] = None
    import_key: Optional[str] = None
