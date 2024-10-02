# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore


@pytest.fixture(scope="session")
def db_name():
    return "un0_test_jwt"
