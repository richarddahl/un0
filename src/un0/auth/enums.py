# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import enum


#  Enumerations
class TenantType(str, enum.Enum):
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
