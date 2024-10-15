# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import json
import datetime
import pytz

import pytest  # type: ignore

from sqlalchemy import func, text, select
from sqlalchemy.exc import ProgrammingError

from un0.auth.models import User
from un0.config import settings as sttngs

from tests.conftest import mock_rls_vars


class TestFltr:
    pass
    '''
    def test_create_fields(self, session):
        assert True

    #######################
    # Graph related tests #
    #######################

    def test_admin_user_graph(self, session, superuser_id):
        """Tests that the graph vertext for the admin user was created correctly."""
        stmt = text(
            f"""
                SELECT * FROM cypher('graph', $$
                MATCH (u:User {{id: '{superuser_id}'}})
                RETURN properties(u)
                $$) as (type agtype);
                """
        )
        with session.begin():
            session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
            admin_user = session.scalar(
                select(User).where(User.email == sttngs.SUPERUSER_EMAIL)
            )
            session.execute(func.un0.mock_role("admin"))
            admin_user_vertex = session.scalars(stmt)
            assert admin_user_vertex is not None
            properties = json.loads(admin_user_vertex.first())
            assert properties["email"] == str(admin_user.email)
            assert properties["handle"] == str(admin_user.handle)
            assert properties["full_name"] == str(admin_user.full_name)
            assert properties["is_superuser"] == str(admin_user.is_superuser).lower()
            assert (
                properties["is_tenant_admin"] == str(admin_user.is_tenant_admin).lower()
            )
            assert properties["is_active"] == str(admin_user.is_active).lower()
            assert properties["is_deleted"] == str(admin_user.is_deleted).lower()
            _graph_created_at = datetime.datetime.strptime(
                properties["created_at"], "%Y-%m-%d %H:%M:%S.%f"
            ).replace(tzinfo=pytz.UTC)
            assert _graph_created_at == admin_user.created_at.replace(tzinfo=pytz.UTC)

            _graph_modified_at = datetime.datetime.strptime(
                properties["modified_at"], "%Y-%m-%d %H:%M:%S.%f"
            ).replace(tzinfo=pytz.UTC)
            assert _graph_modified_at == admin_user.modified_at.replace(tzinfo=pytz.UTC)
            with pytest.raises(KeyError):
                properties["deleted_at"]
    '''
