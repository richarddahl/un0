# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from sqlalchemy.orm import Session


def get_permissible_groups_for_user(user_id: int, session: Session) -> str:
    """
    Generate a SQL statement to retrieve all permissible groups for a given user.

    :param user_id: The ID of the user.
    :param session: The SQLAlchemy session to use for the query.
    :return: A SQL statement string.
    """
    raw_sql = f"""
    SELECT g.*
    from group g
    JOIN un0.user_group_role ugr ON ugr.group_id = g.id
    JOIN un0.user u ON u.id = ugr.user_id
    JOIN un0.tablepermission tp ON ugr.role_id = tp.id
    WHERE u.id = {user_id} AND tp.is_active = TRUE
    """
    return raw_sql
