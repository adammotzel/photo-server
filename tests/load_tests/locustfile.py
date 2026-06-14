"""Load testing."""

import csv
import random

from locust import HttpUser, task


with open("tests/load_tests/data/users.csv") as f:
    USERS = list(csv.DictReader(f))


class LoginUser(HttpUser):

    def on_start(self):
        user = random.choice(USERS)

        self.username = user["username"]
        self.password = user["password"]

    @task
    def login(self):

        with self.client.post(
            "/login",
            data={
                "name": self.username,
                "password": self.password,
            },
            allow_redirects=False,
            catch_response=True,
        ) as response:

            if response.status_code != 302:
                response.failure(
                    f"Expected 302, got {response.status_code}"
                )
                