# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from un0.enums import CustomerType

GROUP_DEFINITIONS = [
    {"name": "You", "group_type": CustomerType.INDIVIDUAL},
    {"name": "Mom and Pop", "group_type": CustomerType.SMALL_BUSINESS},
    # {"name": "Mom and Pop Accounting", "org_type": CustomerType.SMALL_BUSINESS},
    # {"name": "Mom and Pop Delivery", "org_type": CustomerType.SMALL_BUSINESS},
    {"name": "Natl Co", "group_type": CustomerType.CORPORATE},
    # {"name": "Natl Co Accounting", "org_type": CustomerType.CORPORATE, "parent_name": "Natl Co"},
    # {"name": "Natl Co Delivery", "org_type": CustomerType.CORPORATE},
    {"name": "MEGA Corp", "group_type": CustomerType.ENTERPRISE},
]

USER_DEFINITIONS = [
    {
        "email": "admin@un0.tech",
        "full_name": "UNO Administator",
        "plaintext_password": "this15notA$3cur3pa%%w*rd",
        "group": "UNO",
        "is_superuser": True,
        "is_customer_admin": True,
        "default_group": "UNO",
        "group_permissions": [("UNO", "Admin")],
    },
    {
        "email": "OTHER_ADMIN@other_domain.com",
        "full_name": "OTHER Admin",
        "plaintext_password": "this15notA$3cur3pa%%w*rd",
        "group": "OTHER",
        "is_customer_admin": True,
        "default_group": "OTHER",
        "group_permissions": [("OTHER", "Admin")],
    },
    {
        "email": "OTHER_Accounting@other_domain.com",
        "full_name": "OTHER Accounting",
        "plaintext_password": "this15notA$3cur3pa%%w*rd",
        "group": "OTHER",
        "default_group": "OTHER Accounting",
        "group_permissions": [("OTHER Accounting", "Admin"), ("OTHER", "Read")],
    },
    {
        "email": "OTHER_Manager@other_domain.com",
        "full_name": "OTHER Manager",
        "plaintext_password": "this15notA$3cur3pa%%w*rd",
        "group": "OTHER",
        "default_group": "OTHER Manager",
        "group_permissions": [("OTHER Manager", "Admin"), ("OTHER", "Read")],
    },
    {
        "email": "OTHER_Production@other_domain.com",
        "full_name": "OTHER Production",
        "plaintext_password": "this15notA$3cur3pa%%w*rd",
        "group": "OTHER",
        "default_group": "OTHER Production",
        "group_permissions": [("OTHER Production", "Admin"), ("OTHER", "Read")],
    },
]
