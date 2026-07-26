from locust import HttpUser, task


class GalleryUser(HttpUser):
    """
    Simulated user that repeatedly requests the photo gallery page.
    """

    @task
    def view_gallery(self):
        """
        Request the gallery page and mark the sample as failed if the
        response status is not 200.

        Returns
        -------
        None
        """

        with self.client.get(
            "/photos",
            catch_response=True,
        ) as response:

            if response.status_code != 200:
                response.failure(
                    f"Expected 200, got {response.status_code}"
                )
