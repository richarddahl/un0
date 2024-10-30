# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from decimal import Decimal
from typing import Annotated

from sqlalchemy.dialects.postgresql import VARCHAR

str_26 = Annotated[VARCHAR, 26]
str_64 = Annotated[VARCHAR, 64]
str_128 = Annotated[VARCHAR, 128]
str_255 = Annotated[VARCHAR, 255]
decimal = Annotated[Decimal, 19]
