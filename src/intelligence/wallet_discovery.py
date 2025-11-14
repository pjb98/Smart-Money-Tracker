"""
Automatic Wallet Discovery System

Integrates with token analysis pipeline to automatically:
- Discover wallet activity from token holders
- Track wallet performance over time
- Build smart money database automatically
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
import json

from .smart_money_tracker import get_smart_money_tracker


class WalletDiscoveryEngine:
    """Automatically discovers and tracks wallets from token analysis"""

    def __init__(self):
        """Initialize wallet discovery engine"""
        self.tracker = get_smart_money_tracker()
        self.pending_tokens = {}  # token_address -> initial data
        logger.info("Wallet Discovery Engine initialized")

    def process_new_token(
        self,
        token_address: str,
        holders: List[Dict[str, Any]],
        migration_time: datetime,
        pre_migration_data: Optional[Dict] = None
    ):
        """
        Process a newly migrated token and log wallet activity

        Args:
            token_address: Token address
            holders: List of holder dicts with 'owner'/'address' and 'amount'
            migration_time: When token migrated
            pre_migration_data: Optional pre-migration trading data
        """
        logger.info(f"Processing new token {token_address[:8]}... with {len(holders)} holders")

        # Store initial data for later performance tracking
        self.pending_tokens[token_address] = {
            'migration_time': migration_time,
            'initial_holders': holders,
            'tracked_at': datetime.now()
        }

        # Log wallet activity for all holders
        for holder in holders:
            wallet_address = holder.get('owner') or holder.get('address')
            amount_tokens = holder.get('amount', 0)

            if not wallet_address:
                continue

            # Skip if amount is too small (dust)
            if amount_tokens < 1000:  # Threshold for meaningful position
                continue

            # Estimate SOL amount (rough conversion, will be updated later)
            estimated_sol = 0.1  # Default minimal amount

            # Determine if this was pre-migration buy
            pre_migration = False
            if pre_migration_data:
                pre_migration_buyers = pre_migration_data.get('early_buyers', [])
                pre_migration = wallet_address in pre_migration_buyers

            # Log the activity
            self.tracker.log_wallet_activity(
                wallet_address=wallet_address,
                token_address=token_address,
                action='buy',
                amount_sol=estimated_sol,
                timestamp=migration_time,
                pre_migration=pre_migration
            )

        logger.info(f"Logged activity for {len(holders)} wallets on token {token_address[:8]}...")

    def update_token_performance(
        self,
        token_address: str,
        final_price_multiplier: float,
        time_elapsed_minutes: int = 60,
        meta_tag: Optional[str] = None
    ):
        """
        Update wallet performance after observing token outcome

        Args:
            token_address: Token address
            final_price_multiplier: Price change (e.g., 2.0 = 2x, 0.5 = -50%)
            time_elapsed_minutes: Minutes since migration
            meta_tag: Token meta (tech, burn, x402, etc.)
        """
        if token_address not in self.pending_tokens:
            logger.warning(f"Token {token_address[:8]}... not found in pending tokens")
            return

        token_data = self.pending_tokens[token_address]
        holders = token_data['initial_holders']
        migration_time = token_data['migration_time']

        logger.info(f"Updating performance for {len(holders)} wallets on token {token_address[:8]}... ({final_price_multiplier:.2f}x)")

        # Update each wallet's performance
        for holder in holders:
            wallet_address = holder.get('owner') or holder.get('address')
            amount_tokens = holder.get('amount', 0)

            if not wallet_address or amount_tokens < 1000:
                continue

            # Calculate PnL (simplified - assumes sell at current price)
            # In reality, would need to track actual sells
            estimated_sol_invested = 0.1  # Rough estimate
            estimated_pnl = estimated_sol_invested * (final_price_multiplier - 1.0)
            is_profitable = final_price_multiplier > 1.0

            # Calculate entry timing (how many minutes before/after migration)
            # For now, assume all at migration time (0)
            # TODO: Get actual entry timing from pre-migration data
            entry_timing_minutes = 0

            # Update wallet performance
            self.tracker.update_wallet_performance(
                wallet_address=wallet_address,
                token_address=token_address,
                pnl=estimated_pnl,
                is_profitable=is_profitable,
                entry_timing_minutes=entry_timing_minutes,
                meta_tag=meta_tag
            )

        # Remove from pending
        del self.pending_tokens[token_address]
        logger.info(f"Completed performance update for token {token_address[:8]}...")

    def process_token_analysis_result(self, analysis_file: Path):
        """
        Process a complete token analysis result to extract wallet performance

        Args:
            analysis_file: Path to token analysis JSON file
        """
        try:
            with open(analysis_file, 'r') as f:
                data = json.load(f)

            token_address = data.get('token_address')
            if not token_address:
                return

            # Get migration time
            migration_time_str = data.get('migration_time')
            if migration_time_str:
                migration_time = datetime.fromisoformat(migration_time_str.replace('Z', '+00:00'))
            else:
                migration_time = datetime.now()

            # Get holders
            features = data.get('features', {})
            holders = data.get('holders', [])

            if not holders:
                logger.debug(f"No holder data for {token_address[:8]}...")
                return

            # Process initial token discovery
            self.process_new_token(
                token_address=token_address,
                holders=holders,
                migration_time=migration_time
            )

            # If we have performance data, update it
            # (This would come from tracking price 1 hour later)
            # For now, we'll set this up to be called manually or by monitoring system

        except Exception as e:
            logger.error(f"Error processing analysis file {analysis_file}: {e}")

    def auto_discover_from_results_dir(self, results_dir: Path = Path("data/results")):
        """
        Auto-discover wallets from all existing result files

        Args:
            results_dir: Directory containing analysis results
        """
        logger.info(f"Auto-discovering wallets from {results_dir}...")

        if not results_dir.exists():
            logger.warning(f"Results directory {results_dir} does not exist")
            return

        result_files = list(results_dir.glob("*.json"))
        logger.info(f"Found {len(result_files)} result files")

        processed = 0
        for file_path in result_files:
            try:
                self.process_token_analysis_result(file_path)
                processed += 1
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}")

        logger.info(f"Auto-discovery complete: processed {processed}/{len(result_files)} files")

        # Detect cabal groups
        groups = self.tracker.detect_cabal_groups(min_coordination_strength=0.6)
        logger.info(f"Detected {len(groups)} cabal groups")


# Singleton instance
_discovery_engine = None

def get_discovery_engine() -> WalletDiscoveryEngine:
    """Get the global wallet discovery engine instance"""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = WalletDiscoveryEngine()
    return _discovery_engine


# Standalone script for manual discovery
def main():
    """Run wallet discovery on existing results"""
    engine = get_discovery_engine()
    engine.auto_discover_from_results_dir()

    # Print summary
    tracker = get_smart_money_tracker()
    stats = tracker.get_summary_stats()

    print("\n=== Smart Money Discovery Complete ===")
    print(f"Total Wallets Tracked: {stats['total_wallets']}")
    print(f"High Performers (75+): {stats['high_performers']}")
    print(f"Avg Cabal Score: {stats['avg_cabal_score']:.1f}")
    print(f"Cabal Groups Detected: {stats['total_cabal_groups']}")

    # Show top 10
    top_wallets = tracker.get_top_performers(limit=10)
    print("\n=== Top 10 Wallets ===")
    for i, wallet in enumerate(top_wallets, 1):
        print(f"{i}. {wallet.wallet_address[:8]}... | Score: {wallet.cabal_score:.0f}/100 | Win Rate: {wallet.win_rate:.1%}")


if __name__ == "__main__":
    main()
