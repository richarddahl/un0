# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import enum


class MessageImportance(str, enum.Enum):
    INFORMATION = "Information"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ModelMaskConfigDataType(str, enum.Enum):
    """
    Enumeration representing the data types for mask configurations.

    Attributes:
        NATIVE (str): Native data type.
        STRING (str): Babel formatted (localized) string.
        ELEMENT (str): HTML Form Element Dictionary.

    """

    NATIVE = "native"
    STRING = str
    ELEMENT = dict


class UnoSelectResultType(str, enum.Enum):
    """
    Enumeration representing the result types for database select operations.

    Attributes:
        FETCH_ONE (str): Fetches a single row from the result set.
        FETCH_MANY (str): Fetches multiple rows from the result set.
        FETCH_ALL (str): Fetches all rows from the result set.
        FIRST (str): Fetches the first row from the result set.
        COUNT (str): Returns the count of rows in the result set.
        KEYS (str): Returns the keys of the result set.
        SCALAR (str): Returns a single value from the result set.
    """

    FETCH_ONE = "one"
    FETCH_MANY = "many"
    FETCH_ALL = "all"
    FIRST = "first"
    COUNT = "count"
    KEYS = "keys"
    SCALAR = "scalar"


#  Enumerations
class CustomerType(str, enum.Enum):
    """
    Enumeration class representing the types of authenticated groups.

    Attributes:
        INDIVIDUAL (str): Represents an individual group.
        SMALL_BUSINESS (str): Represents a small business group.
        CORPORATE (str): Represents a corporate group.
        ENTERPRISE (str): Represents an enterprise group.
    """

    INDIVIDUAL = "Individual"
    SMALL_BUSINESS = "Small Business"
    CORPORATE = "Corporate"
    ENTERPRISE = "Enterprise"


class PermissionAction(str, enum.Enum):
    """
    Enumeration class representing the permissions in the Uno application.

    Each permission corresponds to a specific SQL operation.

    Attributes:
        INSERT (str): Users with this permission may execute SQL INSERT operations for the table/group.
        SELECT (str): Users with this permission may execute SQL SELECT operations for the table/group.
        UPDATE (str): Users with this permission may execute SQL UPDATE operations for the table/group.
        DELETE (str): Users with this permission may execute SQL DELETE operations for the table/group.
    """

    INSERT = "Insert"
    SELECT = "Select"
    UPDATE = "Update"
    DELETE = "Delete"


class RecordOperation(str, enum.Enum):
    """
    Enumeration class representing the possible actions for a record in the database.

    Each action corresponds to a specific state change in the records lifecycle.

    Attributes:
        INSERT (str): Record inserted into database
        UPDATE (str): Object updateing in database
        DELETED (str): Object deleted from database
        TRUNCATE (str): Object truncated from database

    """

    INSERT = "Insert"
    UPDATE = "Update"
    DELETE = "Delete"
    TRUNCATE = "Truncate"


# Filter Enumerations
class Include(str, enum.Enum):
    """
    Enumeration class for querying the database.

    This class represents the options for including or excluding something in a query.

    Attributes:
        Include (str): The query should include the specified value.
        Exclude (str): The query should exclude the specified value.
    """

    INCLUDE = "Include"
    EXCLUDE = "Exclude"


class Match(str, enum.Enum):
    """
    Enumeration class for Uno match types.

    The Match class represents the different match types in db queries.

    Attributes:
        AND (str): Represents the 'AND' match type.
        OR (str): Represents the 'OR' match type.
        NOT (str): Represents the 'NOT' match type.
    """

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class FieldType(str, enum.Enum):
    """
    Enumeration class representing the possible field types in the Uno application.

    Attributes:
        ARRAY (str): Represents a list field type.
        BIGINT (str): Represents an integer field type.
        BOOLEAN (str): Represents a boolean field type.
        DATE (str): Represents a date field type.
        DECIMAL (str): Represents a decimal field type.
        ENUM (str): Represents an enumeration field type.
        INTERVAL (str): Represents a time interval field type.
        JSON (str): Represents a JSON field type.
        TEXT (str): Represents a text field type.
        TIME (str): Represents a time field type.
        TIMESTAMP (str): Represents a timestamp field type.
        VARCHAR (str): Represents a variable-length character field type.

    """

    ARRAY = "list"
    BIGINT = "int"
    BOOLEAN = "bool"
    DATE = "date"
    DECIMAL = "Decimal"
    ENUM = "Enum"
    INTERVAL = "timedelta"
    JSON = "dict"
    TEXT = "str"
    TIME = "time"
    TIMESTAMP = "datetime"
    VARCHAR = "str"


class Lookup(str, enum.Enum):
    """
    Enumeration class for Uno lookup operations.

    This class defines the available lookup operations that can be used in the Uno framework.
    Each lookup operation is represented by a string value.

    Attributes:
        EQUAL (str): uses the sqlalchemy __eq__ method
        NOT_EQUAL (str): uses the sqlalchemy __ne__ method
        GREATER_THAN (str): uses the sqlalchemy __gt__ method
        GREATER_THAN_OR_EQUAL (str): uses the sqlalchemy __ge__ method
        LESS_THAN (str): uses the sqlalchemy __lt__ method
        LESS_THAN_OR_EQUAL (str): uses the sqlalchemy __le__ method
        BETWEEN (str): uses the sqlalchemy between method
        IN (str): uses the sqlalchemy in_ method
        NOT_IN (str): uses the sqlalchemy not_in method
        NULL (str): uses the sqlalchemy is_ method
        NOT_NULL (str): uses the sqlalchemy is_not method
        LIKE (str): uses the sqlalchemy like method
        ILIKE (str): uses the sqlalchemy ilike method
        NOT_LIKE (str): uses the sqlalchemy notlike method
        NOT_ILIKE (str): uses the sqlalchemy notilike method
        STARTS_WITH (str): uses the sqlalchemy startswith method
        ENDS_WITH (str): uses the sqlalchemy endswith method
        CONTAINS (str): uses the sqlalchemy contains method
    """

    EQUAL = "__eq__"
    NOT_EQUAL = "__ne__"
    GREATER_THAN = "__gt__"
    GREATER_THAN_OR_EQUAL = "__ge__"
    LESS_THAN = "__lt__"
    LESS_THAN_OR_EQUAL = "__le__"
    BETWEEN = "between"
    IN = "in_"
    NOT_IN = "not_in"
    NULL = "is_"
    NOT_NULL = "is_not"
    LIKE = "like"
    ILIKE = "ilike"
    NOT_LIKE = "notlike"
    NOT_ILIKE = "notilike"
    STARTS_WITH = "startswith"
    ENDS_WITH = "endswith"
    CONTAINS = "contains"


selectlookups = [
    Lookup.EQUAL,
    Lookup.NOT_EQUAL,
    Lookup.NULL,
    Lookup.NOT_NULL,
    Lookup.IN,
    Lookup.NOT_IN,
]

numeric_lookups = [
    Lookup.EQUAL,
    Lookup.NOT_EQUAL,
    Lookup.BETWEEN,
    Lookup.GREATER_THAN,
    Lookup.GREATER_THAN_OR_EQUAL,
    Lookup.LESS_THAN,
    Lookup.LESS_THAN_OR_EQUAL,
    Lookup.NULL,
    Lookup.NOT_NULL,
    Lookup.IN,
    Lookup.NOT_IN,
]

string_lookups = [
    Lookup.EQUAL,
    Lookup.NOT_EQUAL,
    Lookup.LIKE,
    Lookup.NOT_LIKE,
    Lookup.ILIKE,
    Lookup.NOT_ILIKE,
    Lookup.STARTS_WITH,
    Lookup.ENDS_WITH,
    Lookup.CONTAINS,
    Lookup.NULL,
    Lookup.NOT_NULL,
]


# Workflow Enumerations
class WorkflowRecordStatus(str, enum.Enum):
    CLOSED = "Closed"
    OPEN = "Open"
    AT_RISK = "At Risk"
    OVERDUE = "Overdue"


class WorkflowRecordState(str, enum.Enum):
    PENDING = "Pending"
    COMPLETE = "Complete"
    CANCELLED = "Cancelled"
    DEFERRED = "Deferred"


class WorkflowFlag(str, enum.Enum):
    INFORMATION = "Information"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class WorkflowDBEvent(str, enum.Enum):
    INSERT = "Insert"
    UPDATE = "Update"
    DELETE = "Delete"


class WorkflowTrigger(str, enum.Enum):
    DB_EVENT = "DB Event"
    SCHEDULE = "Schedule"
    USER = "User"
