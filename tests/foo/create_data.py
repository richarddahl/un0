# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import csv


def create_files() -> None:
    """
    Create the CSV files to be loaded into the tables
    """
    with open("data/foo.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "description", "bar_id"])
        for i in range(1, 1000001):
            writer.writerow([i, f"Foo {i}", f"Description {i}", i])
    file.close()
    with open("data/bar.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "description", "primary_baz_id"])
        for i in range(1, 1000001):
            writer.writerow([i, f"Bar {i}", f"Description {i}", i])
    file.close()
    with open("data/baz.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "description"])
        for i in range(1, 1000001):
            writer.writerow([i, f"Baz {i}", f"Description {i}"])
    file.close()


if __name__ == "__main__":
    create_files()
