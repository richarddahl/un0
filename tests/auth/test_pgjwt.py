# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

import sqlalchemy as sa

from tests.conftest import encode_token, SET_ROLE_READER_STATEMENT


@pytest.mark.asyncio
async def test_valid_jwt(async_session):
    """Tests that a valid JWT token can be verified and the session variables set."""
    token = encode_token()
    async with async_session() as session:
        await session.execute(sa.text(SET_ROLE_READER_STATEMENT))
        result = await session.execute(
            sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
        )
        assert result.scalars().first() is True

        result = await session.execute(
            sa.text("SELECT * FROM un0.list_session_variables();")
        )
        session_variables = result.scalars().first()
        assert session_variables.get("user_email") != ""
        assert session_variables.get("is_superuser") == "true"
        assert session_variables.get("is_customer_admin") == "false"
        assert session_variables.get("customer_id") == ""


@pytest.mark.asyncio
async def test_expired_jwt(async_session):
    token = encode_token(is_expired=True)
    async with async_session() as session:
        await session.execute(sa.text(SET_ROLE_READER_STATEMENT))
        with pytest.raises(sa.exc.ProgrammingError) as excinfo:
            await session.execute(
                sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
            )
        assert "invalid token" in str(excinfo.value)


@pytest.mark.asyncio
async def test_inv_sec_jwt(async_session):
    token = encode_token(inv_sec=True)
    async with async_session() as session:
        await session.execute(sa.text(SET_ROLE_READER_STATEMENT))
        with pytest.raises(sa.exc.ProgrammingError) as excinfo:
            await session.execute(
                sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
            )
        assert "invalid token" in str(excinfo.value)


@pytest.mark.asyncio
async def test_invalid_sub_jwt(async_session):
    token = encode_token(email="richard@dahl.us")
    async with async_session() as session:
        await session.execute(sa.text(SET_ROLE_READER_STATEMENT))
        with pytest.raises(sa.exc.ProgrammingError) as excinfo:
            await session.execute(
                sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
            )
        assert "user not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_no_sub_jwt(async_session):
    token = encode_token(has_sub=False)
    async with async_session() as session:
        await session.execute(sa.text(SET_ROLE_READER_STATEMENT))
        with pytest.raises(sa.exc.ProgrammingError) as excinfo:
            await session.execute(
                sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
            )
        assert "token does not contain a sub" in str(excinfo.value)


@pytest.mark.asyncio
async def test_no_exp_jwt(async_session):
    token = encode_token(has_exp=False)
    async with async_session() as session:
        await session.execute(sa.text(SET_ROLE_READER_STATEMENT))
        with pytest.raises(sa.exc.ProgrammingError) as excinfo:
            await session.execute(
                sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
            )
        assert "token has no expiration" in str(excinfo.value)
