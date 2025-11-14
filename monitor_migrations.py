"""
Live monitoring script for Pump.fun → Raydium token migrations
Automatically detects and analyzes new tokens
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
import json

from config import settings, setup_directories
from src.utils.logger import setup_logger
from main import PumpfunAgent


class RaydiumMigrationMonitor:
    """Monitor Raydium for new token migrations from Pump.fun"""

    def __init__(self, check_interval_seconds: int = 60):
        """
        Initialize migration monitor

        Args:
            check_interval_seconds: How often to check for new tokens (default 60s)
        """
        self.check_interval = check_interval_seconds
        self.seen_tokens = set()
        self.dexscreener_api = "https://api.dexscreener.com/latest/dex"
        self.logger = setup_logger(settings.log_file, settings.log_level)

        # Load previously seen tokens
        self._load_seen_tokens()

    def _load_seen_tokens(self):
        """Load previously seen tokens from disk"""
        seen_file = Path("data/seen_tokens.json")
        if seen_file.exists():
            try:
                with open(seen_file, 'r') as f:
                    data = json.load(f)
                    self.seen_tokens = set(data.get('tokens', []))
                self.logger.info(f"Loaded {len(self.seen_tokens)} previously seen tokens")
            except Exception as e:
                self.logger.error(f"Error loading seen tokens: {e}")

    def _save_seen_tokens(self):
        """Save seen tokens to disk"""
        seen_file = Path("data/seen_tokens.json")
        seen_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(seen_file, 'w') as f:
                json.dump({
                    'tokens': list(self.seen_tokens),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving seen tokens: {e}")

    async def fetch_new_raydium_pairs(self) -> list:
        """
        Fetch new Raydium pairs from DexScreener

        Returns:
            List of new token pairs
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get latest pairs using search endpoint (token profiles)
                # DexScreener has different endpoints - using token profiles for latest
                url = f"{self.dexscreener_api}/token-profiles/latest/v1"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Filter for Solana tokens only
                        all_tokens = data if isinstance(data, list) else []
                        solana_tokens = [
                            t for t in all_tokens
                            if t.get('chainId') == 'solana'
                        ]

                        self.logger.info(f"Found {len(solana_tokens)} recent Solana tokens")
                        return solana_tokens
                    else:
                        self.logger.error(f"DexScreener API error: {response.status}")
                        # Fallback: try alternative endpoint
                        return await self._fetch_from_alternative_source(session)

        except Exception as e:
            self.logger.error(f"Error fetching pairs from DexScreener: {e}")
            return []

    async def _fetch_from_alternative_source(self, session) -> list:
        """Fallback: Fetch from Birdeye or other source"""
        try:
            # Use Birdeye API as fallback (free tier available)
            url = "https://public-api.birdeye.so/defi/tokenlist?sort_by=v24hChangePercent&sort_type=desc&offset=0&limit=50"

            async with session.get(url, headers={"X-API-KEY": "public"}) as response:
                if response.status == 200:
                    data = await response.json()
                    tokens = data.get('data', {}).get('tokens', [])
                    self.logger.info(f"Fetched {len(tokens)} tokens from Birdeye fallback")
                    return tokens

        except Exception as e:
            self.logger.error(f"Fallback source also failed: {e}")

        return []

    async def is_pump_fun_token(self, pair: dict) -> bool:
        """
        Check if a token is from Pump.fun

        Args:
            pair: Token pair data from DexScreener

        Returns:
            True if token is from Pump.fun
        """
        # Heuristics to identify Pump.fun tokens:
        # 1. Created recently (< 7 days)
        # 2. Low initial market cap
        # 3. High initial trading volume spike
        # 4. Specific liquidity patterns

        try:
            created_at = pair.get('pairCreatedAt')
            if created_at:
                created_time = datetime.fromtimestamp(created_at / 1000)
                age_days = (datetime.now() - created_time).days

                # Focus on very recent tokens (< 1 hour for fresh migrations)
                if age_days == 0:
                    age_hours = (datetime.now() - created_time).seconds / 3600
                    if age_hours < 24:  # Less than 24 hours old
                        self.logger.debug(f"Found recent token: {pair.get('baseToken', {}).get('symbol')} ({age_hours:.1f}h old)")
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking if Pump.fun token: {e}")
            return False

    async def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info(f"🚀 Starting Raydium migration monitor (checking every {self.check_interval}s)")
        self.logger.info("Monitoring for Pump.fun → Raydium migrations...")

        # Initialize agent
        agent = PumpfunAgent(use_mock_data=False)

        try:
            while True:
                self.logger.info("=" * 60)
                self.logger.info(f"Checking for new migrations... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

                # Fetch new pairs
                pairs = await self.fetch_new_raydium_pairs()

                new_migrations = []

                for pair in pairs:
                    token_address = pair.get('baseToken', {}).get('address')

                    if not token_address or token_address in self.seen_tokens:
                        continue

                    # Check if it's a Pump.fun token
                    if await self.is_pump_fun_token(pair):
                        new_migrations.append(pair)
                        self.seen_tokens.add(token_address)
                        self.logger.info(f"✨ NEW MIGRATION: {pair.get('baseToken', {}).get('symbol')} ({token_address[:8]}...)")

                # Process new migrations
                if new_migrations:
                    self.logger.info(f"Found {len(new_migrations)} new migrations to analyze")

                    for pair in new_migrations:
                        token_address = pair.get('baseToken', {}).get('address')
                        symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')

                        self.logger.info(f"🔍 Analyzing {symbol} ({token_address[:8]}...)")

                        # Create migration event
                        migration_event = {
                            'token_address': token_address,
                            'migration_time': datetime.now().isoformat(),
                            'initial_liquidity_sol': pair.get('liquidity', {}).get('usd', 0) / 200,  # Rough estimate
                            'pool_address': pair.get('pairAddress', ''),
                            'symbol': symbol,
                            'price_usd': pair.get('priceUsd', 0),
                            'market_cap': pair.get('fdv', 0),
                            'volume_24h': pair.get('volume', {}).get('h24', 0),
                            'price_change_24h': pair.get('priceChange', {}).get('h24', 0)
                        }

                        # Analyze the token
                        try:
                            result = await agent.process_migration(migration_event)

                            # Save result
                            agent._save_result(result)

                            # Log Claude's recommendation
                            if result.get('claude_analysis'):
                                recommendation = result['claude_analysis'].get('recommendation', 'UNKNOWN')
                                confidence = result['claude_analysis'].get('confidence', 'UNKNOWN')
                                risk_score = result['claude_analysis'].get('risk_score', 0)

                                self.logger.info(f"📊 Analysis complete for {symbol}:")
                                self.logger.info(f"   Recommendation: {recommendation} (Confidence: {confidence})")
                                self.logger.info(f"   Risk Score: {risk_score}/10")

                                # Generate alert if HIGH confidence BUY
                                if recommendation == 'BUY' and confidence == 'HIGH':
                                    self.logger.warning(f"🚨 HIGH CONFIDENCE BUY SIGNAL: {symbol} ({token_address})")
                                    # You can add Discord/Telegram alerts here

                        except Exception as e:
                            self.logger.error(f"Error analyzing {symbol}: {e}")

                        # Small delay between tokens
                        await asyncio.sleep(5)

                    # Save seen tokens
                    self._save_seen_tokens()
                else:
                    self.logger.info("No new migrations found")

                # Wait before next check
                self.logger.info(f"Waiting {self.check_interval}s before next check...")
                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Monitor stopped by user")
        finally:
            await agent.close()
            self._save_seen_tokens()


async def main():
    """Main entry point"""
    setup_directories()

    # Create monitor (check every 60 seconds)
    monitor = RaydiumMigrationMonitor(check_interval_seconds=60)

    # Start monitoring
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())
