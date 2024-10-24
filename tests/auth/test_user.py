# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest
import json
import pytz

from pydantic.fields import FieldInfo

from sqlalchemy import func, text, select, update, delete
from sqlalchemy.exc import ProgrammingError

from un0.auth.tables import User
from un0.auth.models import UserObj
from un0.config import settings as sttngs
from un0.db.tools.db_tool import DBTool

from tests.conftest import mock_rls_vars


class TestUser:
    """Tests for the User model."""

    def test_create_user_function(self, session):
        """Creates the superuser and returns it's id."""
        db = DBTool()
        assert 1 == 1

        superuser_id = db.create_user(
            email="new_admin@notorm.com",
            handle="new_admin",
            full_name="New Admin",
            is_superuser=True,
        )
        assert superuser_id is not None
        with session.begin():
            session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
            superuser = session.scalar(select(User).where(User.id == superuser_id))
            assert superuser is not None
            assert superuser.email == "new_admin@notorm.com"
            assert superuser.handle == "new_admin"
            assert superuser.full_name == "New Admin"
            assert superuser.is_superuser is True
            assert superuser.is_tenant_admin is False
            assert superuser.is_active is True
            assert superuser.is_deleted is False
            assert superuser.created_at is not None
            assert superuser.modified_at is not None
            assert superuser.deleted_at is None
            session.execute(func.un0.mock_role("admin"))
            session.execute((delete(User).where(User.id == superuser_id)))
        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="writer")
                )
            )
            session.execute((delete(User).where(User.id == superuser_id)))

    ############################
    # Admin user related tests #
    ############################

    def test_admin_user(self, session, superuser_id):
        """Tests that the admin user, created in create_db.create_db was created correctly."""
        with session.begin():
            session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
            admin_user = session.scalar(
                select(User).where(User.email == sttngs.SUPERUSER_EMAIL)
            )
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

    ############################
    # Row Level Security Tests #
    ############################

    ##############
    # SELECT Tests
    # Superuser SELECT Test
    def test_rls_superuser_select(self, session, superuser_id, user_dict):
        """Tests that a superuser can select all users with each role except the login role."""
        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="admin")
                )
            )
            # Test with admin role
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            # Test with writer role
            session.execute(func.un0.mock_role("writer"))
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            # Test with reader role
            session.execute(func.un0.mock_role("reader"))
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            # Test with login role
            session.execute(func.un0.mock_role("login"))
            stmt = select(func.count()).select_from(User)
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(stmt)
            assert "permission denied" in str(excinfo.value)

    # Tenant Admin SELECT User Test
    def test_rls_tenant_admin_select(self, session, user_dict):
        """Tests that tenant users can only select users from their tenant."""
        acme_admin = user_dict.get("admin@acme.com")
        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(
                        acme_admin.get("id"),
                        email=acme_admin.get("email"),
                        is_superuser="false",
                        is_tenant_admin="true",
                        tenant_id=acme_admin.get("tenant_id"),
                        role_name="admin",
                    )
                )
            )

            # Test with admin role
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with writer role
            session.execute(func.un0.mock_role("writer"))
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with reader role
            session.execute(func.un0.mock_role("reader"))
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with login role
            session.execute(func.un0.mock_role("login"))
            stmt = select(func.count()).select_from(User)
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(stmt)
            assert "permission denied" in str(excinfo.value)

    # Non-Privileged User SELECT Test
    def test_rls_non_privileged_user_select(self, session, superuser_id, user_dict):
        """Tests that non-privileged users can only select users from their tenant."""
        acme_user = user_dict.get("admin@acme.com")
        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(
                        acme_user.get("id"),
                        email=acme_user.get("email"),
                        is_superuser="false",
                        is_tenant_admin="false",
                        tenant_id=acme_user.get("tenant_id"),
                        role_name="admin",
                    )
                )
            )
            # Test with admin role
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with writer role
            session.execute(func.un0.mock_role("writer"))
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with reader role
            session.execute(func.un0.mock_role("reader"))
            stmt = select(func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 10

            # Test with login role
            session.execute(func.un0.mock_role("login"))
            stmt = select(func.count()).select_from(User)
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(stmt)
            assert "permission denied" in str(excinfo.value)

    ############################
    # INSERT/UPDATE/DELETE Tests

    # Superuser INSERT, UPDATE, DELETE Test
    @pytest.mark.parametrize("role_name", ["admin", "writer"])
    def test_rls_superuser_can_insert_update_delete(
        self, session, superuser_id, new_user, role_name, tenant_dict
    ):
        """
        Tests that a user can be INSERTED, UPDATED, and DELETED
            by a superuser with the admin and writer roles.
        """

        with session.begin():
            # INSERT the user with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            session.add(new_user)

        with session.begin():
            # Verify the user was INSERTED with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            assert new_user.id is not None

            # UPDATE the user with the admin role
            stmt = select(User).where(User.email == new_user.email)
            new_user = session.scalar(stmt)
            new_user.full_name = "Updated User"

        with session.begin():
            # Verify the user was UPDATED with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            assert new_user.full_name == "Updated User"

            # UPDATE the user's TENANT with the admin role
            stmt = select(User).where(User.email == new_user.email)
            new_user = session.scalar(stmt)
            new_user.tenant_id = tenant_dict.get("Nacme Corp").get("id")

        with session.begin():
            # Verify the user's tenant ID was UPDATED with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            assert new_user.tenant_id == tenant_dict.get("Nacme Corp").get("id")

            # DELETE the user with the admin role (trigger sets is_deleted to True)
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            session.execute((delete(User).where(User.email == new_user.email)))

        with session.begin():
            # Verify that new_user.is_deleted was set to True with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            stmt = select(User).where(User.email == new_user.email)
            new_user = session.scalar(stmt)
            assert new_user.is_deleted is True

            # Actually DELETE the user with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            session.execute((delete(User).where(User.email == new_user.email)))

        with session.begin():
            # Verify the user was DELETED with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name=role_name)
                )
            )
            assert session.scalar(stmt) is None

    # Superuser cannot INSERT, UPDATE, DELETE Test with reader role
    def test_rls_superuser_cannot_insert_update_with_reader(
        self, session, superuser_id, new_user, user_dict
    ):
        """
        Tests that a user cannot be INSERTED, UPDATED, or DELETED
            by a superuser with the reader role.
        """
        with session.begin():
            # Try to INSERT the user with the admin role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="reader")
                )
            )
            session.add(new_user)
            with pytest.raises(ProgrammingError) as excinfo:
                session.commit()
            assert "permission denied" in str(excinfo.value)

        new_user_email = user_dict.get("user1@acme.com").get("email")
        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="reader")
                )
            )

            # UPDATE a user with the reader role
            stmt = select(User).where(User.email == new_user_email)
            new_user = session.scalar(stmt)
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="reader")
                )
            )
            new_user.full_name = "Updated User"
            with pytest.raises(ProgrammingError) as excinfo:
                session.commit()
            assert "permission denied" in str(excinfo.value)

        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="reader")
                )
            )
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute((delete(User).where(User.email == new_user_email)))
            assert "permission denied" in str(excinfo.value)

    # Superuser cannot INSERT, UPDATE, DELETE Test with login role
    def test_rls_superuser_cannot_insert_update_with_login(
        self, session, superuser_id, new_user, user_dict
    ):
        """
        Tests that a user cannot be INSERTED, UPDATED, or DELETED
            by a superuser with the login role.
        """
        with session.begin():
            # INSERT a user with the login role
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="login")
                )
            )
            session.add(new_user)
            with pytest.raises(ProgrammingError) as excinfo:
                session.commit()
            assert "permission denied" in str(excinfo.value)

        new_user_email = user_dict.get("user1@acme.com").get("email")
        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="login")
                )
            )

            # SELECT a user with the login role
            stmt = select(User).where(User.email == new_user_email)
            with pytest.raises(ProgrammingError) as excinfo:
                new_user = session.scalar(stmt)
            assert "permission denied" in str(excinfo.value)

        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="login")
                )
            )
            new_user.full_name = "Updated User"
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(
                    update(User)
                    .where(User.email == new_user_email)
                    .values(full_name="Updated User")
                )
            assert "permission denied" in str(excinfo.value)

        with session.begin():
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(superuser_id, role_name="login")
                )
            )
            session.execute(func.un0.mock_role("login"))
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute((delete(User).where(User.email == new_user_email)))
            assert "permission denied" in str(excinfo.value)

    def test_rls_tenant_admin_create_update_delete_tenant_user(
        self,
        session,
        acme_tenant,
        acme_group,
        nacme_tenant,
        acme_admin_vars,
    ):
        """Tests that a tenant user can be inserted, updated, and deleted by a tenant admin.

        Also tests that the tenant user's tenant_id CANNOT be changed by a tenant admin.

        """
        acme_user = User(
            email="user@acme.com",
            handle="acme user",
            full_name="ACME User",
            tenant_id=acme_tenant.get("id"),
            default_group_id=acme_group.get("id"),
        )
        with session.begin():
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            # Create the user
            session.add(acme_user)
            session.commit()

        with session.begin():
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            acme_user.full_name = "Updated ACME User"
            # Verify the user was updated
            assert acme_user.full_name == "Updated ACME User"
            session.add(acme_user)
            session.commit()

        with session.begin():
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            # Try to UPDATE the user's TENANT
            acme_user.tenant_id = nacme_tenant.get("id")
            session.add(acme_user)
            # Verify the user's tenant ID was not updated and a RLS error was raised
            with pytest.raises(ProgrammingError) as excinfo:
                session.commit()
            assert "new row violates row-level security policy" in str(excinfo.value)

        with session.begin():
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            # DELETE the user (trigger sets is_deleted to True)
            session.execute((delete(User).where(User.email == acme_user.email)))

        with session.begin():
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            # Verify that new_user.is_deleted was set to True
            stmt = select(User).where(User.email == acme_user.email)
            user = session.scalar(stmt)
            assert user.is_deleted is True

            # Actually DELETE the user with the admin role
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            session.execute((delete(User).where(User.email == user.email)))

        with session.begin():
            # Verify the user was DELETED
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            assert session.scalar(stmt) is None

    def test_rls_tenant_admin_create_non_tenant_user(
        self,
        session,
        acme_group,
        nacme_tenant,
        acme_admin_vars,
    ):
        """Tests that a tenant admin cannot create a user with a different tenant_id."""
        with session.begin():
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            acme_user = User(
                email="not_acme@acme.com",
                handle="not_acme user",
                full_name="Not ACME User",
                tenant_id=nacme_tenant.get("id"),
                default_group_id=acme_group.get("id"),
            )
            session.add(acme_user)
            with pytest.raises(ProgrammingError) as excinfo:
                session.commit()
            assert "new row violates row-level security policy" in str(excinfo.value)

    def test_rls_tenant_admin_delete_non_tenant_user(
        self,
        session,
        acme_admin_vars,
        superuser_id,
    ):
        """Tests that a tenant admin cannot delete a user with a different tenant_id."""
        with session.begin():
            session.execute(func.un0.mock_authorize_user(*acme_admin_vars))
            # The RLS prevents the select from returning the user, so we can't delete it but get no error
            session.execute(delete(User).where(User.email == "admin@nacme.com"))
            session.commit()

        with session.begin():
            session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
            stmt = select(User).where(User.email == "admin@nacme.com")
            user_not_deleted = session.scalar(stmt)
            assert user_not_deleted is not None

    def test_rls_regular_user_cannot_create_a_user(
        self, session, superuser_id, data_dict
    ):
        """Tests that a regular user cannot create a user."""
        with session.begin():
            acme_user = data_dict.get("users").get("user1@acme.com")
            acme = data_dict.get("tenants").get("Acme Inc.")
            session.execute(
                func.un0.mock_authorize_user(
                    *mock_rls_vars(
                        acme_user.get("email"),
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
            with pytest.raises(ProgrammingError):
                session.commit()

    def test_user_obj_select_schema_creation(self):
        """Tests the User model."""
        user_obj = UserObj()
        assert user_obj is not None
        select_schema = user_obj.models.get("select_schema")
        assert select_schema is not None
        assert select_schema.__annotations__ is not None
        assert select_schema.__annotations__.get("id") == str
        assert select_schema.__annotations__.get("email") == str
        assert select_schema.__annotations__.get("handle") == str
        assert select_schema.__annotations__.get("full_name") == str
        assert select_schema.__annotations__.get("tenant_id") == str | None
        assert select_schema.__annotations__.get("default_group_id") == str | None
        assert select_schema.__annotations__.get("is_superuser") == bool
        assert select_schema.__annotations__.get("is_tenant_admin") == bool
        assert select_schema.__annotations__.get("is_active") == bool
        assert select_schema.__annotations__.get("is_deleted") == bool
        assert select_schema.__annotations__.get("created_at") == datetime.datetime
        assert select_schema.__annotations__.get("owner_id") == str | None
        assert select_schema.__annotations__.get("modified_at") == datetime.datetime
        assert select_schema.__annotations__.get("modified_by_id") == str | None
        assert (
            select_schema.__annotations__.get("deleted_at") == datetime.datetime | None
        )
        assert select_schema.__annotations__.get("deleted_by_id") == str | None

    def test_user_obj_insert_schema_creation(self):
        user_obj = UserObj()
        assert user_obj is not None
        insert_schema = user_obj.models.get("insert_schema")
        assert insert_schema is not None
        assert insert_schema.__annotations__ is not None
        assert insert_schema.__annotations__.get("id") is None
        assert insert_schema.__annotations__.get("email") == str
        assert insert_schema.__annotations__.get("handle") == str
        assert insert_schema.__annotations__.get("full_name") == str
        assert insert_schema.__annotations__.get("tenant_id") == str | None
        assert insert_schema.__annotations__.get("default_group_id") == str | None
        assert insert_schema.__annotations__.get("is_superuser") == bool
        assert insert_schema.__annotations__.get("is_tenant_admin") == bool
        assert insert_schema.__annotations__.get("is_active") is None
        assert insert_schema.__annotations__.get("is_deleted") is None
        assert insert_schema.__annotations__.get("created_at") is None
        assert insert_schema.__annotations__.get("owner_id") is None
        assert insert_schema.__annotations__.get("modified_at") is None
        assert insert_schema.__annotations__.get("modified_by_id") is None
        assert insert_schema.__annotations__.get("deleted_at") is None
        assert insert_schema.__annotations__.get("deleted_by_id") is None

    def test_user_obj_update_schema_creation(self):
        user_obj = UserObj()
        assert user_obj is not None
        update_schema = user_obj.models.get("update_schema")
        assert update_schema is not None
        assert update_schema.__annotations__ is not None
        assert update_schema.__annotations__.get("id") is None
        assert update_schema.__annotations__.get("email") == str
        assert update_schema.__annotations__.get("handle") == str
        assert update_schema.__annotations__.get("full_name") == str
        assert update_schema.__annotations__.get("tenant_id") == str | None
        assert update_schema.__annotations__.get("default_group_id") == str | None
        assert update_schema.__annotations__.get("is_superuser") == bool
        assert update_schema.__annotations__.get("is_tenant_admin") == bool
        assert update_schema.__annotations__.get("is_active") == bool
        assert update_schema.__annotations__.get("is_deleted") is None
        assert update_schema.__annotations__.get("created_at") is None
        assert update_schema.__annotations__.get("owner_id") == str | None
        assert update_schema.__annotations__.get("modified_at") is None
        assert update_schema.__annotations__.get("modified_by_id") is None
        assert update_schema.__annotations__.get("deleted_at") is None
        assert update_schema.__annotations__.get("deleted_by_id") is None

    def test_user_obj_list_schema_creation(self):
        user_obj = UserObj()
        assert user_obj is not None
        list_schema = user_obj.models.get("list_schema")
        assert list_schema is not None
        assert list_schema.__annotations__ is not None
        assert list_schema.__annotations__.get("id") == str
        assert list_schema.__annotations__.get("email") == str
        assert list_schema.__annotations__.get("handle") == str
        assert list_schema.__annotations__.get("full_name") is None
        assert list_schema.__annotations__.get("tenant_id") is None
        assert list_schema.__annotations__.get("default_group_id") is None
        assert list_schema.__annotations__.get("is_superuser") is None
        assert list_schema.__annotations__.get("is_tenant_admin") is None
        assert list_schema.__annotations__.get("is_active") is None
        assert list_schema.__annotations__.get("is_deleted") is None
        assert list_schema.__annotations__.get("created_at") is None
        assert list_schema.__annotations__.get("owner_id") is None
        assert list_schema.__annotations__.get("modified_at") is None
        assert list_schema.__annotations__.get("modified_by_id") is None
        assert list_schema.__annotations__.get("deleted_at") is None
        assert list_schema.__annotations__.get("deleted_by_id") is None

    def test_user_schema_instantiation(self, session, superuser_id):
        """Tests that the admin user, created in create_db.create_db was created correctly."""
        with session.begin():
            session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
            admin_user = session.scalar(
                select(User).where(User.email == sttngs.SUPERUSER_EMAIL)
            ).__dict__
        user_obj = UserObj()
        assert user_obj is not None

        select_schema = user_obj.models.get("select_schema")(**admin_user)
        assert select_schema is not None
        print("")
        print(select_schema.model_dump())
        print(select_schema.process_app_logic())

        insert_schema = user_obj.models.get("insert_schema")(**admin_user)
        assert insert_schema is not None
        print("")
        print(insert_schema.model_dump())

        update_schema = user_obj.models.get("update_schema")(**admin_user)
        assert update_schema is not None
        print("")
        print(update_schema.model_dump())

        list_schema = user_obj.models.get("list_schema")(**admin_user)
        assert list_schema is not None
        print("")
        print(list_schema.model_dump())
