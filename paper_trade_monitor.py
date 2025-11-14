"""
Paper Trading Monitor - Real-time paper trading with SL/TP automation
Integrates with migration monitor and simulates trading
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
from src.trading.paper_trader import PaperTrader
from main import PumpfunAgent


class PaperTradingMonitor:
    """Real-time paper trading monitor"""

    def __init__(self, initial_capital: float = 10000):
        """Initialize paper trading monitor"""
        self.logger = setup_logger(settings.log_file, settings.log_level)
        self.mode_manager = get_mode_manager()
        self.agent = None
        self.paper_trader = PaperTrader(initial_capital=initial_capital)
        self.pumpportal = PumpPortalClient()
        self.pumpfun_data = PumpfunDataClient()
        self.birdeye = BirdeyeClient(api_key=settings.birdeye_api_key)
        self.twitter_analyzer = TwitterAnalyzer(bearer_token=settings.twitter_bearer_token)

        # Price tracking for open positions
        self.price_update_interval = 60  # Check prices every 60 seconds

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
        Handle migration event and make paper trading decision

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
            self.logger.info("NEW MIGRATION DETECTED")
            self.logger.info("=" * 70)

            # Extract token address
            token_address = (
                event.get('mint') or
                event.get('tokenAddress') or
                event.get('token') or
                event.get('signature')
            )

            if not token_address:
                self.logger.warning("No token address in migration event")
                return

            # Skip if already processed
            if token_address in self.seen_migrations:
                self.logger.debug(f"Already processed migration for {token_address[:8]}...")
                return

            self.seen_migrations.add(token_address)

            # Extract metadata
            symbol = event.get('symbol', 'UNKNOWN')
            name = event.get('name', event.get('tokenName', 'Unknown Token'))

            self.logger.info(f"✨ Token: {name} ({symbol})")
            self.logger.info(f"   Address: {token_address}")

            # Fetch pre-migration metrics
            self.logger.info(f"Fetching pre-migration data...")
            migration_datetime = datetime.now()
            pre_migration_metrics = await self.pumpfun_data.calculate_pre_migration_metrics(
                token_address,
                migration_datetime
            )

            # Fetch wallet intelligence
            self.logger.info(f"Analyzing wallet intelligence...")
            wallet_intelligence = await self.birdeye.analyze_wallet_intelligence(
                token_address,
                top_n_holders=50
            )

            # Analyze Twitter if available
            twitter_account_analysis = None
            token_data = await self.pumpfun_data.get_token_data(token_address)
            if token_data and ('twitter' in token_data or 'x' in token_data):
                self.logger.info(f"Analyzing Twitter account...")
                try:
                    username = self.twitter_analyzer.extract_twitter_handle(token_data)
                    if username:
                        twitter_account_analysis = await self.twitter_analyzer.comprehensive_analysis(username, token_data)
                except Exception as e:
                    self.logger.warning(f"Twitter analysis failed: {e}")

            # Build migration event
            migration_event = {
                'token_address': token_address,
                'migration_time': migration_datetime.isoformat(),
                'symbol': symbol,
                'name': name,
                'initial_liquidity_sol': event.get('initialLiquiditySol', 0),
                'pool_address': event.get('poolAddress', ''),
                'market_cap': event.get('marketCap', 0),
                'pre_migration_metrics': pre_migration_metrics,
                'wallet_intelligence': wallet_intelligence,
                'twitter_analysis': twitter_account_analysis,
                'raw_event': event
            }

            # Analyze with agent
            self.logger.info(f"Running AI analysis...")
            result = await self.agent.process_migration(migration_event)

            # Save result
            self.agent._save_result(result)

            # Extract analysis
            claude_analysis = result.get('claude_analysis', {})
            features = result.get('features', {})
            prediction = result.get('prediction', {})
            comprehensive_report = result.get('comprehensive_report', {})

            recommendation = claude_analysis.get('recommendation', 'HOLD')
            confidence = claude_analysis.get('confidence', 'MEDIUM')
            risk_score = claude_analysis.get('risk_score', 5)

            self.logger.info("=" * 70)
            self.logger.info(f"📊 ANALYSIS RESULT: {symbol}")
            self.logger.info(f"   Recommendation: {recommendation} ({confidence} confidence)")
            self.logger.info(f"   Risk Score: {risk_score}/10")

            # PAPER TRADING DECISION (only if trading is allowed)
            if recommendation == 'BUY':
                # Check if trading is allowed in current mode
                if not self.mode_manager.can_trade():
                    self.logger.info(f"⏭️  Skipping trade: Mode is {self.mode_manager.get_mode().value} (trading disabled)")
                    self.logger.info(f"   Token {symbol} received BUY recommendation but trading is not enabled")
                    return

                self.logger.info("=" * 70)
                self.logger.info("🤖 PAPER TRADING DECISION")
                self.logger.info("=" * 70)

                # Get initial price (from market cap and supply if available)
                # In real trading, we'd get this from DEX
                # For paper trading, we'll estimate or use a mock price
                initial_price = self._estimate_initial_price(migration_event, features)

                # Start watching token for entry
                predicted_return = prediction.get('prediction', 0.25)

                position = await self.paper_trader.watch_token(
                    token_address=token_address,
                    symbol=symbol,
                    recommendation=recommendation,
                    confidence=confidence,
                    risk_score=risk_score,
                    predicted_return=predicted_return,
                    features=features,
                    twitter_analysis=twitter_account_analysis,
                    current_price=initial_price
                )

                if position:
                    self.logger.info(f"✅ Now watching {symbol} for entry")

                    # Check if immediate entry
                    should_enter = await self.paper_trader.check_entry_signal(
                        token_address, initial_price
                    )

                    if should_enter:
                        await self.paper_trader.enter_position(
                            token_address, initial_price, predicted_return, fill_pct=1.0
                        )

                # Display performance
                perf = self.paper_trader.get_performance_summary()
                self.logger.info(f"\n💰 Portfolio: ${perf['current_capital']:.2f} | P&L: ${perf['total_pnl']:.2f} | Win Rate: {perf['win_rate']*100:.1f}%")

            else:
                self.logger.info(f"⏭️  Skipping {symbol}: {recommendation}")

            self.logger.info("=" * 70)

            # Save seen migrations
            self._save_seen_migrations()

        except Exception as e:
            self.logger.error(f"Error handling migration: {e}")
            import traceback
            traceback.print_exc()

    def _estimate_initial_price(
        self,
        migration_event: Dict,
        features: Dict
    ) -> float:
        """
        Estimate initial price (mock for paper trading)

        In real trading, this would come from DEX API

        Args:
            migration_event: Migration data
            features: Token features

        Returns:
            Estimated price in USD
        """
        # For paper trading, we'll use a mock price
        # In production, fetch from Jupiter, Raydium API, etc.
        market_cap = migration_event.get('market_cap', 100000)

        # Typical supply for pump.fun tokens
        estimated_supply = 1_000_000_000

        price = market_cap / estimated_supply if estimated_supply > 0 else 0.0001

        return price

    async def simulate_price_updates(self):
        """
        Simulate price updates for open positions

        In real trading, this would fetch from DEX APIs
        """
        while True:
            try:
                await asyncio.sleep(self.price_update_interval)

                if not self.paper_trader.positions:
                    continue

                self.logger.debug(f"Updating {len(self.paper_trader.positions)} open positions...")

                for token_address, position in list(self.paper_trader.positions.items()):
                    # Simulate price movement (random walk)
                    # In production, fetch real price from DEX
                    current_price = await self._fetch_current_price(token_address, position)

                    if current_price:
                        await self.paper_trader.update_position(token_address, current_price)

            except Exception as e:
                self.logger.error(f"Error updating positions: {e}")

    async def _fetch_current_price(self, token_address: str, position) -> float:
        """
        Fetch current price (mock for paper trading)

        In real trading, fetch from Jupiter, Raydium, etc.

        Args:
            token_address: Token address
            position: Position object

        Returns:
            Current price
        """
        import random

        # MOCK PRICE SIMULATION
        # Simulate realistic price action based on token type

        if position.entry_price is None:
            return position.current_price

        current = position.current_price

        if position.token_type.value == 'viral_meme':
            # Viral memes: High volatility, can pump fast or dump fast
            change_pct = random.gauss(0.02, 0.15)  # 2% drift, 15% volatility
        elif position.token_type.value == 'tech':
            # Tech tokens: Lower volatility, gradual movement
            change_pct = random.gauss(0.01, 0.05)  # 1% drift, 5% volatility
        else:
            # Unknown: Medium volatility
            change_pct = random.gauss(0.01, 0.10)

        # Apply change
        new_price = current * (1 + change_pct)

        # Ensure price stays positive
        new_price = max(new_price, current * 0.5)  # Max 50% drop per update

        return new_price

    async def run(self):
        """Main run loop"""
        self.logger.info("=" * 70)
        self.logger.info("🤖 PAPER TRADING MONITOR")
        self.logger.info("=" * 70)

        # Display mode status
        self.mode_manager.display_status()

        self.logger.info("\n" + "="*70)
        self.logger.info("Simulating trades with virtual capital")
        self.logger.info("Stop Loss and Take Profit automation enabled")
        self.logger.info("Press Ctrl+C to stop")
        self.logger.info("=" * 70)

        # Display initial capital
        perf = self.paper_trader.get_performance_summary()
        self.logger.info(f"\n💰 Starting Capital: ${perf['initial_capital']:,.2f}")
        self.logger.info(f"📊 Max Position Size: {self.paper_trader.max_position_size_pct*100:.0f}% per trade")

        # Initialize agent
        self.logger.info("\nInitializing agent...")
        self.agent = PumpfunAgent(use_mock_data=False)

        # Start price update task
        price_task = asyncio.create_task(self.simulate_price_updates())

        try:
            # Connect to PumpPortal and start listening
            await self.pumpportal.run(
                on_migration=self.handle_migration,
                on_new_token=None  # Optional: monitor new tokens
            )

        except KeyboardInterrupt:
            self.logger.info("\nShutting down monitor...")
        except Exception as e:
            self.logger.error(f"Monitor error: {e}")
        finally:
            # Cleanup
            price_task.cancel()
            if self.agent:
                await self.agent.close()
            await self.pumpportal.disconnect()
            await self.pumpfun_data.close()
            await self.birdeye.close()
            await self.twitter_analyzer.close()
            self._save_seen_migrations()

            # Final performance summary
            self.logger.info("\n" + "=" * 70)
            self.logger.info("FINAL PERFORMANCE SUMMARY")
            self.logger.info("=" * 70)
            perf = self.paper_trader.get_performance_summary()
            self.logger.info(f"Initial Capital: ${perf['initial_capital']:,.2f}")
            self.logger.info(f"Final Capital:   ${perf['current_capital']:,.2f}")
            self.logger.info(f"Total P&L:       ${perf['total_pnl']:,.2f} ({perf['total_return_pct']:+.2f}%)")
            self.logger.info(f"Total Trades:    {perf['total_trades']}")
            self.logger.info(f"Win Rate:        {perf['win_rate']*100:.1f}%")
            self.logger.info("=" * 70)

            self.logger.info("\nView detailed journal:")
            self.logger.info("  python view_trading_journal.py --summary")
            self.logger.info("  python view_trading_journal.py --list")
            self.logger.info("  python view_trading_journal.py --analyze")

            self.logger.info("\nMonitor stopped")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Paper trading monitor')
    parser.add_argument('--capital', type=float, default=10000, help='Initial capital (default: $10,000)')
    args = parser.parse_args()

    setup_directories()

    monitor = PaperTradingMonitor(initial_capital=args.capital)
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
