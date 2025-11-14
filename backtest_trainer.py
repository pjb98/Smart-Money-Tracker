"""
Training Mode - Backtest on Historical Migration Data
Analyzes past migrations to evaluate strategy performance
"""
import asyncio
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
import json
from typing import List, Dict, Any, Optional

from config import settings, setup_directories
from src.utils.logger import setup_logger
from src.utils.trading_mode import TradingMode, get_mode_manager
from src.ingestion.pumpfun_data_client import PumpfunDataClient
from src.ingestion.birdeye_client import BirdeyeClient
from src.ingestion.twitter_analyzer import TwitterAnalyzer
from src.trading.paper_trader import PaperTrader
from main import PumpfunAgent


class BacktestTrainer:
    """Backtest strategy on historical migrations"""

    def __init__(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 10000,
        enable_paper_trading: bool = False
    ):
        """
        Initialize backtest trainer

        Args:
            start_date: Start date for backtesting
            end_date: End date for backtesting
            initial_capital: Starting capital for paper trading
            enable_paper_trading: If True, use TRAINING_PAPER mode (backtest + simulate trades)
        """
        self.logger = setup_logger(settings.log_file, settings.log_level)
        self.mode_manager = get_mode_manager()
        self.agent = None
        self.pumpfun_data = PumpfunDataClient()
        self.birdeye = BirdeyeClient(api_key=settings.birdeye_api_key)
        self.twitter_analyzer = TwitterAnalyzer(bearer_token=settings.twitter_bearer_token)

        # Date range
        self.start_date = start_date or (datetime.now() - timedelta(days=7))
        self.end_date = end_date or datetime.now()

        # Paper trading (optional)
        self.enable_paper_trading = enable_paper_trading
        self.paper_trader = None
        if enable_paper_trading:
            self.paper_trader = PaperTrader(initial_capital=initial_capital)

        # Results tracking
        self.total_migrations = 0
        self.analyzed_migrations = 0
        self.buy_recommendations = 0
        self.hold_recommendations = 0
        self.avoid_recommendations = 0
        self.errors = 0

        self.results_file = Path("data/backtest_results.json")
        self.results_file.parent.mkdir(parents=True, exist_ok=True)

    async def fetch_historical_migrations(self) -> List[Dict[str, Any]]:
        """
        Fetch historical migrations from Pump.fun

        Returns:
            List of migration events
        """
        self.logger.info(f"Fetching historical migrations from {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}...")

        # TODO: Implement actual historical data fetching
        # This would require:
        # 1. PumpPortal historical API (if available)
        # 2. Or: Scraping past transactions from Solana blockchain
        # 3. Or: Using saved migration data from previous monitoring sessions

        # For now, we'll use saved migration results if available
        migrations = []
        results_dir = Path("data/results")

        if results_dir.exists():
            for result_file in results_dir.glob("*.json"):
                try:
                    with open(result_file, 'r') as f:
                        result = json.load(f)

                    # Check if migration is within date range
                    migration_time_str = result.get('migration_event', {}).get('migration_time')
                    if migration_time_str:
                        migration_time = datetime.fromisoformat(migration_time_str)
                        if self.start_date <= migration_time <= self.end_date:
                            migrations.append(result.get('migration_event'))

                except Exception as e:
                    self.logger.debug(f"Error loading result file {result_file}: {e}")

        if migrations:
            self.logger.info(f"Found {len(migrations)} historical migrations")
        else:
            self.logger.warning("No historical migrations found")
            self.logger.info("Tip: Run monitor_realtime.py or paper_trade_monitor.py first to collect data")

        return migrations

    async def analyze_migration(self, migration_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a historical migration

        Args:
            migration_event: Migration event data

        Returns:
            Analysis result
        """
        token_address = migration_event.get('token_address')
        symbol = migration_event.get('symbol', 'UNKNOWN')

        self.logger.info(f"Analyzing {symbol} ({token_address[:8] if token_address else 'N/A'}...)")

        # Run analysis through agent
        result = await self.agent.process_migration(migration_event)

        return result

    async def run_backtest(self):
        """Run backtest on historical data"""
        self.logger.info("=" * 70)
        self.logger.info("🎓 TRAINING MODE - Backtesting Historical Data")
        self.logger.info("=" * 70)

        # Display mode status
        self.mode_manager.display_status()

        self.logger.info(f"\n📅 Date Range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        if self.enable_paper_trading:
            self.logger.info(f"💰 Paper Trading: ENABLED (Capital: ${self.paper_trader.initial_capital:,.2f})")
        else:
            self.logger.info(f"💰 Paper Trading: DISABLED (Analysis only)")

        self.logger.info("=" * 70)

        # Initialize agent
        self.logger.info("\nInitializing agent...")
        self.agent = PumpfunAgent(use_mock_data=False)

        try:
            # Fetch historical migrations
            migrations = await self.fetch_historical_migrations()
            self.total_migrations = len(migrations)

            if self.total_migrations == 0:
                self.logger.warning("No historical data available for backtesting")
                self.logger.info("\n💡 To collect historical data:")
                self.logger.info("   1. Run: python monitor_realtime.py")
                self.logger.info("   2. Let it run for a few hours/days")
                self.logger.info("   3. Then run backtest on collected data")
                return

            self.logger.info(f"\nAnalyzing {self.total_migrations} historical migrations...")
            self.logger.info("=" * 70)

            # Analyze each migration
            for idx, migration in enumerate(migrations, 1):
                try:
                    self.logger.info(f"\n[{idx}/{self.total_migrations}]")

                    # Analyze
                    result = await self.analyze_migration(migration)

                    # Extract recommendation
                    claude_analysis = result.get('claude_analysis', {})
                    recommendation = claude_analysis.get('recommendation', 'HOLD')
                    confidence = claude_analysis.get('confidence', 'MEDIUM')
                    risk_score = claude_analysis.get('risk_score', 5)

                    # Track recommendations
                    if recommendation == 'BUY':
                        self.buy_recommendations += 1
                    elif recommendation == 'AVOID':
                        self.avoid_recommendations += 1
                    else:
                        self.hold_recommendations += 1

                    self.analyzed_migrations += 1

                    self.logger.info(f"   Recommendation: {recommendation} ({confidence} confidence, risk {risk_score}/10)")

                    # Paper trading (if enabled)
                    if self.enable_paper_trading and recommendation == 'BUY':
                        symbol = migration.get('symbol', 'UNKNOWN')
                        token_address = migration.get('token_address')
                        features = result.get('features', {})
                        twitter_analysis = migration.get('twitter_analysis')
                        prediction = result.get('prediction', {})
                        predicted_return = prediction.get('prediction', 0.25)

                        # Estimate initial price
                        initial_price = self._estimate_price(migration, features)

                        # Watch token
                        position = await self.paper_trader.watch_token(
                            token_address=token_address,
                            symbol=symbol,
                            recommendation=recommendation,
                            confidence=confidence,
                            risk_score=risk_score,
                            predicted_return=predicted_return,
                            features=features,
                            twitter_analysis=twitter_analysis,
                            current_price=initial_price
                        )

                        if position:
                            # Check entry
                            should_enter = await self.paper_trader.check_entry_signal(
                                token_address, initial_price
                            )

                            if should_enter:
                                await self.paper_trader.enter_position(
                                    token_address, initial_price, predicted_return, fill_pct=1.0
                                )

                                self.logger.info(f"   📊 Paper trade: ENTERED at ${initial_price:.8f}")

                    # Delay to avoid rate limits
                    await asyncio.sleep(1)

                except Exception as e:
                    self.logger.error(f"Error analyzing migration {idx}: {e}")
                    self.errors += 1
                    import traceback
                    traceback.print_exc()

            # Final summary
            self.logger.info("\n" + "=" * 70)
            self.logger.info("BACKTEST SUMMARY")
            self.logger.info("=" * 70)

            self.logger.info(f"\n📊 Analysis Results:")
            self.logger.info(f"   Total Migrations: {self.total_migrations}")
            self.logger.info(f"   Successfully Analyzed: {self.analyzed_migrations}")
            self.logger.info(f"   Errors: {self.errors}")

            self.logger.info(f"\n💡 Recommendations:")
            self.logger.info(f"   BUY:   {self.buy_recommendations} ({self.buy_recommendations/self.analyzed_migrations*100:.1f}%)" if self.analyzed_migrations > 0 else "   BUY:   0 (0%)")
            self.logger.info(f"   HOLD:  {self.hold_recommendations} ({self.hold_recommendations/self.analyzed_migrations*100:.1f}%)" if self.analyzed_migrations > 0 else "   HOLD:  0 (0%)")
            self.logger.info(f"   AVOID: {self.avoid_recommendations} ({self.avoid_recommendations/self.analyzed_migrations*100:.1f}%)" if self.analyzed_migrations > 0 else "   AVOID: 0 (0%)")

            # Paper trading summary
            if self.enable_paper_trading and self.paper_trader:
                perf = self.paper_trader.get_performance_summary()
                self.logger.info(f"\n💰 Paper Trading Performance:")
                self.logger.info(f"   Initial Capital:  ${perf['initial_capital']:,.2f}")
                self.logger.info(f"   Final Capital:    ${perf['current_capital']:,.2f}")
                self.logger.info(f"   Total P&L:        ${perf['total_pnl']:,.2f} ({perf['total_return_pct']:+.2f}%)")
                self.logger.info(f"   Total Trades:     {perf['total_trades']}")
                self.logger.info(f"   Win Rate:         {perf['win_rate']*100:.1f}%")

            # Save results
            self._save_backtest_results()

            self.logger.info("\n" + "=" * 70)
            self.logger.info("Backtest complete!")

            if self.enable_paper_trading:
                self.logger.info("\nView trading journal:")
                self.logger.info("  python view_trading_journal.py --summary")

        except Exception as e:
            self.logger.error(f"Backtest error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Cleanup
            if self.agent:
                await self.agent.close()
            await self.pumpfun_data.close()
            await self.birdeye.close()
            await self.twitter_analyzer.close()

    def _estimate_price(self, migration_event: Dict, features: Dict) -> float:
        """
        Estimate initial price from migration data

        Args:
            migration_event: Migration data
            features: Token features

        Returns:
            Estimated price
        """
        market_cap = migration_event.get('market_cap', 100000)
        estimated_supply = 1_000_000_000
        price = market_cap / estimated_supply if estimated_supply > 0 else 0.0001
        return price

    def _save_backtest_results(self):
        """Save backtest results to file"""
        results = {
            'backtest_date': datetime.now().isoformat(),
            'date_range': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat()
            },
            'statistics': {
                'total_migrations': self.total_migrations,
                'analyzed': self.analyzed_migrations,
                'errors': self.errors,
                'buy_recommendations': self.buy_recommendations,
                'hold_recommendations': self.hold_recommendations,
                'avoid_recommendations': self.avoid_recommendations
            },
            'paper_trading_enabled': self.enable_paper_trading
        }

        if self.enable_paper_trading and self.paper_trader:
            results['paper_trading_performance'] = self.paper_trader.get_performance_summary()

        try:
            with open(self.results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            self.logger.info(f"\nResults saved to: {self.results_file}")
        except Exception as e:
            self.logger.error(f"Error saving backtest results: {e}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Backtest strategy on historical data')
    parser.add_argument('--days', type=int, default=7, help='Number of days to backtest (default: 7)')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=10000, help='Initial capital for paper trading (default: $10,000)')
    parser.add_argument('--paper-trading', action='store_true', help='Enable paper trading simulation')
    args = parser.parse_args()

    setup_directories()

    # Check mode
    mode_manager = get_mode_manager()

    # Determine which mode to use
    if args.paper_trading:
        # TRAINING_PAPER mode: Backtest + simulate trades
        if mode_manager.get_mode() != TradingMode.TRAINING_PAPER:
            logger.warning("⚠️  Switching to TRAINING_PAPER mode")
            mode_manager.set_mode(TradingMode.TRAINING_PAPER)
    else:
        # TRAINING mode: Analysis only
        if mode_manager.get_mode() != TradingMode.TRAINING:
            logger.warning("⚠️  Switching to TRAINING mode")
            mode_manager.set_mode(TradingMode.TRAINING)

    # Enable system if not enabled
    if not mode_manager.is_active():
        logger.info("Enabling system for training...")
        mode_manager.enable()

    # Parse dates
    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    else:
        start_date = datetime.now() - timedelta(days=args.days)

    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()

    trainer = BacktestTrainer(
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.capital,
        enable_paper_trading=args.paper_trading
    )

    await trainer.run_backtest()


if __name__ == "__main__":
    asyncio.run(main())
