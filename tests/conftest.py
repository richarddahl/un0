# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime
import pytest
import jwt

from typing import Any

from un0.config import settings as sttngs


# Not a pytest.fixture as need to call it with various parameters for testing
def mock_session_variables_for_user(
    email, is_superuser, is_customer_admin, customer_id
):
    """Mocks the session variables for a user."""
    return f"""
        SELECT SET_CONFIG('s_var.user_email', '{email}', true);
        SELECT SET_CONFIG('s_var.is_superuser', '{is_superuser}', true);
        SELECT SET_CONFIG('s_var.is_customer_admin', '{is_customer_admin}', true);
        SELECT SET_CONFIG('s_var.customer_id', '{customer_id}', true);
    """


# Fixtures start here
@pytest.fixture
def mock_superuser_session_variables():
    """Mocks the session variables for a superuser."""
    return f"""
        SELECT SET_CONFIG('s_var.user_email', '{sttngs.SUPERUSER_EMAIL}', true);
        SELECT SET_CONFIG('s_var.is_superuser', 'true', true);
        SELECT SET_CONFIG('s_var.is_customer_admin', 'false', true);
        SELECT SET_CONFIG('s_var.customer_id', '', true);
    """
