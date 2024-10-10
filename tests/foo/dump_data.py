# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import os


def dump_data() -> None:
    """ """
    os.system(
        "pg_dump -d un0_test_foo --data-only --table=un0.testbaz --table=un0.testbar --table=un0.testfoo --table=un0.testfoo_baz --table=un0.testbar_baz > tests/foo/data/foo.sql"
    )


if __name__ == "__main__":
    dump_data()
