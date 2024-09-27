# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

import sqlalchemy as sa

from un0.auth.models import Group
from un0.cmd.sql import (
    set_role_admin,
    set_role_reader,
    set_role_writer,
)
from tests.conftest import (
    mock_s_vars,
)
from un0.config import settings as sttngs

'''
class TestGroup:
    @pytest.mark.parametrize("db_name", ["un0_test_group"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_group"], indirect=["session"])
    def test_super_user_select_group(
        self,
        session,
        db_name,
        mock_su_s_vars,
        data_dict,
    ):
        """Tests that a user can be read by a superuserwith each of the db ROLEs."""
        with session as session:
            session.execute(sa.text(mock_su_s_vars))

            # Test with admin role
            session.execute(sa.text(set_role_admin(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4

            # Test with writer role
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4

            # Test with reader role
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4
        session.close()

'''
