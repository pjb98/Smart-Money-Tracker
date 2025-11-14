"""
Pumpfun API client for fetching token migration events and metadata
"""
import aiohttp
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import json


class PumpfunClient:
    """Client for interacting with Pumpfun API"""

    def __init__(
        self,
        api_url: str = "https://api.pumpfun.io",
        api_key: Optional[str] = None,
        rate_limit_delay: float = 1.0
    ):
        """
        Initialize Pumpfun API client

        Args:
            api_url: Pumpfun API base URL
            api_key: API key (if required)
            rate_limit_delay: Delay between requests
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Initialized Pumpfun client with URL: {api_url}")

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request to Pumpfun API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data

        Returns:
            Response data or None
        """
        await self._ensure_session()

        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        try:
            async with self.session.request(
                method,
                url,
                params=params,
                json=json_data
            ) as response:
                await asyncio.sleep(self.rate_limit_delay)

                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    logger.warning(f"Endpoint not found: {url}")
                    return None
                else:
                    logger.error(f"API request failed: {response.status} - {await response.text()}")
                    return None

        except Exception as e:
            logger.error(f"Error making request to {url}: {e}")
            return None

    async def get_migrations(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch token migration events

        Args:
            since: Fetch migrations since this datetime
            limit: Maximum number of migrations to fetch

        Returns:
            List of migration event dicts
        """
        params = {"limit": limit}
        if since:
            params["since"] = since.isoformat()

        response = await self._request("GET", "/api/v1/migrations", params=params)

        if response and isinstance(response, list):
            logger.info(f"Fetched {len(response)} migrations")
            return response
        elif response and "migrations" in response:
            migrations = response["migrations"]
            logger.info(f"Fetched {len(migrations)} migrations")
            return migrations

        logger.warning("No migrations found or API structure changed")
        return []

    async def get_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed token information

        Args:
            token_address: Token mint address

        Returns:
            Token info dict or None
        """
        response = await self._request("GET", f"/api/v1/tokens/{token_address}")

        if response:
            logger.debug(f"Fetched info for token {token_address}")
            return response

        return None

    async def get_token_metadata(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch token metadata (name, symbol, description, etc.)

        Args:
            token_address: Token mint address

        Returns:
            Token metadata dict or None
        """
        response = await self._request("GET", f"/api/v1/tokens/{token_address}/metadata")

        if response:
            return response

        return None

    async def get_migration_timeline(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch migration timeline for a token

        Args:
            token_address: Token mint address

        Returns:
            Timeline dict with key events or None
        """
        response = await self._request("GET", f"/api/v1/tokens/{token_address}/timeline")

        if response:
            return response

        return None

    async def search_tokens(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for tokens by name or symbol

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching tokens
        """
        params = {"q": query, "limit": limit}
        response = await self._request("GET", "/api/v1/tokens/search", params=params)

        if response and isinstance(response, list):
            return response
        elif response and "results" in response:
            return response["results"]

        return []

    async def get_trending_tokens(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch trending tokens on Pumpfun

        Args:
            limit: Maximum number of tokens

        Returns:
            List of trending token dicts
        """
        params = {"limit": limit}
        response = await self._request("GET", "/api/v1/tokens/trending", params=params)

        if response and isinstance(response, list):
            return response
        elif response and "tokens" in response:
            return response["tokens"]

        return []


class MockPumpfunClient(PumpfunClient):
    """
    Mock Pumpfun client for testing when API is unavailable
    Generates synthetic migration events
    """

    def __init__(self):
        super().__init__(api_url="http://mock.pumpfun.io")
        logger.info("Initialized MOCK Pumpfun client")

    async def get_migrations(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Generate mock migration events"""

        # Generate mock data
        mock_migrations = []
        base_time = since or datetime.now() - timedelta(days=7)

        for i in range(min(limit, 10)):
            migration_time = base_time + timedelta(hours=i * 12)
            mock_migrations.append({
                "token_address": f"MOCK{i}{'x' * 30}{i}",
                "migration_time": migration_time.isoformat(),
                "pre_migration_rank": i + 1,
                "initial_liquidity_sol": 5 + i * 0.5,
                "pool_address": f"POOL{i}{'y' * 30}{i}",
                "status": "completed"
            })

        logger.info(f"Generated {len(mock_migrations)} mock migrations")
        return mock_migrations

    async def get_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Generate mock token info"""
        return {
            "address": token_address,
            "name": f"Mock Token {token_address[:8]}",
            "symbol": f"MOCK{token_address[:4]}",
            "decimals": 9,
            "supply": 1000000000,
            "created_at": (datetime.now() - timedelta(days=30)).isoformat()
        }


# Example usage
async def main():
    # Use mock client for testing
    client = MockPumpfunClient()

    # Get recent migrations
    migrations = await client.get_migrations(limit=5)
    print(f"Found {len(migrations)} migrations:")
    for m in migrations:
        print(f"  - {m['token_address']} at {m['migration_time']}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
