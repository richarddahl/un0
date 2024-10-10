# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest  # type: ignore
import jwt

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError

from un0.auth.models import User
from un0.config import settings as sttngs

from tests.conftest import mock_rls_vars


class TestFltr:
    def test_create_fields(self, session):
        assert True
