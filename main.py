"""
Main orchestration script for Pumpfun -> Raydium Prediction Agent
Runs the complete pipeline: data ingestion -> feature engineering -> prediction -> Claude analysis
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from loguru import logger
from typing import List, Dict, Any
import schedule
import time

from config import settings, setup_directories
from src.utils.logger import setup_logger
from src.ingestion.pumpfun_client import PumpfunClient, MockPumpfunClient
from src.ingestion.solana_client import SolanaClient
from src.ingestion.phanes_parser import PhanesParser, MockPhanesParser
from src.ingestion.twitter_analyzer import TwitterAnalyzer
from src.features.feature_engineer import FeatureEngineer
from src.features.label_generator import LabelGenerator
from src.models.predictor import TokenPredictor
from src.agents.claude_agent import ClaudeAgent
from src.utils.report_generator import ReportGenerator
from src.trading.paper_trader import PaperTrader


class PumpfunAgent:
    """Main agent orchestrator"""

    def __init__(self, use_mock_data: bool = True):
        """
        Initialize agent

        Args:
            use_mock_data: Use mock clients for testing without API keys
        """
        # Setup
        setup_directories()
        self.logger = setup_logger(settings.log_file, settings.log_level)

        # Initialize clients
        if use_mock_data:
            self.logger.info("Using MOCK data clients")
            self.pumpfun_client = MockPumpfunClient()
            self.phanes_parser = MockPhanesParser()
        else:
            self.logger.info("Using REAL data - will fetch from Solana blockchain")
            # Pumpfun client (optional - won't be used for monitoring via DexScreener)
            self.pumpfun_client = PumpfunClient(
                api_url=settings.pumpfun_api_url,
                api_key=settings.pumpfun_api_key
            )
            # Phanes parser - use mock if no Telegram credentials
            if settings.telegram_api_id and settings.telegram_api_hash:
                self.phanes_parser = PhanesParser(
                    api_id=settings.telegram_api_id,
                    api_hash=settings.telegram_api_hash,
                    phone=settings.telegram_phone,
                    channel_id=settings.phanes_channel_id
                )
            else:
                self.logger.warning("No Telegram credentials - using mock Phanes data")
                self.phanes_parser = MockPhanesParser()

        self.solana_client = SolanaClient(settings.solana_rpc_url)

        # Initialize Twitter analyzer
        self.twitter_analyzer = TwitterAnalyzer(bearer_token=settings.twitter_bearer_token)

        # Initialize report generator
        self.report_generator = ReportGenerator(output_dir="data/reports")

        # Initialize feature engineer and predictor
        self.feature_engineer = FeatureEngineer(lookback_windows=settings.lookback_windows)
        self.label_generator = LabelGenerator(label_windows=settings.label_windows)

        # Load or initialize model
        self.predictor = self._load_or_create_model()

        # Initialize Claude agent if API key available
        if settings.anthropic_api_key:
            self.claude_agent = ClaudeAgent(api_key=settings.anthropic_api_key)
        else:
            self.logger.warning("No Claude API key provided, agent disabled")
            self.claude_agent = None

        # Initialize Paper Trader for automatic trading
        self.paper_trader = PaperTrader(
            initial_capital=10000,
            max_position_size_pct=0.10,
            use_ai_optimization=False
        )
        self.logger.info("Paper Trader initialized with $10,000 capital")

        self.logger.info("Agent initialized successfully")

    def _load_or_create_model(self) -> TokenPredictor:
        """Load existing model or create new one"""
        model_path = Path(settings.model_save_path) / "token_predictor.pkl"

        if model_path.exists():
            self.logger.info(f"Loading model from {model_path}")
            predictor = TokenPredictor()
            predictor.load(str(model_path))
            return predictor
        else:
            self.logger.info("No existing model found, creating new predictor")
            return TokenPredictor(target_variable="return_24h", task_type="regression")

    async def process_migration(self, migration_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single migration event

        Args:
            migration_event: Migration event dict from Pumpfun

        Returns:
            Analysis result dict
        """
        token_address = migration_event['token_address']
        migration_time = datetime.fromisoformat(migration_event['migration_time'].replace('Z', '+00:00'))

        self.logger.info(f"Processing migration: {token_address}")

        try:
            # 1. Fetch on-chain data
            self.logger.debug("Fetching on-chain data...")

            # Get transactions (24h before migration)
            start_time = migration_time - timedelta(hours=24)
            transactions = await self.solana_client.get_transactions_in_timeframe(
                token_address,
                start_time,
                migration_time,
                max_transactions=1000
            )

            # Get holder data
            holders = await self.solana_client.get_token_accounts(token_address)

            # Get token info
            token_info = await self.pumpfun_client.get_token_info(token_address)

            # 2. Fetch Phanes data
            self.logger.debug("Fetching Phanes scan data...")
            phanes_scans = await self.phanes_parser.fetch_recent_scans(hours_back=48)
            phanes_data = self.phanes_parser.get_token_scan_metrics(token_address, lookback_hours=24)

            # 2.5. Analyze Twitter account (if available)
            twitter_account_analysis = None
            if token_info and 'twitter' in token_info:
                self.logger.debug("Analyzing Twitter account...")
                try:
                    username = self.twitter_analyzer.extract_twitter_handle(token_info)
                    if username:
                        twitter_account_analysis = await self.twitter_analyzer.comprehensive_analysis(username, token_info)
                        self.logger.info(f"Twitter analysis complete: Risk={twitter_account_analysis.get('risk_score', 'N/A')}/10")
                    else:
                        self.logger.debug("No Twitter handle found in token metadata")
                except Exception as e:
                    self.logger.warning(f"Twitter analysis failed: {e}")

            # 3. Build features
            self.logger.debug("Engineering features...")
            features = self.feature_engineer.build_feature_vector(
                token_address=token_address,
                migration_time=migration_time,
                token_data=token_info or {},
                pool_data=migration_event,
                transactions=transactions,
                holders=holders,
                phanes_data=phanes_data,
                twitter_account_analysis=twitter_account_analysis
            )

            # 4. Make prediction
            self.logger.debug("Making prediction...")
            features_df = pd.DataFrame([features])

            if self.predictor.model is not None:
                prediction = self.predictor.predict_with_explanation(features_df)[0]
            else:
                self.logger.warning("Model not trained, skipping prediction")
                prediction = {'prediction': 0.0, 'top_features': []}

            # 5. Claude analysis
            analysis = None
            if self.claude_agent:
                self.logger.debug("Running Claude analysis...")

                # Extract wallet intelligence and pre-migration metrics if available
                wallet_intelligence = migration_event.get('wallet_intelligence')
                pre_migration_metrics = migration_event.get('pre_migration_metrics')

                # Include Twitter analysis in Claude's context
                additional_context = {}
                if twitter_account_analysis:
                    additional_context['twitter_analysis'] = twitter_account_analysis

                analysis = self.claude_agent.analyze_token(
                    token_address,
                    features,
                    prediction,
                    phanes_data,
                    recent_history=None,
                    wallet_intelligence=wallet_intelligence,
                    pre_migration_metrics=pre_migration_metrics,
                    additional_context=additional_context
                )

            # 6. Execute Paper Trade if Claude recommends BUY
            if analysis and self.paper_trader:
                self.logger.debug("Evaluating trading opportunity...")
                try:
                    recommendation = analysis.get('recommendation', 'HOLD')
                    confidence = analysis.get('confidence', 'MEDIUM')
                    risk_score = analysis.get('risk_score', 5)

                    # Extract adaptive risk parameters from features
                    dev_risk_category = features.get('dev_risk_category', None)
                    token_category = features.get('token_category', 'unknown')

                    # Get predicted return from ML model
                    predicted_return = prediction.get('prediction', 0.0)

                    # Get current price (estimate from initial liquidity if not available)
                    current_price = migration_event.get('price_usd', 0.01)

                    if recommendation == 'BUY':
                        self.logger.info(f"🎯 BUY signal detected! Starting position watch...")

                        # Watch token for entry opportunity
                        position = await self.paper_trader.watch_token(
                            token_address=token_address,
                            symbol=migration_event.get('symbol', token_address[:8]),
                            recommendation=recommendation,
                            confidence=confidence,
                            risk_score=risk_score,
                            predicted_return=predicted_return,
                            features=features,
                            twitter_analysis=twitter_account_analysis,
                            current_price=current_price,
                            dev_risk_category=dev_risk_category,
                            token_category=token_category
                        )

                        if position:
                            self.logger.info(f"✅ Now watching {position.symbol} - Entry strategy: {position.entry_strategy}")

                            # Check if should enter immediately
                            should_enter = await self.paper_trader.check_entry_signal(
                                token_address=token_address,
                                current_price=current_price
                            )

                            if should_enter:
                                self.logger.info(f"📈 Entering position for {position.symbol}")
                                await self.paper_trader.enter_position(
                                    token_address=token_address,
                                    entry_price=current_price
                                )
                        else:
                            self.logger.info("Position not created (may not meet criteria)")
                    else:
                        self.logger.info(f"No trade: Recommendation is {recommendation}")

                except Exception as e:
                    self.logger.error(f"Error executing paper trade: {e}")

            # 7. Generate Comprehensive Report
            self.logger.debug("Generating comprehensive investment report...")
            comprehensive_report = self.report_generator.generate_comprehensive_report(
                token_address=token_address,
                migration_event=migration_event,
                features=features,
                prediction=prediction,
                claude_analysis=analysis,
                twitter_analysis=twitter_account_analysis,
                wallet_intelligence=wallet_intelligence,
                pre_migration_metrics=pre_migration_metrics
            )

            # 8. Add paper trading info if position was created
            paper_trading_info = None
            if token_address in self.paper_trader.positions:
                position = self.paper_trader.positions[token_address]
                paper_trading_info = {
                    'status': position.status.value,
                    'entry_strategy': position.entry_strategy,
                    'entry_price': position.entry_price,
                    'stop_loss': position.stop_loss,
                    'position_size': position.position_size_usd,
                    'confidence': position.confidence,
                    'risk_score': position.risk_score
                }

            # 9. Compile result (includes report and trading info)
            result = {
                'token_address': token_address,
                'migration_time': migration_time.isoformat(),
                'features': features,
                'prediction': prediction,
                'claude_analysis': analysis,
                'twitter_analysis': twitter_account_analysis,
                'comprehensive_report': comprehensive_report,
                'paper_trading': paper_trading_info,
                'processed_at': datetime.now().isoformat()
            }

            self.logger.info(f"Successfully processed {token_address}")

            # Log report summary
            self.logger.info("="*70)
            self.logger.info("INVESTMENT DECISION REPORT")
            self.logger.info("="*70)
            exec_summary = comprehensive_report['executive_summary']
            self.logger.info(exec_summary['one_line_summary'])
            self.logger.info(f"Position Size: {comprehensive_report['decision']['position_size_recommendation']}")
            self.logger.info(f"Entry: {comprehensive_report['decision']['entry_strategy']}")
            self.logger.info(f"Exit: {comprehensive_report['decision']['exit_strategy']}")

            # Log red flags if any
            red_flags = comprehensive_report['red_flags']
            if red_flags:
                self.logger.warning(f"⚠️  {len(red_flags)} RED FLAGS DETECTED:")
                for flag in red_flags[:3]:  # Show top 3
                    self.logger.warning(f"  [{flag['severity']}] {flag['flag']}")

            self.logger.info("="*70)

            return result

        except Exception as e:
            self.logger.error(f"Error processing migration {token_address}: {e}")
            return {
                'token_address': token_address,
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }

    async def monitor_positions(self, update_interval_seconds: int = 60):
        """
        Continuously monitor and update all open positions

        Args:
            update_interval_seconds: How often to update positions (default 60s)
        """
        self.logger.info(f"Starting position monitor (update every {update_interval_seconds}s)")

        while True:
            try:
                if self.paper_trader.positions:
                    self.logger.debug(f"Monitoring {len(self.paper_trader.positions)} active positions")

                    for token_address, position in list(self.paper_trader.positions.items()):
                        try:
                            # Fetch current price from Solana
                            token_info = await self.pumpfun_client.get_token_info(token_address)
                            current_price = token_info.get('price_usd', position.current_price) if token_info else position.current_price

                            # Update position (checks SL/TP, trailing stop, time decay)
                            await self.paper_trader.update_position(token_address, current_price)

                            # Check entry signals for WATCHING positions
                            if position.status.value == 'watching':
                                should_enter = await self.paper_trader.check_entry_signal(
                                    token_address=token_address,
                                    current_price=current_price
                                )

                                if should_enter:
                                    self.logger.info(f"📈 Entry signal triggered for {position.symbol}")
                                    await self.paper_trader.enter_position(
                                        token_address=token_address,
                                        entry_price=current_price
                                    )

                        except Exception as e:
                            self.logger.error(f"Error updating position {token_address[:8]}: {e}")

                    # Log performance summary periodically
                    summary = self.paper_trader.get_performance_summary()
                    self.logger.info(
                        f"Portfolio: ${summary['current_capital']:.2f} | "
                        f"P&L: ${summary['total_pnl']:.2f} | "
                        f"Win Rate: {summary['win_rate']*100:.1f}% | "
                        f"Active: {summary['active_positions']}"
                    )

            except Exception as e:
                self.logger.error(f"Error in position monitor loop: {e}")

            # Wait before next update
            await asyncio.sleep(update_interval_seconds)

    async def monitor_migrations(self, check_interval_minutes: int = 5):
        """
        Continuously monitor for new migrations

        Args:
            check_interval_minutes: How often to check for new migrations
        """
        self.logger.info(f"Starting migration monitor (check every {check_interval_minutes} min)")

        last_check_time = datetime.now() - timedelta(hours=24)

        while True:
            try:
                # Fetch new migrations since last check
                migrations = await self.pumpfun_client.get_migrations(
                    since=last_check_time,
                    limit=50
                )

                if migrations:
                    self.logger.info(f"Found {len(migrations)} new migrations")

                    for migration in migrations:
                        result = await self.process_migration(migration)

                        # Save result
                        self._save_result(result)

                        # Send alert if Claude analysis available
                        if result.get('claude_analysis') and self.claude_agent:
                            alert = self.claude_agent.generate_alert(
                                result['token_address'],
                                result['claude_analysis']
                            )
                            self.logger.info(f"Alert:\n{alert}")

                last_check_time = datetime.now()

            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")

            # Wait before next check
            await asyncio.sleep(check_interval_minutes * 60)

    def _save_result(self, result: Dict[str, Any]):
        """Save analysis result to disk in multiple formats"""
        results_dir = Path("data/results")
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        token_addr_short = result['token_address'][:8]

        # Save full JSON result
        filename = f"{timestamp}_{token_addr_short}.json"
        filepath = results_dir / filename

        import json
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        self.logger.debug(f"Saved result to {filepath}")

        # Save comprehensive report in multiple formats if available
        if 'comprehensive_report' in result:
            report = result['comprehensive_report']

            # Save JSON report
            self.report_generator.save_report(report, format='json')

            # Save human-readable text report
            self.report_generator.save_report(report, format='txt')

            self.logger.info(f"Saved comprehensive reports for {token_addr_short}")

    async def run_backtest(
        self,
        start_date: str,
        end_date: str,
        output_path: str = "data/backtest_results.csv"
    ):
        """
        Run historical backtest

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_path: Where to save results
        """
        self.logger.info(f"Running backtest from {start_date} to {end_date}")

        # Fetch historical migrations
        since_time = datetime.fromisoformat(start_date)
        migrations = await self.pumpfun_client.get_migrations(since=since_time, limit=100)

        results = []
        for migration in migrations:
            result = await self.process_migration(migration)
            results.append(result)

        # Save results
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_path, index=False)

        self.logger.info(f"Backtest complete, results saved to {output_path}")

    async def close(self):
        """Cleanup resources"""
        await self.solana_client.close()
        await self.pumpfun_client.close()
        await self.phanes_parser.disconnect()
        await self.twitter_analyzer.close()
        self.logger.info("Agent shutdown complete")


async def main():
    """Main entry point with automatic trading"""
    logger.info("Starting Pumpfun -> Raydium Prediction Agent with AUTO-TRADING")

    # Initialize agent (use_mock_data=False for real tokens)
    agent = PumpfunAgent(use_mock_data=False)

    logger.info("="*70)
    logger.info("🤖 AI AGENT AUTONOMOUS MODE")
    logger.info("="*70)
    logger.info("✓ Claude AI will analyze all new token migrations")
    logger.info("✓ Automatic paper trading based on AI recommendations")
    logger.info("✓ Dynamic SL/TP with trailing stops")
    logger.info("✓ Position monitoring every 60 seconds")
    logger.info("✓ Dashboard available at http://127.0.0.1:8050")
    logger.info("="*70)

    # Start both monitoring loops in parallel
    try:
        await asyncio.gather(
            agent.monitor_migrations(check_interval_minutes=5),  # Check for new tokens every 5 min
            agent.monitor_positions(update_interval_seconds=60)  # Update positions every 60 sec
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down agent...")
    finally:
        await agent.close()
        logger.info("Agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
