from locust import HttpUser
from locust import between
from locust import constant
from locust import task

from tests.performance.config import config


class EvaUser(HttpUser):
    """
    Simulates a user interacting with the EVA service.
    """

    wait_time = between(config.WAIT_TIME_MIN, config.WAIT_TIME_MAX)
    host = config.DEFAULT_HOST

    @task(3)
    def healthcheck(self) -> None:
        """
        Check the health of the service.
        Higher weight (3) means this task is executed more often.
        """
        self.client.get("/common/healthcheck", name="Healthcheck")

    @task(1)
    def root(self) -> None:
        """
        Visit the root endpoint.
        """
        self.client.get("/common/", name="Root")

    @task(2)
    def search(self) -> None:
        """
        Perform a search query.
        """
        # In a real scenario, you might want to randomize the query
        self.client.post(
            "/v1/answer/generate",
            json={"query": "test"},
            name="Search",
        )


class EvaStressUser(EvaUser):
    """
    Stress test user with no wait time to maximize RPS.
    """

    wait_time = constant(0)
