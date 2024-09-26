# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest
import json
import pytz

import sqlalchemy as sa

from tests.conftest import mock_s_vars
from un0.auth.models import Tenant, User
from un0.auth.enums import TenantType
from un0.cmd.sql import (
    set_role_login,
    set_role_reader,
    set_role_writer,
    set_role_admin,
)
from un0.config import settings as sttngs


class TestUser:
    """Tests for the User model."""

    """
    Admin user related tests
    """

    @classmethod
    @pytest.fixture(scope="function")
    def new_user(cls, tenant_dict):
        tenant_id = tenant_dict.get("Acme Inc.").get("id")
        return User(
            email="new_user@acme.com",
            handle="new_user",
            full_name="New User",
            tenant_id=tenant_id,
        )

    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_admin_user(self, admin_user):
        """Tests that the admin user, created in create_db.create_db was created correctly."""
        assert admin_user is not None
        assert admin_user.email == sttngs.SUPERUSER_EMAIL
        assert admin_user.handle == sttngs.SUPERUSER_HANDLE
        assert admin_user.full_name == sttngs.SUPERUSER_FULL_NAME
        assert admin_user.is_superuser is True
        assert admin_user.is_tenant_admin is False
        assert admin_user.is_active is True
        assert admin_user.is_deleted is False
        assert admin_user.created_at is not None
        assert admin_user.modified_at is not None
        assert admin_user.deleted_at is None

    """
    Graph related tests
    """

    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_admin_user_graph(self, session, db_name, admin_user):
        """Tests that the graph vertext for the admin user was created correctly."""
        session.execute(sa.text(set_role_admin(db_name=db_name)))
        stmt = sa.text(
            f"""
                SELECT * FROM cypher('graph', $$
                MATCH (u:User)
                WHERE (u.id = '{admin_user.id}')
                RETURN properties(u)
                $$) as (type agtype);
                """
        )
        admin_user_vertex = session.execute(stmt)
        properties = json.loads(admin_user_vertex.first()[0])
        assert properties["email"] == str(admin_user.email)
        assert properties["handle"] == str(admin_user.handle)
        assert properties["full_name"] == str(admin_user.full_name)
        assert properties["is_superuser"] == str(admin_user.is_superuser).lower()
        assert properties["is_tenant_admin"] == str(admin_user.is_tenant_admin).lower()
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

    ############################
    # Row Level Security Tests #
    ############################

    ##############
    # SELECT Tests

    # Superuser SELECT Test
    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_superuser_select(self, session, db_name, user_dict, mock_su_s_vars):
        """Tests that a superuser can select all users with each role except the login role."""
        with session as session:
            session.execute(sa.text(mock_su_s_vars))

            # Test with admin role
            session.execute(sa.text(set_role_admin(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            # Test with writer role
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            # Test with reader role
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            # Test with login role
            session.execute(sa.text(set_role_login(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(stmt)
            assert "permission denied" in str(excinfo.value)

    # Tenant Admin SELECT Test
    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_tenant_admin_select(
        self,
        session,
        db_name,
        user_dict,
    ):
        """Tests that tenant users can only select users from their tenant."""
        with session as session:
            session.execute(
                sa.text(
                    mock_s_vars(
                        user_dict.get("admin@acme.com").get("email"),
                        False,
                        True,
                        user_dict.get("admin@acme.com").get("tenant_id"),
                    )
                )
            )

            # Test with admin role
            session.execute(sa.text(set_role_admin(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with writer role
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with reader role
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with login role
            session.execute(sa.text(set_role_login(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(stmt)
            assert "permission denied" in str(excinfo.value)

    # Non-Privileged User SELECT Test
    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_non_privileged_user_select(
        self,
        session,
        db_name,
        user_dict,
    ):
        """Tests that non-privileged users can only select users from their tenant."""
        with session as session:
            session.execute(
                sa.text(
                    mock_s_vars(
                        user_dict.get("user1@acme.com").get("email"),
                        False,
                        False,
                        user_dict.get("user1@acme.com").get("tenant_id"),
                    )
                )
            )

            # Test with admin role
            session.execute(sa.text(set_role_admin(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with writer role
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with reader role
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with login role
            session.execute(sa.text(set_role_login(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(stmt)
            assert "permission denied" in str(excinfo.value)

    ############################
    # INSERT/UPDATE/DELETE Tests

    # Superuser INSERT/UPDATE/DELETE Test
    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_superuser_insert_update_delete(
        self,
        session,
        db_name,
        mock_su_s_vars,
        new_user,
    ):
        """Tests that a user can be created by a superuser ."""
        with session as session:
            session.execute(sa.text(mock_su_s_vars))
            session.execute(sa.text(set_role_admin(db_name=db_name)))
            session.add(new_user)
            result = session.commit()
            assert result is None

            # Update the full_name of new_user
            new_user.full_name = "Updated User"
            session.add(new_user)
            result = session.commit()
            assert result is None

            # Delete the new_user
            session.delete(new_user)
            result = session.commit()
            assert result is None

    '''
    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_tenant_admin_create_delete_tenant_user(
        self,
        session,
        db_name,
        data_dict,
    ):
        """Tests that a tenant user can be created by a tenant admin."""
        with session as session:
            acme_admin = data_dict.get("users").get("admin@acme.com")
            acme = data_dict.get("tenants").get("Acme Inc.")
            session.execute(
                sa.text(
                    mock_s_vars(
                        acme_admin.get("email"),
                        False,
                        True,
                        acme.get("id"),
                    )
                )
            )
            acme_user = User(
                email="user@acme.com",
                handle="acme user",
                full_name="ACME User",
                tenant_id=acme.get("id"),
            )
            session.add(acme_user)
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            result = session.commit()
            assert result is None

    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_tenant_admin_create_non_tenant_user(self, session, db_name, data_dict):
        """Tests that a tenant admin cannot create a user with a different tenant_id."""
        with session as session:
            acme_admin = data_dict.get("users").get("admin@acme.com")
            acme = data_dict.get("tenants").get("Acme Inc.")
            nacme = data_dict.get("tenants").get("Nacme Corp")
            session.execute(
                sa.text(
                    mock_s_vars(
                        acme_admin.get("email"),
                        False,
                        True,
                        acme.get("id"),
                    )
                )
            )

            acme_user = User(
                email="not_acme@acme.com",
                handle="not_acme user",
                full_name="Not ACME User",
                tenant_id=nacme.get("id"),
            )
            session.add(acme_user)
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            with pytest.raises(sa.exc.ProgrammingError):
                session.commit()

    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_tenant_admin_delete_non_tenant_user(self, session, db_name, data_dict):
        """Tests that a tenant admin cannot delete a user with a different tenant_id."""
        with session as session:
            acme_user = data_dict.get("users").get("user1@acme.com")
            acme = data_dict.get("tenants").get("Acme Inc.")
            session.execute(
                sa.text(
                    mock_s_vars(
                        acme_user.get("email"),
                        False,
                        False,
                        acme.get("id"),
                    )
                )
            )

            unauthorized_acme_user = User(
                email="unauthorized@acme.com",
                handle="unauthorized acme user",
                full_name="Unauthorized ACME User",
                tenant_id=acme.get("id"),
            )
            session.add(unauthorized_acme_user)
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            with pytest.raises(sa.exc.ProgrammingError):
                session.commit()

    @pytest.mark.parametrize("db_name", ["un0_test_user"], indirect=["db_name"])
    @pytest.mark.parametrize("session", ["un0_test_user"], indirect=["session"])
    def test_rls_regular_user_cannot_create_a_user(self, session, db_name, data_dict):
        """Tests that a regular user cannot create a user."""
        with session as session:
            acme_user = data_dict.get("users").get("user1@acme.com")
            acme = data_dict.get("tenants").get("Acme Inc.")
            session.execute(
                sa.text(
                    mock_s_vars(
                        acme_user.get("email"),
                        False,
                        False,
                        acme.get("id"),
                    )
                )
            )

            unauthorized_acme_user = User(
                email="unauthorized@acme.com",
                handle="unauthorized acme user",
                full_name="Unauthorized ACME User",
                tenant_id=acme.get("id"),
            )
            session.add(unauthorized_acme_user)
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            with pytest.raises(sa.exc.ProgrammingError):
                session.commit()
    '''
