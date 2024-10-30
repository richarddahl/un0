# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import enum


#  Enumerations
class TenantType(str, enum.Enum):
    """
    Enumeration class representing the types of Tenants.

    Each tenant type corresponds to a specific customer group.
    Tenants are a key concept in the Uno library.
    They represent a group of users that may share permissions and access to data.
    Tenant Types can be configured via the settings to restrict the number of database
    objects, users, and or user groups allowed.

    Attributes:
        INDIVIDUAL (str): Represents an individual group.
        BUSINESS (str): Represents a small business group.
        CORPORATE (str): Represents a corporate group.
        ENTERPRISE (str): Represents an enterprise group.
    """

    INDIVIDUAL = "Individual"
    BUSINESS = "Business"
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
