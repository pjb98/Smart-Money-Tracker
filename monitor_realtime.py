"""
REAL-TIME Pump.fun → Raydium Migration Monitor
Uses PumpPortal WebSocket for instant migration detection (no polling!)
"""
import asyncio
from datetime import datetime
from loguru import logger
from pathlib import Path
import json

from config import settings, setup_directories
from src.utils.logger import setup_logger
from src.utils.trading_mode import TradingMode, get_mode_manager
from src.ingestion.pumpportal_client import PumpPortalClient
from src.ingestion.pumpfun_data_client import PumpfunDataClient
from src.ingestion.birdeye_client import BirdeyeClient
from src.ingestion.twitter_analyzer import TwitterAnalyzer
from main import PumpfunAgent


class RealtimeMigrationMonitor:
    """Real-time monitor using PumpPortal WebSocket"""

    def __init__(self):
        """Initialize real-time monitor"""
        self.logger = setup_logger(settings.log_file, settings.log_level)
        self.mode_manager = get_mode_manager()
        self.agent = None
        self.pumpportal = PumpPortalClient()
        self.pumpfun_data = PumpfunDataClient()  # Fetch pre-migration metrics
        self.birdeye = BirdeyeClient(api_key=settings.birdeye_api_key)  # Wallet intelligence
        self.twitter_analyzer = TwitterAnalyzer(bearer_token=settings.twitter_bearer_token)  # Twitter analysis
        self.seen_migrations = set()
        self._load_seen_migrations()

    def _load_seen_migrations(self):
        """Load previously seen migrations"""
        seen_file = Path("data/seen_migrations.json")
        if seen_file.exists():
            try:
                with open(seen_file, 'r') as f:
                    data = json.load(f)
                    self.seen_migrations = set(data.get('migrations', []))
                self.logger.info(f"Loaded {len(self.seen_migrations)} previously seen migrations")
            except Exception as e:
                self.logger.error(f"Error loading seen migrations: {e}")

    def _save_seen_migrations(self):
        """Save seen migrations"""
        seen_file = Path("data/seen_migrations.json")
        seen_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(seen_file, 'w') as f:
                json.dump({
                    'migrations': list(self.seen_migrations),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving seen migrations: {e}")

    async def handle_migration(self, event: dict):
        """
        Handle migration event from PumpPortal

        Args:
            event: Migration event data from WebSocket
        """
        try:
            # Check if system is active
            if not self.mode_manager.is_active():
                self.logger.debug("System is not active, skipping migration")
                return

            # Check if analysis is allowed
            if not self.mode_manager.can_analyze():
                self.logger.debug("Analysis not allowed in current mode")
                return

            self.logger.info("=" * 70)
            self.logger.info("MIGRATION EVENT RECEIVED")
            self.logger.info("=" * 70)

            # Log full event for debugging - CRITICAL for understanding data structure
            self.logger.info(f"FULL MIGRATION DATA: {json.dumps(event, indent=2, default=str)}")

            # Extract token address (adjust field names based on actual API response)
            token_address = (
                event.get('mint') or
                event.get('tokenAddress') or
                event.get('token') or
                event.get('signature')  # Fallback to signature if no token address
            )

            if not token_address:
                self.logger.warning("No token address in migration event")
                self.logger.debug(f"Event keys: {list(event.keys())}")
                return

            # Skip if already processed
            if token_address in self.seen_migrations:
                self.logger.debug(f"Already processed migration for {token_address[:8]}...")
                return

            self.seen_migrations.add(token_address)

            # Extract metadata
            symbol = event.get('symbol', 'UNKNOWN')
            name = event.get('name', event.get('tokenName', 'Unknown Token'))
            signature = event.get('signature', '')

            self.logger.info(f"✨ NEW MIGRATION: {name} ({symbol})")
            self.logger.info(f"   Token: {token_address}")
            self.logger.info(f"   Signature: {signature}")

            # FETCH PRE-MIGRATION METRICS FROM PUMP.FUN
            self.logger.info(f"Fetching pre-migration metrics from Pump.fun...")
            migration_datetime = datetime.now()
            pre_migration_metrics = await self.pumpfun_data.calculate_pre_migration_metrics(
                token_address,
                migration_datetime
            )

            self.logger.info(f"Fetched {len(pre_migration_metrics)} pre-migration metrics:")
            self.logger.info(f"  - Time on bonding curve: {pre_migration_metrics.get('time_on_bonding_curve_hours', 0):.2f}h")
            self.logger.info(f"  - Total volume: {pre_migration_metrics.get('total_volume_pre_migration_sol', 0):.2f} SOL")
            self.logger.info(f"  - Unique wallets: {pre_migration_metrics.get('unique_wallets_pre_migration', 0)}")
            self.logger.info(f"  - Buy/Sell ratio: {pre_migration_metrics.get('buy_sell_ratio', 0):.2f}")

            # FETCH WALLET INTELLIGENCE FROM BIRDEYE
            self.logger.info(f"Analyzing wallet intelligence (whales, profitable wallets, insiders)...")
            wallet_intelligence = await self.birdeye.analyze_wallet_intelligence(
                token_address,
                top_n_holders=50  # Analyze top 50 holders
            )

            self.logger.info(f"Wallet Intelligence Results:")
            self.logger.info(f"  - Whale wallets: {wallet_intelligence.get('whale_count', 0)}")
            self.logger.info(f"  - Whale ownership: {wallet_intelligence.get('whale_total_percentage', 0):.2f}%")
            self.logger.info(f"  - Highly profitable wallets: {len(wallet_intelligence.get('highly_profitable_wallets', []))}")
            self.logger.info(f"  - Potential insider wallets: {len(wallet_intelligence.get('insider_wallets', []))}")
            self.logger.info(f"  - Insider risk score: {wallet_intelligence.get('insider_risk_score', 0)}/10")

            # ANALYZE TWITTER ACCOUNT (if available)
            twitter_account_analysis = None
            # Try to get token data from Pump.fun to extract social links
            token_data = await self.pumpfun_data.get_token_data(token_address)
            if token_data and ('twitter' in token_data or 'x' in token_data):
                self.logger.info(f"Analyzing Twitter account for social legitimacy...")
                try:
                    username = self.twitter_analyzer.extract_twitter_handle(token_data)
                    if username:
                        twitter_account_analysis = await self.twitter_analyzer.comprehensive_analysis(username, token_data)
                        self.logger.info(f"Twitter Analysis Results:")
                        self.logger.info(f"  - Account: @{username}")
                        self.logger.info(f"  - Risk Score: {twitter_account_analysis.get('risk_score', 'N/A')}/10 ({twitter_account_analysis.get('risk_level', 'UNKNOWN')})")
                        if twitter_account_analysis.get('insights'):
                            for insight in twitter_account_analysis['insights'][:3]:  # Show top 3 insights
                                self.logger.info(f"    {insight}")
                    else:
                        self.logger.debug("Could not extract Twitter handle from token data")
                except Exception as e:
                    self.logger.warning(f"Twitter analysis failed: {e}")
            else:
                self.logger.debug("No Twitter account linked to token")

            # Build migration event for agent with PRE-MIGRATION DATA + WALLET INTELLIGENCE + TWITTER ANALYSIS
            migration_event = {
                'token_address': token_address,
                'migration_time': migration_datetime.isoformat(),
                'symbol': symbol,
                'name': name,
                'signature': signature,
                # Add any other fields from the event
                'initial_liquidity_sol': event.get('initialLiquiditySol', 0),
                'pool_address': event.get('poolAddress', ''),
                'market_cap': event.get('marketCap', 0),
                # PRE-MIGRATION METRICS (bonding curve data)
                'pre_migration_metrics': pre_migration_metrics,
                # WALLET INTELLIGENCE (whale/profitable/insider detection)
                'wallet_intelligence': wallet_intelligence,
                # TWITTER ACCOUNT ANALYSIS (social legitimacy)
                'twitter_analysis': twitter_account_analysis,
                'raw_event': event  # Keep full event for reference
            }

            self.logger.info(f"Analyzing {symbol}...")

            # Analyze the token
            result = await self.agent.process_migration(migration_event)

            # Save result
            self.agent._save_result(result)

            # Extract Claude's recommendation
            if result.get('claude_analysis'):
                recommendation = result['claude_analysis'].get('recommendation', 'UNKNOWN')
                confidence = result['claude_analysis'].get('confidence', 'UNKNOWN')
                risk_score = result['claude_analysis'].get('risk_score', 0)

                self.logger.info("=" * 70)
                self.logger.info(f"📊 ANALYSIS COMPLETE: {symbol}")
                self.logger.info(f"   Recommendation: {recommendation}")
                self.logger.info(f"   Confidence: {confidence}")
                self.logger.info(f"   Risk Score: {risk_score}/10")
                self.logger.info("=" * 70)

                # ALERT on high confidence BUY
                if recommendation == 'BUY' and confidence == 'HIGH':
                    self.logger.warning("=" * 70)
                    self.logger.warning(f"🚨 HIGH CONFIDENCE BUY SIGNAL")
                    self.logger.warning(f"   Token: {symbol} ({name})")
                    self.logger.warning(f"   Address: {token_address}")
                    self.logger.warning(f"   Risk Score: {risk_score}/10")
                    self.logger.warning("=" * 70)

                    # TODO: Add Discord/Telegram webhook here
                    # await self.send_alert(symbol, token_address, risk_score)

            # Save seen migrations
            self._save_seen_migrations()

        except Exception as e:
            self.logger.error(f"Error handling migration: {e}")
            import traceback
            traceback.print_exc()

    async def handle_new_token(self, event: dict):
        """
        Handle new token creation event (optional monitoring)

        Args:
            event: New token event data
        """
        try:
            token_address = event.get('mint') or event.get('tokenAddress')
            symbol = event.get('symbol', 'UNKNOWN')

            self.logger.info(f"✨ New token created: {symbol} ({token_address[:8] if token_address else 'N/A'}...)")

            # You can add logic here to monitor promising new tokens
            # before they migrate to Raydium

        except Exception as e:
            self.logger.error(f"Error handling new token: {e}")

    async def run(self):
        """Main run loop"""
        self.logger.info("=" * 70)
        self.logger.info("🚀 REAL-TIME Pump.fun → Raydium Migration Monitor")
        self.logger.info("=" * 70)

        # Display mode status
        self.mode_manager.display_status()

        self.logger.info("\n" + "=" * 70)
        self.logger.info("Using PumpPortal WebSocket for INSTANT migration detection")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("=" * 70)

        # Initialize agent
        self.logger.info("Initializing agent...")
        self.agent = PumpfunAgent(use_mock_data=False)

        try:
            # Connect to PumpPortal and start listening
            await self.pumpportal.run(
                on_migration=self.handle_migration,
                on_new_token=self.handle_new_token  # Optional: monitor new tokens too
            )

        except KeyboardInterrupt:
            self.logger.info("\nShutting down monitor...")
        except Exception as e:
            self.logger.error(f"Monitor error: {e}")
        finally:
            # Cleanup
            if self.agent:
                await self.agent.close()
            await self.pumpportal.disconnect()
            await self.pumpfun_data.close()  # Close Pump.fun data client
            await self.birdeye.close()  # Close Birdeye client
            await self.twitter_analyzer.close()  # Close Twitter analyzer
            self._save_seen_migrations()
            self.logger.info("Monitor stopped")


async def main():
    """Main entry point"""
    setup_directories()

    monitor = RealtimeMigrationMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
