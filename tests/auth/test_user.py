# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest
import json
import pytz

import sqlalchemy as sa

from un0.auth.models import Tenant, User, Group
from un0.auth.enums import TenantType
from un0.cmd.sql import (
    set_role_admin,
    set_role_reader,
    set_role_writer,
)
from tests.conftest import (
    mock_session_variables_for_user,
)
from un0.cmd import create_db, drop_db
from un0.config import settings as sttngs


class TestUser:
    @classmethod
    def setup_class(cls, db_name="un0_test_user"):
        drop_db.drop(db_name=db_name)
        create_db.create(db_name=db_name)

    @pytest.fixture
    def select_admin_user(self, session, db_name, mock_superuser_session_variables):
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            q = sa.sql.select(User).where(User.email == sttngs.SUPERUSER_EMAIL)
            result = session.execute(q)
            yield result.scalars().first()
        session.close()

    def test_admin_user(self, select_admin_user):
        """Tests that the admin user, created in create_db.create_db was created correctly."""
        assert select_admin_user is not None
        assert select_admin_user.email == sttngs.SUPERUSER_EMAIL
        assert select_admin_user.handle == sttngs.SUPERUSER_HANDLE
        assert select_admin_user.full_name == sttngs.SUPERUSER_FULL_NAME
        assert select_admin_user.is_superuser is True
        assert select_admin_user.is_tenant_admin is False
        assert select_admin_user.is_active is True
        assert select_admin_user.is_deleted is False
        assert select_admin_user.created_at is not None
        assert select_admin_user.modified_at is not None
        assert select_admin_user.deleted_at is None

    def test_admin_user_graph(self, session, db_name, select_admin_user):
        """Tests that the graph vertext for the admin user was created correctly."""
        with session as session:
            session.execute(sa.text(set_role_admin(db_name=db_name)))
            stmt = sa.text(
                f"""
                SELECT * FROM cypher('graph', $$
                MATCH (u:User)
                WHERE (u.id = '{select_admin_user.id}')
                RETURN properties(u)
                $$) as (type agtype);
                """
            )
            admin_user_vertex = session.execute(stmt)
            properties = json.loads(admin_user_vertex.first()[0])
            assert properties["email"] == str(select_admin_user.email)
            assert properties["handle"] == str(select_admin_user.handle)
            assert properties["full_name"] == str(select_admin_user.full_name)
            assert (
                properties["is_superuser"]
                == str(select_admin_user.is_superuser).lower()
            )
            assert (
                properties["is_tenant_admin"]
                == str(select_admin_user.is_tenant_admin).lower()
            )
            assert properties["is_active"] == str(select_admin_user.is_active).lower()
            assert properties["is_deleted"] == str(select_admin_user.is_deleted).lower()
            _graph_created_at = datetime.datetime.strptime(
                properties["created_at"], "%Y-%m-%d %H:%M:%S.%f"
            ).replace(tzinfo=pytz.UTC)
            assert _graph_created_at == select_admin_user.created_at.replace(
                tzinfo=pytz.UTC
            )

            _graph_modified_at = datetime.datetime.strptime(
                properties["modified_at"], "%Y-%m-%d %H:%M:%S.%f"
            ).replace(tzinfo=pytz.UTC)
            assert _graph_modified_at == select_admin_user.modified_at.replace(
                tzinfo=pytz.UTC
            )
            with pytest.raises(KeyError):
                properties["deleted_at"]
        session.close()

    def test_super_user_select(
        self, session, db_name, mock_superuser_session_variables, populate_db
    ):
        """Tests that a user can be read by a superuserwith each of the db ROLEs."""
        for k, v in populate_db.items():
            for n, r in v.items():
                print(f"{k}: {n}: {r}")
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))

            # Test with admin role
            session.execute(sa.text(set_role_admin(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            stmt = sa.select(sa.func.count()).select_from(Tenant)
            tenant_count = session.execute(stmt)
            assert tenant_count.scalar() == 4

            stmt = sa.select(sa.func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4

            # Test with writer role
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            stmt = sa.select(sa.func.count()).select_from(Tenant)
            tenant_count = session.execute(stmt)
            assert tenant_count.scalar() == 4

            stmt = sa.select(sa.func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4

            # Test with reader role
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            stmt = sa.select(sa.func.count()).select_from(User)
            user_count = session.execute(stmt)
            assert user_count.scalar() == 20

            stmt = sa.select(sa.func.count()).select_from(Tenant)
            tenant_count = session.execute(stmt)
            assert tenant_count.scalar() == 4

            stmt = sa.select(sa.func.count()).select_from(Group)
            group_count = session.execute(stmt)
            assert group_count.scalar() == 4
        session.close()

    def test_reader_role_cannot_create_object(
        self, session, db_name, mock_superuser_session_variables
    ):
        """Tests that an object cannot be created by the reader role."""
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            un0tech = Tenant(name="un0.tech", tenant_type=TenantType.INDIVIDUAL)
            session.add(un0tech)
            with pytest.raises(sa.exc.ProgrammingError):
                session.commit()
        session.close()

    def test_writer_role_can_create_object(
        self, session, db_name, mock_superuser_session_variables
    ):
        """Tests that an object can be created by the writer role."""
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            un0tech = Tenant(name="un0.tech", tenant_type=TenantType.INDIVIDUAL)
            session.add(un0tech)
            assert session.commit() is None
        session.close()


'''

    def test_writer_role_can_create_object(
        self, session, db_name, mock_superuser_session_variables
    ):
        """Tests that an object cannot be created by the reader role."""
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            nacme = Tenant(name="Nacme Inc.", tenant_type=TenantType.CORPORATE)
            session.add(nacme)
            session.commit()
            stmt = sa.select(Tenant).filter_by(name="Nacme Inc.")
            result = session.scalars(stmt)
            nacme = result.first()
            assert nacme.name == "Nacme Inc."
            assert nacme.tenant_type == TenantType.CORPORATE
        session.close()

    def test_super_user_create_user(
        self, session, db_name, mock_superuser_session_variables
    ):
        """Tests that a user can be created by a superuser ."""
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            acme = Tenant(name="Acme Inc.", tenant_type=TenantType.ENTERPRISE)
            session.add(acme)
            result = session.commit()
            assert result is None

            stmt = sa.select(Tenant).filter_by(name="Acme Inc.")
            result = session.scalars(stmt)
            acme = result.first()

            acme_admin = User(
                email="admin@acme.com",
                handle="acme admin",
                full_name="ACME Admin",
                is_superuser=False,
                is_tenant_admin=True,
                is_active=True,
                is_deleted=False,
                tenant_id=acme.id,
            )
            session.add(acme_admin)
            result = session.commit()
            assert result is None
        session.close()


    def test_tenant_admin_user_create_user(
        self, session, db_name, mock_superuser_session_variables
    ):
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))
            session.execute(sa.text(set_role_reader(db_name=db_name)))
            stmt = sa.select(User).filter_by(email="admin@acme.com")
            result = session.scalars(stmt)
            acme_admin = result.first()

            stmt = sa.select(Tenant).filter_by(name="Nacme Inc.")
            result = session.scalars(stmt)
            nacme = result.first()
            assert nacme.id != acme_admin.tenant_id

            session.execute(
                sa.text(
                    mock_session_variables_for_user(
                        acme_admin.email,
                        acme_admin.is_superuser,
                        acme_admin.is_tenant_admin,
                        acme_admin.tenant_id,
                    )
                )
            )

            acme_user = User(
                email="user@acme.com",
                handle="acme user",
                full_name="ACME User",
                is_superuser=False,
                is_tenant_admin=False,
                tenant_id=nacme.id,
            )
            session.add(acme_user)
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            with pytest.raises(sa.exc.ProgrammingError):
                session.commit()

        with session as session:
            acme_user = User(
                email="user@acme.com",
                handle="acme user",
                full_name="ACME User",
                is_superuser=False,
                is_tenant_admin=False,
                tenant_id=acme_admin.tenant_id,
            )
            session.add(acme_user)
            result = session.commit()
            assert result is None

        session.close()


    def test_tenant_admin_user_create_user(self, session, db_name):
        """Tests that a user can be created by a tenant admin, but onlywith the same tenant_id."""
        with session as session:
            session.execute(sa.text(mock_superuser_session_variables))
            coyote = Tenant(
                name="Coyote LLC", tenant_type=TenantType.SMALL_BUSINESS
            )
            session.add(coyote)
            session.execute(sa.text(set_role_writer(db_name=db_name)))
            result = session.commit()
            assert result is None

        with session as session:
            stmt = sa.select(Tenant).filter_by(name="Coyote LLC")
            result = session.scalars(stmt)
            coyote = result.first()

        with session as session:
            coyote_admin = User(
                email="wiley@coyote.com",
                handle="coyote admin",
                full_name="Wiley Coyote",
                is_superuser=False,
                is_tenant_admin=True,
                tenant_id=coyote.id,
            )
            session.add(coyote_admin)
            result = session.commit()
            assert result is None

        with session as session:
            stmt = sa.select(User).filter_by(email="wiley@coyote.com")
            result = session.scalars(stmt)
            coyote_admin = result.first()

        assert coyote_admin is not None
        assert coyote_admin.tenant_id == coyote.id
        session.close()
'''
