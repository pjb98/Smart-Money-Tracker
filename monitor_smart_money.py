"""
Smart Money Continuous Monitor

Automatically discovers and tracks smart money wallets by:
1. Watching for new token analysis results
2. Extracting wallet addresses from holders
3. Tracking wallet performance over time
4. Periodically detecting cabal groups
5. Updating Birdeye PnL data

Run this continuously in the background alongside your other monitors.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from intelligence.smart_money_tracker import get_smart_money_tracker
from intelligence.wallet_discovery import get_discovery_engine
from ingestion.birdeye_client import BirdeyeClient


class SmartMoneyMonitor(FileSystemEventHandler):
    """Monitor for new token analysis results and track wallets"""

    def __init__(self, results_dir: Path = Path("data/results")):
        """
        Initialize smart money monitor

        Args:
            results_dir: Directory to watch for new analysis results
        """
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.tracker = get_smart_money_tracker()
        self.discovery_engine = get_discovery_engine()

        # Track processed files to avoid duplicates
        self.processed_files = set()

        # Track tokens pending performance update
        self.pending_performance_updates = {}

        # Birdeye client (optional)
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            birdeye_key = os.getenv('BIRDEYE_API_KEY', 'public')
            self.birdeye_client = BirdeyeClient(api_key=birdeye_key)
            logger.info("Birdeye client initialized for PnL tracking")
        except Exception as e:
            logger.warning(f"Could not initialize Birdeye client: {e}")
            self.birdeye_client = None

        # Stats
        self.tokens_processed = 0
        self.wallets_discovered = 0
        self.groups_detected = 0

        logger.info(f"Smart Money Monitor initialized, watching {results_dir}")

    def on_created(self, event):
        """Handle new file creation in results directory"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process JSON files
        if file_path.suffix != '.json':
            return

        # Avoid processing the same file multiple times
        if str(file_path) in self.processed_files:
            return

        logger.info(f"New token analysis detected: {file_path.name}")
        self.process_token_analysis(file_path)

    def process_token_analysis(self, file_path: Path):
        """
        Process a token analysis result file

        Args:
            file_path: Path to JSON analysis file
        """
        try:
            # Mark as processed
            self.processed_files.add(str(file_path))

            # Wait a moment to ensure file is fully written
            time.sleep(0.5)

            # Read analysis data
            with open(file_path, 'r') as f:
                data = json.load(f)

            token_address = data.get('token_address')
            if not token_address:
                logger.warning(f"No token address in {file_path.name}")
                return

            # Get migration time
            migration_time_str = data.get('migration_time')
            if migration_time_str:
                migration_time = datetime.fromisoformat(migration_time_str.replace('Z', '+00:00'))
            else:
                migration_time = datetime.now()

            # Get holders
            holders = data.get('holders', [])
            if not holders:
                # Try to get from features
                features = data.get('features', {})
                holders = features.get('holders', [])

            if not holders:
                logger.debug(f"No holders found for {token_address[:8]}...")
                return

            logger.info(f"Processing {len(holders)} holders for token {token_address[:8]}...")

            # Process with discovery engine
            self.discovery_engine.process_new_token(
                token_address=token_address,
                holders=holders,
                migration_time=migration_time
            )

            # Schedule performance update in 60 minutes
            update_time = datetime.now() + timedelta(minutes=60)
            self.pending_performance_updates[token_address] = {
                'file_path': file_path,
                'update_time': update_time,
                'migration_time': migration_time
            }

            self.tokens_processed += 1
            self.wallets_discovered += len(holders)

            logger.info(f"Processed token {token_address[:8]}... - Total tokens: {self.tokens_processed}, Wallets: {self.wallets_discovered}")

        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")

    async def update_pending_performances(self):
        """Check for tokens that need performance updates"""
        now = datetime.now()
        tokens_to_update = []

        for token_address, data in list(self.pending_performance_updates.items()):
            if now >= data['update_time']:
                tokens_to_update.append((token_address, data))

        for token_address, data in tokens_to_update:
            await self.update_token_performance(token_address, data)
            del self.pending_performance_updates[token_address]

    async def update_token_performance(self, token_address: str, data: Dict):
        """
        Update wallet performance for a token after tracking period

        Args:
            token_address: Token address
            data: Token data including file path
        """
        try:
            logger.info(f"Updating performance for token {token_address[:8]}...")

            # Try to get current price data (simplified - would need price tracking)
            # For now, use a heuristic based on time elapsed
            time_elapsed = (datetime.now() - data['migration_time']).total_seconds() / 60

            # Estimate price multiplier (this is simplified - real version would track actual price)
            # Assume most tokens either pump early or dump
            # You would replace this with actual price tracking from DexScreener or Birdeye
            price_multiplier = 1.2  # Default modest pump

            # Try to get real data from file if available
            try:
                with open(data['file_path'], 'r') as f:
                    analysis = json.load(f)

                # Check if we have price tracking data
                features = analysis.get('features', {})
                # Add your price tracking logic here

            except:
                pass

            # Determine meta tag from analysis
            meta_tag = None
            try:
                with open(data['file_path'], 'r') as f:
                    analysis = json.load(f)

                # Try to extract meta from token name or description
                token_data = analysis.get('token_data', {})
                name = token_data.get('name', '').lower()
                desc = token_data.get('description', '').lower()

                if 'tech' in name or 'ai' in name:
                    meta_tag = 'tech'
                elif 'burn' in name or 'deflationary' in name:
                    meta_tag = 'burn'
                elif 'x402' in name:
                    meta_tag = 'x402'
                elif 'meme' in name:
                    meta_tag = 'meme'

            except:
                pass

            # Update performance
            self.discovery_engine.update_token_performance(
                token_address=token_address,
                final_price_multiplier=price_multiplier,
                time_elapsed_minutes=int(time_elapsed),
                meta_tag=meta_tag
            )

            logger.info(f"Performance updated for {token_address[:8]}... ({price_multiplier:.2f}x)")

        except Exception as e:
            logger.error(f"Error updating performance for {token_address}: {e}")

    async def detect_cabal_groups_periodically(self):
        """Periodically detect new cabal groups"""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour

                logger.info("Running cabal group detection...")
                groups = self.tracker.detect_cabal_groups(min_coordination_strength=0.6)
                self.groups_detected = len(groups)

                logger.info(f"Detected {len(groups)} cabal groups")

                # Log group details
                for group in groups:
                    logger.info(f"  {group.group_name}: {len(group.wallet_addresses)} wallets, "
                              f"Score: {group.avg_cabal_score:.1f}, "
                              f"Win Rate: {group.group_win_rate:.1%}")

            except Exception as e:
                logger.error(f"Error detecting cabal groups: {e}")

    async def update_birdeye_pnl_periodically(self):
        """Periodically update PnL data from Birdeye for tracked wallets"""
        if not self.birdeye_client:
            logger.info("Birdeye client not available, skipping PnL updates")
            return

        while True:
            try:
                await asyncio.sleep(1800)  # Every 30 minutes

                # Get top wallets to update
                top_wallets = self.tracker.get_top_performers(limit=20)

                if not top_wallets:
                    logger.debug("No wallets to update PnL for")
                    continue

                logger.info(f"Updating Birdeye PnL for {len(top_wallets)} top wallets...")

                for wallet in top_wallets:
                    try:
                        # Get wallet win rate from Birdeye
                        pnl_data = await self.birdeye_client.get_wallet_win_rate(
                            wallet.wallet_address,
                            min_trades=3
                        )

                        if pnl_data and pnl_data.get('total_trades', 0) > 0:
                            # Update wallet with Birdeye data
                            wallet.birdeye_pnl = pnl_data.get('total_pnl', 0)
                            wallet.birdeye_last_updated = datetime.now().isoformat()

                            logger.debug(f"Updated PnL for {wallet.wallet_address[:8]}...: "
                                       f"{pnl_data.get('total_pnl', 0):.2f} SOL")

                        # Rate limiting
                        await asyncio.sleep(2)

                    except Exception as e:
                        logger.warning(f"Error updating PnL for {wallet.wallet_address[:8]}...: {e}")

                # Save updated data
                self.tracker._save_databases()
                logger.info("Birdeye PnL update complete")

            except Exception as e:
                logger.error(f"Error in Birdeye PnL update cycle: {e}")

    async def check_pending_updates_periodically(self):
        """Periodically check for pending performance updates"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                await self.update_pending_performances()
            except Exception as e:
                logger.error(f"Error checking pending updates: {e}")

    async def print_stats_periodically(self):
        """Print statistics periodically"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                stats = self.tracker.get_summary_stats()

                logger.info("=== Smart Money Monitor Stats ===")
                logger.info(f"Tokens Processed: {self.tokens_processed}")
                logger.info(f"Wallets Discovered: {self.wallets_discovered}")
                logger.info(f"Total Wallets Tracked: {stats['total_wallets']}")
                logger.info(f"High Performers (75+): {stats['high_performers']}")
                logger.info(f"Avg Cabal Score: {stats['avg_cabal_score']:.1f}")
                logger.info(f"Cabal Groups: {stats['total_cabal_groups']}")
                logger.info(f"Pending Performance Updates: {len(self.pending_performance_updates)}")
                logger.info("================================")

            except Exception as e:
                logger.error(f"Error printing stats: {e}")

    def scan_existing_files(self):
        """Scan existing result files on startup"""
        logger.info("Scanning existing result files...")

        existing_files = sorted(self.results_dir.glob("*.json"))
        logger.info(f"Found {len(existing_files)} existing files")

        for file_path in existing_files:
            if str(file_path) not in self.processed_files:
                self.process_token_analysis(file_path)

        logger.info("Existing file scan complete")

    async def run_async(self):
        """Run all async monitoring tasks"""
        # Start all monitoring tasks
        tasks = [
            self.detect_cabal_groups_periodically(),
            self.update_birdeye_pnl_periodically(),
            self.check_pending_updates_periodically(),
            self.print_stats_periodically()
        ]

        await asyncio.gather(*tasks)

    def run(self):
        """Run the smart money monitor"""
        logger.info("🔥 Starting Smart Money Monitor...")

        # Scan existing files first
        self.scan_existing_files()

        # Start file system observer
        observer = Observer()
        observer.schedule(self, str(self.results_dir), recursive=False)
        observer.start()

        logger.info(f"Watching {self.results_dir} for new token analyses...")

        # Run async tasks
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("Shutting down Smart Money Monitor...")
            observer.stop()
            observer.join()


def main():
    """Main entry point"""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/smart_money_monitor.log",
        rotation="100 MB",
        retention="7 days",
        level="DEBUG"
    )

    # Create and run monitor
    monitor = SmartMoneyMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
