# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from fastapi import HTTPException, status


class Un0Error(Exception):
    message: str
    error_code: str

    def __init__(self, message, error_code):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class Un0ModelConfigError(Un0Error):
    pass


class Un0ModelRegistryError(Un0Error):
    pass


class Un0ModelFieldListError(Un0Error):
    pass


class Un0ModelRelationConfigError(Un0Error):
    pass


class Un0ModelTableError(Un0Error):
    pass


class Un0HTTPError(HTTPException):
    status_code = 400
    detail = "Record matching data already exists in database."


class DataExistsError(HTTPException):
    status_code = 400
    detail = "Record matching data already exists in database."


class UnauthorizedError(HTTPException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Invalid user credentials"
    headers = {"WWW-enticate": "Bearer"}


class ForbiddenError(HTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to access this resource."
