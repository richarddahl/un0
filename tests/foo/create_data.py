# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import csv
import random


def create_files() -> None:
    """
    Create the CSV files to be loaded into the tables
    """
    with open("tests/foo/data/baz.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "description"])
        for i in range(1, 101):
            writer.writerow([i, f"Baz {i}", f"Description {i}"])
    file.close()
    with open("tests/foo/data/bar.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "description", "primary_baz_id"])
        for i in range(1, 101):
            baz_id = random.randint(1, 10)
            writer.writerow([i, f"Bar {i}", f"Description {i}", baz_id])
    file.close()
    with open("tests/foo/data/foo.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "description", "bar_id"])
        for i in range(1, 1001):
            bar_id = random.randint(1, 100)
            writer.writerow([i, f"Foo {i}", f"Description {i}", bar_id])
    file.close()
    with open("tests/foo/data/foobaz.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["foo_id", "baz_id"])
        for i in range(1, 11):
            for baz_id in random.sample(range(1, 11), 5):
                writer.writerow([i, baz_id])
    file.close()
    with open("tests/foo/data/barbaz.csv", "w") as file:
        writer = csv.writer(file)
        writer.writerow(["bar_id", "baz_id"])
        for i in range(1, 11):
            for baz_id in random.sample(range(1, 11), 3):
                writer.writerow([i, baz_id])
    file.close()


if __name__ == "__main__":
    create_files()
