# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

import sqlalchemy as sa

from un0.cmd.sql import set_role_reader
from un0.cmd import create_db, drop_db

from tests.pgjwt.conftest import encode_test_token


class TestVerifyJWTAndSetVars:
    @classmethod
    def setup_class(cls, db_name="un0_test_jwt"):
        drop_db.drop(db_name=db_name)
        create_db.create(db_name=db_name)

    def test_valid_jwt(self, session, db_name):
        """Tests that a valid JWT token can be verified and the session variables set."""
        token = encode_test_token()
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            result = session.execute(
                sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
            )
            assert result.scalars().first() is True

            result = session.execute(
                sa.text("SELECT * FROM un0.list_session_variables();")
            )
            session_variables = result.scalars().first()
            assert session_variables.get("user_email") != ""
            assert session_variables.get("user_id") != ""
            assert session_variables.get("is_superuser") == "true"
            assert session_variables.get("is_tenant_admin") == "false"
            assert session_variables.get("tenant_id") == ""

    def test_expired_jwt(self, session, db_name):
        """Tests that an expired JWT token cannot be authorized."""
        token = encode_test_token(is_expired=True)
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(
                    sa.text(
                        f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);"
                    )
                )
            assert "invalid token" in str(excinfo.value)

    def test_invalid_secret_jwt(self, session, db_name):
        """Tests that a JWT token with an invalid secret cannot be authorized."""
        token = encode_test_token(invalid_secret=True)
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(
                    sa.text(
                        f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);"
                    )
                )
            assert "invalid token" in str(excinfo.value)

    def test_invalid_sub_jwt(self, session, db_name):
        """Tests that a JWT token with an invalid sub cannot be authorized."""
        token = encode_test_token(email="richard@dahl.us")
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(
                    sa.text(
                        f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);"
                    )
                )
            assert "user not found" in str(excinfo.value)

    def test_no_sub_jwt(self, session, db_name):
        """Tests that a JWT token without a sub cannot be authorized."""
        token = encode_test_token(has_sub=False)
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(
                    sa.text(
                        f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);"
                    )
                )
            assert "token does not contain a sub" in str(excinfo.value)

    def test_no_exp_jwt(self, session, db_name):
        """Tests that a JWT token without an expiration cannot be authorized."""
        token = encode_test_token(has_exp=False)
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(
                    sa.text(
                        f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);"
                    )
                )
            assert "token has no expiration" in str(excinfo.value)

    def test_inactive_user_jwt(self, session, db_name, load_inactive_user):
        """Tests that an inactive user cannot be authorized."""
        token = encode_test_token(email="inactive@user.com")
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(
                    sa.text(
                        f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);"
                    )
                )
            assert "user is not active" in str(excinfo.value)

    def test_deleted_user_jwt(self, session, db_name, load_deleted_user):
        """Tests that a deleted user cannot be authorized."""
        token = encode_test_token(email="deleted@user.com")
        with session as session:
            session.execute(sa.text(set_role_reader(db_name)))
            with pytest.raises(sa.exc.ProgrammingError) as excinfo:
                session.execute(
                    sa.text(
                        f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);"
                    )
                )
            assert "user was deleted" in str(excinfo.value)
