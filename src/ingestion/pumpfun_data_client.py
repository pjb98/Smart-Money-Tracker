"""
Pump.fun Historical Data Client
Fetches pre-migration metrics: volume, time on curve, wallet activity, etc.
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger


class PumpfunDataClient:
    """Client for fetching detailed Pump.fun token data"""

    def __init__(self, api_base: str = "https://frontend-api.pump.fun"):
        """
        Initialize Pump.fun data client

        Args:
            api_base: Base URL for Pump.fun API
        """
        self.api_base = api_base.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Initialized Pump.fun data client: {api_base}")

    async def _ensure_session(self):
        """Ensure HTTP session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_token_data(self, token_address: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive token data from Pump.fun

        Args:
            token_address: Token mint address

        Returns:
            Token data dict with bonding curve info
        """
        try:
            await self._ensure_session()

            url = f"{self.api_base}/coins/{token_address}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Fetched token data for {token_address[:8]}...")
                    return data
                else:
                    logger.warning(f"Failed to fetch token data: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching token data for {token_address}: {e}")
            return None

    async def get_token_trades(
        self,
        token_address: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get trade history for a token on Pump.fun bonding curve

        Args:
            token_address: Token mint address
            limit: Number of trades to fetch
            offset: Offset for pagination

        Returns:
            List of trade dicts
        """
        try:
            await self._ensure_session()

            url = f"{self.api_base}/trades/{token_address}"
            params = {
                "limit": limit,
                "offset": offset
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    trades = data if isinstance(data, list) else data.get('trades', [])
                    logger.debug(f"Fetched {len(trades)} trades for {token_address[:8]}...")
                    return trades
                else:
                    logger.warning(f"Failed to fetch trades: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trades for {token_address}: {e}")
            return []

    async def calculate_pre_migration_metrics(
        self,
        token_address: str,
        migration_time: datetime
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive pre-migration metrics for a token

        Args:
            token_address: Token mint address
            migration_time: When token migrated to Raydium

        Returns:
            Dict with pre-migration metrics
        """
        logger.info(f"Calculating pre-migration metrics for {token_address[:8]}...")

        # Fetch token data and trades
        token_data = await self.get_token_data(token_address)
        trades = await self.get_token_trades(token_address, limit=500)

        if not token_data:
            logger.warning("No token data available")
            return {}

        # Calculate metrics
        metrics = {}

        try:
            # 1. TIME ON BONDING CURVE
            created_timestamp = token_data.get('created_timestamp')
            if created_timestamp:
                created_time = datetime.fromtimestamp(created_timestamp / 1000)
                time_on_curve_seconds = (migration_time - created_time).total_seconds()
                metrics['time_on_bonding_curve_hours'] = time_on_curve_seconds / 3600
                metrics['time_on_bonding_curve_days'] = time_on_curve_seconds / 86400
            else:
                metrics['time_on_bonding_curve_hours'] = 0
                metrics['time_on_bonding_curve_days'] = 0

            # 2. VOLUME METRICS
            total_volume_sol = 0
            buy_volume_sol = 0
            sell_volume_sol = 0
            total_trades = len(trades)

            for trade in trades:
                sol_amount = trade.get('sol_amount', 0) / 1e9  # Convert lamports to SOL
                is_buy = trade.get('is_buy', True)

                total_volume_sol += sol_amount
                if is_buy:
                    buy_volume_sol += sol_amount
                else:
                    sell_volume_sol += sol_amount

            metrics['total_volume_pre_migration_sol'] = total_volume_sol
            metrics['buy_volume_pre_migration_sol'] = buy_volume_sol
            metrics['sell_volume_pre_migration_sol'] = sell_volume_sol
            metrics['total_trades_pre_migration'] = total_trades

            # 3. BUY/SELL RATIO
            buy_count = sum(1 for t in trades if t.get('is_buy', True))
            sell_count = total_trades - buy_count
            metrics['buy_count_pre_migration'] = buy_count
            metrics['sell_count_pre_migration'] = sell_count
            metrics['buy_sell_ratio'] = buy_count / sell_count if sell_count > 0 else 100

            # 4. UNIQUE WALLETS
            unique_wallets = set()
            unique_buyers = set()
            unique_sellers = set()

            for trade in trades:
                wallet = trade.get('user', trade.get('trader'))
                if wallet:
                    unique_wallets.add(wallet)
                    if trade.get('is_buy', True):
                        unique_buyers.add(wallet)
                    else:
                        unique_sellers.add(wallet)

            metrics['unique_wallets_pre_migration'] = len(unique_wallets)
            metrics['unique_buyers_pre_migration'] = len(unique_buyers)
            metrics['unique_sellers_pre_migration'] = len(unique_sellers)

            # 5. AVERAGE TRADE SIZE
            if total_trades > 0:
                metrics['avg_trade_size_sol'] = total_volume_sol / total_trades
                metrics['avg_buy_size_sol'] = buy_volume_sol / buy_count if buy_count > 0 else 0
                metrics['avg_sell_size_sol'] = sell_volume_sol / sell_count if sell_count > 0 else 0
            else:
                metrics['avg_trade_size_sol'] = 0
                metrics['avg_buy_size_sol'] = 0
                metrics['avg_sell_size_sol'] = 0

            # 6. VELOCITY METRICS (trades per hour)
            if metrics['time_on_bonding_curve_hours'] > 0:
                metrics['trades_per_hour'] = total_trades / metrics['time_on_bonding_curve_hours']
                metrics['volume_per_hour_sol'] = total_volume_sol / metrics['time_on_bonding_curve_hours']
            else:
                metrics['trades_per_hour'] = 0
                metrics['volume_per_hour_sol'] = 0

            # 7. MARKET CAP AT MIGRATION
            metrics['market_cap_usd'] = token_data.get('usd_market_cap', 0)
            metrics['market_cap_sol'] = token_data.get('market_cap', 0) / 1e9

            # 8. BONDING CURVE PROGRESS
            virtual_sol_reserves = token_data.get('virtual_sol_reserves', 0) / 1e9
            virtual_token_reserves = token_data.get('virtual_token_reserves', 0) / 1e6
            metrics['bonding_curve_progress_pct'] = token_data.get('complete', 0) * 100

            # 9. PRICE METRICS
            metrics['price_at_migration_sol'] = token_data.get('vir sol_reserves', 0) / 1e9 if virtual_token_reserves > 0 else 0

            # 10. HOLDER METRICS (if available)
            metrics['holder_count'] = token_data.get('holder_count', 0)

            # 11. SOCIAL METRICS (if available)
            metrics['telegram_members'] = token_data.get('telegram', {}).get('member_count', 0)
            metrics['twitter_followers'] = token_data.get('twitter', {}).get('follower_count', 0)

            logger.info(f"Calculated {len(metrics)} pre-migration metrics")

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")

        return metrics


# Example usage
async def example():
    """Test the client"""
    client = PumpfunDataClient()

    # Example token address
    token = "ExampleTokenAddress"
    migration_time = datetime.now()

    metrics = await client.calculate_pre_migration_metrics(token, migration_time)

    print(json.dumps(metrics, indent=2))

    await client.close()


if __name__ == "__main__":
    import json
    asyncio.run(example())
