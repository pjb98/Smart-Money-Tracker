"""
Real-time token migration monitor using PumpPortal WebSocket API
Detects Pump.fun → Raydium migrations instantly
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from loguru import logger

from config import settings, setup_directories
from src.utils.logger import setup_logger
from src.ingestion.pumpportal_client import PumpPortalClient
from main import PumpfunAgent


class PumpPortalGraduationMonitor:
    """Monitor for Pump.fun token graduations (bonding curve completions) via PumpPortal WebSocket

    Only tracks tokens that have completed their bonding curve and graduated to PumpSwap.
    Filters out LaunchLab, Moonshot, and other non-Pump.fun platforms.
    """

    def __init__(self):
        """Initialize the graduation monitor"""
        self.logger = setup_logger(settings.log_file, settings.log_level)
        self.seen_tokens_file = Path("data/seen_migrations.json")
        self.seen_tokens = set()

        # Initialize PumpPortal client
        self.pumpportal = PumpPortalClient()

        # Initialize agent for token analysis
        self.agent = PumpfunAgent(use_mock_data=False)

        # Load previously seen tokens
        self._load_seen_tokens()

        self.logger.info("PumpPortal Graduation Monitor initialized")

    def _load_seen_tokens(self):
        """Load previously seen graduations from disk"""
        if self.seen_tokens_file.exists():
            try:
                with open(self.seen_tokens_file, 'r') as f:
                    data = json.load(f)
                    self.seen_tokens = set(data.get('migrations', []))
                self.logger.info(f"Loaded {len(self.seen_tokens)} previously seen graduations")
            except Exception as e:
                self.logger.error(f"Error loading seen graduations: {e}")

    def _save_seen_tokens(self):
        """Save seen graduations to disk"""
        self.seen_tokens_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.seen_tokens_file, 'w') as f:
                json.dump({
                    'migrations': list(self.seen_tokens),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving seen graduations: {e}")

    async def handle_migration(self, event: dict):
        """
        Handle token graduation/migration event from PumpPortal
        Only processes tokens that have completed bonding curve and migrated to PumpSwap

        Args:
            event: Migration event data from WebSocket
        """
        try:
            # Log raw event for debugging
            self.logger.debug(f"Raw migration event: {json.dumps(event, indent=2)}")

            # Extract token information from event
            token_address = event.get('mint') or event.get('token') or event.get('signature')

            if not token_address:
                self.logger.warning(f"Migration event missing address: {event}")
                return

            # Filter out non-Pump.fun tokens (LaunchLab, etc.)
            event_str = json.dumps(event).lower()
            excluded_platforms = ['launchlab', 'moonshot', 'jupiter']
            for platform in excluded_platforms:
                if platform in event_str:
                    self.logger.info(f"Skipping {platform} token: {token_address[:8]}...")
                    return

            # Check if this is actually a bonding curve completion/graduation
            # For Pump.fun, this means the token has graduated to PumpSwap
            is_graduated = event.get('complete', False) or event.get('graduated', False)

            # Log for debugging
            self.logger.debug(f"Token {token_address[:8]}... - Graduated: {is_graduated}")

            # Only process if token has actually graduated/completed bonding curve
            if not is_graduated:
                self.logger.info(f"Skipping non-graduated token: {token_address[:8]}...")
                return

            # Skip if already seen
            if token_address in self.seen_tokens:
                self.logger.debug(f"Already processed migration: {token_address[:8]}...")
                return

            # Mark as seen
            self.seen_tokens.add(token_address)

            # Log graduation detection
            symbol = event.get('symbol', 'UNKNOWN')
            name = event.get('name', 'UNKNOWN')
            self.logger.info("="*70)
            self.logger.info(f"TOKEN GRADUATION DETECTED! (Bonding Curve Complete)")
            self.logger.info(f"  Name: {name}")
            self.logger.info(f"  Symbol: {symbol}")
            self.logger.info(f"  Address: {token_address}")
            self.logger.info(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("="*70)

            # Create migration event for analysis (treating launch as migration)
            migration_event = {
                'token_address': token_address,
                'migration_time': datetime.now().isoformat(),
                'symbol': symbol,
                'name': name,
                'initial_liquidity_sol': event.get('initialBuy', 0),
                'initial_price_sol': event.get('vSolInBondingCurve', 0) / event.get('vTokensInBondingCurve', 1) if event.get('vTokensInBondingCurve') else 0,
                'market_cap_sol': event.get('marketCapSol', 0),
                'bonding_curve_completion': event.get('complete', False),
                'signature': event.get('signature', ''),
                'uri': event.get('uri', ''),
                'raw_event': event  # Store full event for debugging
            }

            # Analyze the token with AI
            self.logger.info(f"Analyzing graduated token {symbol} with AI...")

            try:
                result = await self.agent.process_migration(migration_event)

                # Save result to file
                self.agent._save_result(result)

                # Extract Claude's analysis
                if result.get('claude_analysis'):
                    analysis = result['claude_analysis']
                    recommendation = analysis.get('recommendation', 'UNKNOWN')
                    confidence = analysis.get('confidence', 'UNKNOWN')
                    risk_score = analysis.get('risk_score', 0)

                    self.logger.info(f"AI Analysis Complete for {symbol}:")
                    self.logger.info(f"  Recommendation: {recommendation}")
                    self.logger.info(f"  Confidence: {confidence}")
                    self.logger.info(f"  Risk Score: {risk_score}/10")

                    # Alert on high confidence BUY signals
                    if recommendation == 'BUY' and confidence == 'HIGH':
                        self.logger.warning("="*70)
                        self.logger.warning(f"HIGH CONFIDENCE BUY SIGNAL!")
                        self.logger.warning(f"  Token: {symbol} ({token_address})")
                        self.logger.warning(f"  Risk: {risk_score}/10")
                        self.logger.warning(f"  PumpSwap: https://pump.fun/board")
                        self.logger.warning(f"  DexScreener: https://dexscreener.com/solana/{token_address}")
                        self.logger.warning("="*70)

                # Save seen tokens after successful analysis
                self._save_seen_tokens()

            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

        except Exception as e:
            self.logger.error(f"Error handling token event: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    async def run(self):
        """Main entry point - connect to PumpPortal and monitor graduations"""
        self.logger.info("="*70)
        self.logger.info("PUMPPORTAL GRADUATION MONITOR")
        self.logger.info("="*70)
        self.logger.info("Real-time monitoring via WebSocket")
        self.logger.info("Tracking: BONDING CURVE COMPLETIONS (Graduations to PumpSwap)")
        self.logger.info("Filtering: Pump.fun ONLY (excluding LaunchLab, Moonshot, etc.)")
        self.logger.info("Mode: OBSERVATION (analysis only, no trading)")
        self.logger.info("Dashboard: http://127.0.0.1:8050")
        self.logger.info("="*70)

        try:
            # Connect and subscribe to migrations/graduations
            await self.pumpportal.run(
                on_migration=self.handle_migration
            )

        except KeyboardInterrupt:
            self.logger.info("\nShutting down monitor...")
        except Exception as e:
            self.logger.error(f"Monitor error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            # Cleanup
            await self.pumpportal.disconnect()
            await self.agent.close()
            self._save_seen_tokens()
            self.logger.info("Monitor stopped")


async def main():
    """Main entry point"""
    setup_directories()

    # Create and run monitor
    monitor = PumpPortalGraduationMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
