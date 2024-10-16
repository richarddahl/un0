# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import datetime
import decimal

import asyncio
import pytest

# #from un0.db.base_definition import un0DB  # type: ignore

from un0.config import settings  # type: ignore


pytest_plugins = ("pytest_asyncio",)


"""
@pytest.mark.asyncio
async def test_db_init():
    assert 1 == 1


@pytest.mark.asyncio
async def test_group_db_init():
    db = UnoDB(f"{settings.DB_SCHEMA}.group")
    assert db.table_name == f"{settings.DB_SCHEMA}.group"
    assert db.pk_fields == ["id"]
"""
