"""Load testing."""

from locust import HttpUser, task


class GalleryUser(HttpUser):

    @task
    def view_gallery(self):

        with self.client.get(
            "/photos",
            catch_response=True,
        ) as response:

            if response.status_code != 200:
                response.failure(
                    f"Expected 200, got {response.status_code}"
                )
