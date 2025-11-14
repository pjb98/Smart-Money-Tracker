"""
Smart Money & Cabal Wallet Detection System

Automatically discovers and tracks high-performing wallets based on:
- Pre-migration timing accuracy
- Post-migration performance
- Win rate and PnL tracking
- Meta participation
- Coordinated group behavior
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass, asdict, field
import numpy as np
from collections import defaultdict


@dataclass
class SmartMoneyWallet:
    """Represents a smart money wallet with performance tracking"""
    wallet_address: str

    # Performance metrics
    total_trades: int = 0
    profitable_trades: int = 0
    win_rate: float = 0.0
    pnl_total: float = 0.0

    # Timing signals
    pre_migration_buys: int = 0
    post_migration_buys: int = 0
    avg_entry_timing_minutes: float = 0.0  # negative = before migration

    # Size signals
    avg_buy_amount_sol: float = 0.0
    total_volume_sol: float = 0.0

    # Meta participation
    meta_tags: List[str] = field(default_factory=list)

    # Cabal score (0-100)
    cabal_score: float = 0.0

    # Tracking
    first_seen: str = ""
    last_seen: str = ""
    tokens_traded: List[str] = field(default_factory=list)

    # Cabal group (if detected as part of coordinated group)
    cabal_group_id: Optional[str] = None

    # Birdeye data
    birdeye_pnl: Optional[float] = None
    birdeye_last_updated: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class CabalGroup:
    """Represents a coordinated group of wallets"""
    group_id: str
    group_name: str
    wallet_addresses: List[str]
    avg_cabal_score: float = 0.0
    total_trades: int = 0
    group_win_rate: float = 0.0
    coordination_strength: float = 0.0  # 0-1, how coordinated they are
    meta_focus: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


class SmartMoneyTracker:
    """Tracks and identifies smart money wallets automatically"""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize smart money tracker

        Args:
            data_dir: Directory to store smart money data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.smart_money_db_file = self.data_dir / "smart_money_wallets.json"
        self.cabal_groups_file = self.data_dir / "cabal_groups.json"
        self.wallet_activity_file = self.data_dir / "wallet_activity_log.json"

        # Load databases
        self.wallets: Dict[str, SmartMoneyWallet] = {}
        self.cabal_groups: Dict[str, CabalGroup] = {}
        self.wallet_activity_log: List[Dict] = []

        self._load_databases()

        logger.info(f"Smart Money Tracker initialized: {len(self.wallets)} wallets, {len(self.cabal_groups)} cabal groups")

    def _load_databases(self):
        """Load all databases from disk"""
        # Load smart money wallets
        if self.smart_money_db_file.exists():
            try:
                with open(self.smart_money_db_file, 'r') as f:
                    data = json.load(f)

                for wallet_data in data.get('wallets', []):
                    wallet = SmartMoneyWallet(**wallet_data)
                    self.wallets[wallet.wallet_address] = wallet

                logger.info(f"Loaded {len(self.wallets)} smart money wallets")
            except Exception as e:
                logger.error(f"Error loading smart money database: {e}")

        # Load cabal groups
        if self.cabal_groups_file.exists():
            try:
                with open(self.cabal_groups_file, 'r') as f:
                    data = json.load(f)

                for group_data in data.get('groups', []):
                    group = CabalGroup(**group_data)
                    self.cabal_groups[group.group_id] = group

                logger.info(f"Loaded {len(self.cabal_groups)} cabal groups")
            except Exception as e:
                logger.error(f"Error loading cabal groups: {e}")

    def _save_databases(self):
        """Save all databases to disk"""
        try:
            # Save smart money wallets
            wallet_data = {
                'wallets': [wallet.to_dict() for wallet in self.wallets.values()],
                'last_updated': datetime.now().isoformat(),
                'total_wallets': len(self.wallets)
            }

            with open(self.smart_money_db_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)

            # Save cabal groups
            group_data = {
                'groups': [group.to_dict() for group in self.cabal_groups.values()],
                'last_updated': datetime.now().isoformat(),
                'total_groups': len(self.cabal_groups)
            }

            with open(self.cabal_groups_file, 'w') as f:
                json.dump(group_data, f, indent=2)

            logger.debug("Saved smart money databases")
        except Exception as e:
            logger.error(f"Error saving databases: {e}")

    def log_wallet_activity(
        self,
        wallet_address: str,
        token_address: str,
        action: str,  # 'buy' or 'sell'
        amount_sol: float,
        timestamp: datetime,
        pre_migration: bool = False
    ):
        """
        Log wallet activity for a token

        Args:
            wallet_address: Wallet address
            token_address: Token being traded
            action: 'buy' or 'sell'
            amount_sol: Amount in SOL
            timestamp: Transaction timestamp
            pre_migration: Whether this was before migration
        """
        activity = {
            'wallet_address': wallet_address,
            'token_address': token_address,
            'action': action,
            'amount_sol': amount_sol,
            'timestamp': timestamp.isoformat(),
            'pre_migration': pre_migration
        }

        self.wallet_activity_log.append(activity)

        # Update wallet if it exists, or track for potential smart money
        if wallet_address not in self.wallets:
            # Check if this wallet shows smart money characteristics
            if amount_sol >= 0.1:  # Minimum threshold
                self._consider_for_tracking(wallet_address, activity)

    def _consider_for_tracking(self, wallet_address: str, first_activity: Dict):
        """
        Evaluate if a wallet should be tracked as potential smart money

        Args:
            wallet_address: Wallet to evaluate
            first_activity: First observed activity
        """
        # For now, add any wallet with >0.1 SOL buys
        # Later we'll filter by performance
        wallet = SmartMoneyWallet(
            wallet_address=wallet_address,
            first_seen=first_activity['timestamp'],
            last_seen=first_activity['timestamp']
        )

        self.wallets[wallet_address] = wallet
        logger.debug(f"Started tracking wallet {wallet_address[:8]}... as potential smart money")

    def update_wallet_performance(
        self,
        wallet_address: str,
        token_address: str,
        pnl: float,
        is_profitable: bool,
        entry_timing_minutes: float = 0.0,
        meta_tag: Optional[str] = None
    ):
        """
        Update wallet performance after trade outcome is known

        Args:
            wallet_address: Wallet address
            token_address: Token traded
            pnl: Profit/loss in SOL
            is_profitable: Whether trade was profitable
            entry_timing_minutes: Minutes relative to migration (negative = before)
            meta_tag: Token meta (tech, burn, x402, etc.)
        """
        if wallet_address not in self.wallets:
            # Create wallet entry
            self.wallets[wallet_address] = SmartMoneyWallet(
                wallet_address=wallet_address,
                first_seen=datetime.now().isoformat(),
                last_seen=datetime.now().isoformat()
            )

        wallet = self.wallets[wallet_address]

        # Update metrics
        wallet.total_trades += 1
        if is_profitable:
            wallet.profitable_trades += 1

        wallet.pnl_total += pnl
        wallet.win_rate = wallet.profitable_trades / wallet.total_trades if wallet.total_trades > 0 else 0.0

        # Update timing
        if entry_timing_minutes < 0:
            wallet.pre_migration_buys += 1
        else:
            wallet.post_migration_buys += 1

        # Update average entry timing
        if wallet.total_trades > 0:
            wallet.avg_entry_timing_minutes = (
                (wallet.avg_entry_timing_minutes * (wallet.total_trades - 1) + entry_timing_minutes)
                / wallet.total_trades
            )

        # Add token to traded list
        if token_address not in wallet.tokens_traded:
            wallet.tokens_traded.append(token_address)

        # Add meta tag
        if meta_tag and meta_tag not in wallet.meta_tags:
            wallet.meta_tags.append(meta_tag)

        wallet.last_seen = datetime.now().isoformat()

        # Recalculate cabal score
        wallet.cabal_score = self._calculate_cabal_score(wallet)

        self._save_databases()

        logger.info(f"Updated wallet {wallet_address[:8]}... - Win Rate: {wallet.win_rate:.1%}, Cabal Score: {wallet.cabal_score:.0f}")

    def _calculate_cabal_score(self, wallet: SmartMoneyWallet) -> float:
        """
        Calculate 0-100 cabal score based on wallet performance

        Score Components:
        - Pre-Migration Timing: 20 points
        - PnL History: 25 points
        - Win Rate: 20 points
        - Buy Size: 10 points
        - Meta Participation: 10 points
        - Behavioral Consistency: 15 points

        Args:
            wallet: SmartMoneyWallet to score

        Returns:
            Score from 0-100
        """
        score = 0.0

        # 1. Pre-Migration Timing (20 points)
        if wallet.total_trades > 0:
            pre_migration_rate = wallet.pre_migration_buys / wallet.total_trades
            # Bonus for entering before migration
            if wallet.avg_entry_timing_minutes < -5:  # 5+ minutes before
                score += 20 * pre_migration_rate
            elif wallet.avg_entry_timing_minutes < 0:  # Any time before
                score += 15 * pre_migration_rate

        # 2. PnL History (25 points)
        if wallet.pnl_total > 0:
            # Scale based on total PnL
            pnl_score = min(25, (wallet.pnl_total / 100) * 25)  # Max at 100 SOL profit
            score += pnl_score

        # 3. Win Rate (20 points)
        score += wallet.win_rate * 20

        # 4. Buy Size (10 points)
        if wallet.avg_buy_amount_sol > 0:
            # Favor larger buys (not dust)
            if wallet.avg_buy_amount_sol >= 5.0:
                score += 10
            elif wallet.avg_buy_amount_sol >= 1.0:
                score += 7
            elif wallet.avg_buy_amount_sol >= 0.5:
                score += 5
            elif wallet.avg_buy_amount_sol >= 0.1:
                score += 3

        # 5. Meta Participation (10 points)
        meta_count = len(wallet.meta_tags)
        if meta_count >= 3:
            score += 10  # Diversified meta participation
        elif meta_count >= 2:
            score += 7
        elif meta_count >= 1:
            score += 4

        # 6. Behavioral Consistency (15 points)
        if wallet.total_trades >= 10:
            score += 15  # Proven track record
        elif wallet.total_trades >= 5:
            score += 10
        elif wallet.total_trades >= 3:
            score += 5

        return min(100.0, score)  # Cap at 100

    def detect_cabal_groups(self, min_coordination_strength: float = 0.6) -> List[CabalGroup]:
        """
        Detect coordinated wallet groups based on behavior patterns

        Args:
            min_coordination_strength: Minimum coordination score (0-1) to form a group

        Returns:
            List of detected CabalGroups
        """
        # Build token -> wallets mapping
        token_wallets = defaultdict(list)
        for wallet_addr, wallet in self.wallets.items():
            for token in wallet.tokens_traded:
                token_wallets[token].append(wallet_addr)

        # Find wallets that frequently trade the same tokens
        wallet_pairs = defaultdict(int)
        for token, wallets in token_wallets.items():
            if len(wallets) >= 2:
                # All pairs of wallets that traded this token
                for i, w1 in enumerate(wallets):
                    for w2 in wallets[i+1:]:
                        pair = tuple(sorted([w1, w2]))
                        wallet_pairs[pair] += 1

        # Cluster wallets into groups
        detected_groups = []
        grouped_wallets = set()

        for (w1, w2), shared_tokens in wallet_pairs.items():
            # Calculate coordination strength
            w1_total = len(self.wallets[w1].tokens_traded)
            w2_total = len(self.wallets[w2].tokens_traded)

            if w1_total == 0 or w2_total == 0:
                continue

            coordination = shared_tokens / min(w1_total, w2_total)

            if coordination >= min_coordination_strength:
                # Check if either wallet is already in a group
                existing_group = None
                for group in detected_groups:
                    if w1 in group or w2 in group:
                        existing_group = group
                        break

                if existing_group:
                    existing_group.add(w1)
                    existing_group.add(w2)
                else:
                    detected_groups.append({w1, w2})

                grouped_wallets.add(w1)
                grouped_wallets.add(w2)

        # Convert to CabalGroup objects
        cabal_groups = []
        for i, group_wallets in enumerate(detected_groups, 1):
            group_id = f"auto_cabal_{i:03d}"

            # Calculate group stats
            group_scores = [self.wallets[w].cabal_score for w in group_wallets if w in self.wallets]
            group_trades = sum(self.wallets[w].total_trades for w in group_wallets if w in self.wallets)
            group_wins = sum(self.wallets[w].profitable_trades for w in group_wallets if w in self.wallets)

            # Collect meta tags
            all_metas = []
            for w in group_wallets:
                if w in self.wallets:
                    all_metas.extend(self.wallets[w].meta_tags)

            from collections import Counter
            meta_focus = [meta for meta, count in Counter(all_metas).most_common(3)]

            cabal_group = CabalGroup(
                group_id=group_id,
                group_name=f"Cabal Group {i}",
                wallet_addresses=list(group_wallets),
                avg_cabal_score=np.mean(group_scores) if group_scores else 0,
                total_trades=group_trades,
                group_win_rate=group_wins / group_trades if group_trades > 0 else 0,
                coordination_strength=min_coordination_strength,
                meta_focus=meta_focus
            )

            cabal_groups.append(cabal_group)

            # Update wallets with group ID
            for wallet_addr in group_wallets:
                if wallet_addr in self.wallets:
                    self.wallets[wallet_addr].cabal_group_id = group_id

        # Save detected groups
        for group in cabal_groups:
            self.cabal_groups[group.group_id] = group

        self._save_databases()

        logger.info(f"Detected {len(cabal_groups)} cabal groups from {len(self.wallets)} wallets")
        return cabal_groups

    def analyze_token_smart_money(self, holder_addresses: List[str]) -> Dict:
        """
        Analyze a token's holders for smart money involvement

        Args:
            holder_addresses: List of wallet addresses holding the token

        Returns:
            Dictionary with smart money analysis
        """
        if not holder_addresses:
            return {
                'has_smart_money': False,
                'smart_money_count': 0,
                'avg_cabal_score': 0.0,
                'top_wallets': [],
                'cabal_groups_present': []
            }

        smart_wallets_found = []
        cabal_groups_present = set()

        for address in holder_addresses:
            if address in self.wallets:
                wallet = self.wallets[address]
                smart_wallets_found.append({
                    'address': address,
                    'cabal_score': wallet.cabal_score,
                    'win_rate': wallet.win_rate,
                    'total_trades': wallet.total_trades,
                    'cabal_group_id': wallet.cabal_group_id
                })

                if wallet.cabal_group_id:
                    cabal_groups_present.add(wallet.cabal_group_id)

        # Sort by cabal score
        smart_wallets_found.sort(key=lambda x: x['cabal_score'], reverse=True)

        avg_score = np.mean([w['cabal_score'] for w in smart_wallets_found]) if smart_wallets_found else 0.0

        return {
            'has_smart_money': len(smart_wallets_found) > 0,
            'smart_money_count': len(smart_wallets_found),
            'smart_money_percentage': (len(smart_wallets_found) / len(holder_addresses)) * 100,
            'avg_cabal_score': avg_score,
            'top_wallets': smart_wallets_found[:10],  # Top 10
            'cabal_groups_present': list(cabal_groups_present),
            'high_confidence': avg_score >= 75  # High confidence if avg score > 75
        }

    def get_top_performers(self, limit: int = 50) -> List[SmartMoneyWallet]:
        """
        Get top performing smart money wallets

        Args:
            limit: Maximum number of wallets to return

        Returns:
            List of top SmartMoneyWallets sorted by cabal score
        """
        sorted_wallets = sorted(
            self.wallets.values(),
            key=lambda w: w.cabal_score,
            reverse=True
        )

        return sorted_wallets[:limit]

    def get_summary_stats(self) -> Dict:
        """Get summary statistics about tracked smart money"""
        if not self.wallets:
            return {
                'total_wallets': 0,
                'avg_cabal_score': 0,
                'avg_win_rate': 0,
                'total_cabal_groups': 0
            }

        return {
            'total_wallets': len(self.wallets),
            'avg_cabal_score': np.mean([w.cabal_score for w in self.wallets.values()]),
            'avg_win_rate': np.mean([w.win_rate for w in self.wallets.values() if w.total_trades > 0]),
            'total_cabal_groups': len(self.cabal_groups),
            'high_performers': len([w for w in self.wallets.values() if w.cabal_score >= 75]),
            'total_trades_tracked': sum(w.total_trades for w in self.wallets.values())
        }


# Singleton instance
_smart_money_tracker = None

def get_smart_money_tracker() -> SmartMoneyTracker:
    """Get the global smart money tracker instance"""
    global _smart_money_tracker
    if _smart_money_tracker is None:
        _smart_money_tracker = SmartMoneyTracker()
    return _smart_money_tracker
