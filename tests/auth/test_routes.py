# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest

from sqlalchemy import func, select, update, delete
from sqlalchemy.exc import ProgrammingError

from fastapi.testclient import TestClient

from un0.db.tools.db_tool import DBTool
from un0.auth.tables import User
from un0.auth.models import UserObj
from un0.config import settings as sttngs
from un0.main import app

from tests.pgjwt.test_pgjwt import encode_test_token

client = TestClient(app)


def test_user_list_route():
    response = client.get(
        "/api/auth/users",
        headers={"X_Token": encode_test_token()},
    )
    assert response.status_code == 200
