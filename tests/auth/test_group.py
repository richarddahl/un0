# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

import sqlalchemy as sa

from un0.auth.tables import Group
from un0.config import settings as sttngs

'''
class TestGroup:
    @pytest.mark.parametrize("session", ["un0_test_group"], indirect=["session"])
    def test_super_user_select_group(
        self,
        session,
        mock_rls_vars,
        data_dict,
    ):
        """Tests that a user can be read by a superuserwith each of the db ROLEs."""
        with session as session:
            session.execute(text(mock_rls_vars))

            # Test with admin role
            session.execute(func(un0.mock_role("admin")))
            stmt = select(func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4

            # Test with writer role
            stmt = select(func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4

            # Test with reader role
            stmt = select(func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4
        session.close()

'''
