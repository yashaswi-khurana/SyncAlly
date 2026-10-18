import asyncio
import unittest

import httpx

from syncally.api.main import app


class HealthRouteTests(unittest.TestCase):
    def test_health_route_reports_api_process_is_responding(self) -> None:
        async def get_health() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.get("/health")

        response = asyncio.run(get_health())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
