"""
Cabal Wallet Tracking and Detection System

Tracks coordinated wallet groups (cabals) that manipulate token prices.
Provides win rates, risk scores, and detection of new cabal patterns.
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class CabalWallet:
    """Represents a known cabal wallet"""
    wallet_address: str
    cabal_name: str
    cabal_id: str
    notes: str = ""
    known_associations: List[str] = None  # Other wallets in same cabal
    winrate: float = 0.0  # % of profitable trades
    lifetime_pnl: float = 0.0  # Total SOL profit/loss
    lifetime_tokens_traded: int = 0
    avg_entry_mcap: float = 0.0  # Average market cap when they buy
    avg_exit_mcap: float = 0.0  # Average market cap when they sell
    first_seen: str = ""
    last_seen: str = ""
    risk_level: str = "UNKNOWN"  # BULLISH, NEUTRAL, TOXIC
    confidence_score: float = 0.0  # How confident we are this is a cabal wallet

    def __post_init__(self):
        if self.known_associations is None:
            self.known_associations = []

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)


class CabalTracker:
    """Tracks and identifies cabal wallets"""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize cabal tracker

        Args:
            data_dir: Directory to store cabal data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.cabal_db_file = self.data_dir / "cabal_wallets.json"
        self.cabal_activity_file = self.data_dir / "cabal_activity.json"

        # Load cabal database
        self.cabals: Dict[str, CabalWallet] = {}
        self.cabal_groups: Dict[str, List[str]] = {}  # cabal_id -> list of wallet addresses

        self._load_cabal_database()

        logger.info(f"Cabal Tracker initialized: {len(self.cabals)} known wallets across {len(self.cabal_groups)} cabals")

    def _load_cabal_database(self):
        """Load known cabals from disk"""
        if self.cabal_db_file.exists():
            try:
                with open(self.cabal_db_file, 'r') as f:
                    data = json.load(f)

                for wallet_data in data.get('wallets', []):
                    cabal = CabalWallet(**wallet_data)
                    self.cabals[cabal.wallet_address] = cabal

                    # Build cabal groups
                    if cabal.cabal_id not in self.cabal_groups:
                        self.cabal_groups[cabal.cabal_id] = []
                    self.cabal_groups[cabal.cabal_id].append(cabal.wallet_address)

                logger.info(f"Loaded {len(self.cabals)} cabal wallets from disk")
            except Exception as e:
                logger.error(f"Error loading cabal database: {e}")
                self._initialize_seed_cabals()
        else:
            logger.info("No existing cabal database found, initializing with seed data")
            self._initialize_seed_cabals()

    def _initialize_seed_cabals(self):
        """Initialize with some known seed cabal wallets"""
        # This is a starter set - you'll add real ones as you discover them
        seed_cabals = [
            # Example format - replace with real data
            {
                "wallet_address": "EXAMPLE1...",
                "cabal_name": "High Roller Crew",
                "cabal_id": "crew_001",
                "notes": "Seed example - replace with real data",
                "winrate": 0.75,
                "risk_level": "BULLISH",
                "confidence_score": 0.9
            },
        ]

        # Don't actually add the example
        logger.info("Cabal database initialized (empty - add real wallets)")
        self._save_cabal_database()

    def _save_cabal_database(self):
        """Save cabal database to disk"""
        try:
            data = {
                'wallets': [cabal.to_dict() for cabal in self.cabals.values()],
                'last_updated': datetime.now().isoformat(),
                'total_cabals': len(self.cabal_groups)
            }

            with open(self.cabal_db_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self.cabals)} cabal wallets to disk")
        except Exception as e:
            logger.error(f"Error saving cabal database: {e}")

    def add_cabal_wallet(self, wallet: CabalWallet):
        """
        Add a new cabal wallet to the tracker

        Args:
            wallet: CabalWallet to add
        """
        self.cabals[wallet.wallet_address] = wallet

        if wallet.cabal_id not in self.cabal_groups:
            self.cabal_groups[wallet.cabal_id] = []
        if wallet.wallet_address not in self.cabal_groups[wallet.cabal_id]:
            self.cabal_groups[wallet.cabal_id].append(wallet.wallet_address)

        self._save_cabal_database()
        logger.info(f"Added cabal wallet: {wallet.wallet_address[:8]}... ({wallet.cabal_name})")

    def is_cabal_wallet(self, wallet_address: str) -> bool:
        """Check if a wallet is a known cabal wallet"""
        return wallet_address in self.cabals

    def get_cabal_info(self, wallet_address: str) -> Optional[CabalWallet]:
        """Get information about a cabal wallet"""
        return self.cabals.get(wallet_address)

    def get_cabal_group(self, cabal_id: str) -> List[str]:
        """Get all wallet addresses in a cabal group"""
        return self.cabal_groups.get(cabal_id, [])

    def analyze_token_holders(self, holder_addresses: List[str]) -> Dict:
        """
        Analyze a token's holders for cabal involvement

        Args:
            holder_addresses: List of wallet addresses holding the token

        Returns:
            Dictionary with cabal analysis
        """
        if not holder_addresses:
            return {
                'has_cabal_involvement': False,
                'cabal_count': 0,
                'cabals_detected': [],
                'total_cabal_wallets': 0,
                'cabal_percentage': 0.0,
                'risk_assessment': 'NONE',
                'bullish_cabals': 0,
                'toxic_cabals': 0,
                'avg_cabal_winrate': 0.0
            }

        detected_cabals = set()
        cabal_wallets_found = []
        bullish_count = 0
        toxic_count = 0
        winrates = []

        for address in holder_addresses:
            if address in self.cabals:
                cabal = self.cabals[address]
                detected_cabals.add(cabal.cabal_id)
                cabal_wallets_found.append(cabal)

                if cabal.risk_level == 'BULLISH':
                    bullish_count += 1
                elif cabal.risk_level == 'TOXIC':
                    toxic_count += 1

                if cabal.winrate > 0:
                    winrates.append(cabal.winrate)

        # Determine overall risk
        if toxic_count > 0:
            risk_assessment = 'TOXIC'
        elif bullish_count > toxic_count:
            risk_assessment = 'BULLISH'
        elif len(detected_cabals) > 0:
            risk_assessment = 'NEUTRAL'
        else:
            risk_assessment = 'NONE'

        avg_winrate = np.mean(winrates) if winrates else 0.0

        return {
            'has_cabal_involvement': len(detected_cabals) > 0,
            'cabal_count': len(detected_cabals),
            'cabals_detected': [
                {
                    'cabal_id': c.cabal_id,
                    'cabal_name': c.cabal_name,
                    'winrate': c.winrate,
                    'risk_level': c.risk_level,
                    'wallet_count': len([w for w in cabal_wallets_found if w.cabal_id == c.cabal_id])
                }
                for c in set(cabal_wallets_found)
            ],
            'total_cabal_wallets': len(cabal_wallets_found),
            'cabal_percentage': (len(cabal_wallets_found) / len(holder_addresses)) * 100,
            'risk_assessment': risk_assessment,
            'bullish_cabals': bullish_count,
            'toxic_cabals': toxic_count,
            'avg_cabal_winrate': avg_winrate,
            'confidence_high': len(detected_cabals) >= 2  # Multiple cabals = high confidence signal
        }

    def detect_potential_cabal_pattern(
        self,
        wallet_addresses: List[str],
        buy_timestamps: List[datetime],
        buy_amounts: List[float]
    ) -> Optional[Dict]:
        """
        Detect potential new cabal patterns from trading behavior

        Args:
            wallet_addresses: List of wallet addresses
            buy_timestamps: List of buy timestamps
            buy_amounts: List of buy amounts in SOL

        Returns:
            Dictionary with potential cabal info, or None
        """
        if len(wallet_addresses) < 3:
            return None  # Need at least 3 wallets to identify a pattern

        # Check for coordinated buying patterns
        # 1. Buys within short time window (< 5 minutes)
        time_windows = []
        for i in range(len(buy_timestamps)):
            window_buys = []
            for j in range(len(buy_timestamps)):
                if i != j:
                    time_diff = abs((buy_timestamps[i] - buy_timestamps[j]).total_seconds())
                    if time_diff < 300:  # 5 minutes
                        window_buys.append((wallet_addresses[j], buy_amounts[j]))

            if len(window_buys) >= 2:
                time_windows.append({
                    'lead_wallet': wallet_addresses[i],
                    'coordinated_wallets': window_buys,
                    'timestamp': buy_timestamps[i]
                })

        if not time_windows:
            return None

        # 2. Similar buy amounts (within 20% of each other)
        amount_variance = np.std(buy_amounts) / np.mean(buy_amounts) if np.mean(buy_amounts) > 0 else 1

        if amount_variance < 0.2:  # Low variance = coordinated
            return {
                'pattern_detected': True,
                'confidence': 'HIGH' if len(time_windows) >= 3 else 'MEDIUM',
                'coordinated_wallets': list(set(wallet_addresses)),
                'pattern_type': 'COORDINATED_BUY',
                'evidence': {
                    'time_windows': len(time_windows),
                    'amount_variance': amount_variance,
                    'avg_buy_amount': np.mean(buy_amounts)
                }
            }

        return None

    def get_cabal_summary(self) -> Dict:
        """Get summary statistics about tracked cabals"""
        return {
            'total_cabals': len(self.cabal_groups),
            'total_wallets': len(self.cabals),
            'bullish_cabals': len([c for c in self.cabals.values() if c.risk_level == 'BULLISH']),
            'toxic_cabals': len([c for c in self.cabals.values() if c.risk_level == 'TOXIC']),
            'avg_winrate': np.mean([c.winrate for c in self.cabals.values() if c.winrate > 0]),
            'top_cabals': sorted(
                [
                    {
                        'cabal_id': cabal_id,
                        'name': self.cabals[wallets[0]].cabal_name if wallets else 'Unknown',
                        'wallet_count': len(wallets),
                        'avg_winrate': np.mean([self.cabals[w].winrate for w in wallets if w in self.cabals and self.cabals[w].winrate > 0])
                    }
                    for cabal_id, wallets in self.cabal_groups.items()
                ],
                key=lambda x: x.get('avg_winrate', 0),
                reverse=True
            )[:10]
        }


# Singleton instance
_cabal_tracker = None

def get_cabal_tracker() -> CabalTracker:
    """Get the global cabal tracker instance"""
    global _cabal_tracker
    if _cabal_tracker is None:
        _cabal_tracker = CabalTracker()
    return _cabal_tracker
