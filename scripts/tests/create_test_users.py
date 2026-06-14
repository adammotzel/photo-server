"""Seed test users in the `photoapp_test` db for load testing."""

import csv
import os

import psycopg
from argon2 import PasswordHasher
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photoapp_test",
    "user": "photoapp_user",
    "password": os.getenv("POSTGRES_PW")
}

NUM_USERS = 1000
TEST_PASSWORD = os.getenv("TEST_PW")

# same password for all test users
ph = PasswordHasher()
password_hash = ph.hash(TEST_PASSWORD)


def main():

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            for i in range(NUM_USERS):
                username = f"locust_user_{i:05d}"

                cur.execute(
                    """
                    INSERT INTO users (
                        username,
                        password_hash
                    )
                    VALUES (%s, %s)
                    ON CONFLICT (username) DO NOTHING
                    """,
                    (
                        username,
                        password_hash,
                    ),
                )

                if i % 100 == 0:
                    print(f"Created {i} users")

        conn.commit()

    print(f"Finished creating {NUM_USERS} users")

    # write test users to csv for easy loading
    with open("tests/load_tests/data/users.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "password"])
        for i in range(NUM_USERS):
            writer.writerow(
                [
                    f"locust_user_{i:05d}",
                    TEST_PASSWORD,
                ]
            )

    print("Users stored in tests/load_tests/data/users.csv")


if __name__ == "__main__":
    main()
    