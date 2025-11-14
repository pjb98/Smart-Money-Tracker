"""
Feature engineering pipeline for token prediction
Computes on-chain, social, and temporal features from raw data
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from collections import Counter
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from ingestion.helius_client import HeliusClient
except ImportError:
    HeliusClient = None
    logger.warning("HeliusClient not available - dev credibility features will be disabled")

try:
    from intelligence.cabal_tracker import get_cabal_tracker
except ImportError:
    get_cabal_tracker = None
    logger.warning("CabalTracker not available - cabal detection features will be disabled")


class FeatureEngineer:
    """Compute ML-ready features from raw token data"""

    def __init__(self, lookback_windows: List[int] = None, helius_client: Optional['HeliusClient'] = None):
        """
        Initialize feature engineer

        Args:
            lookback_windows: Time windows (seconds) for rolling aggregations
            helius_client: Optional Helius client for dev credibility features
        """
        self.lookback_windows = lookback_windows or [
            60,      # 1 minute
            300,     # 5 minutes
            900,     # 15 minutes
            3600,    # 1 hour
            21600,   # 6 hours
            86400    # 24 hours
        ]
        self.helius_client = helius_client
        logger.info("Initialized feature engineer")

    def compute_temporal_features(
        self,
        token_data: Dict[str, Any],
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        Compute temporal features

        Args:
            token_data: Token metadata
            current_time: Current timestamp (migration time)

        Returns:
            Dict of temporal features
        """
        features = {}

        # Time of day / week patterns
        features['hour_of_day'] = current_time.hour
        features['day_of_week'] = current_time.weekday()
        features['is_weekend'] = int(current_time.weekday() >= 5)

        # Token age features
        if 'created_at' in token_data:
            created_time = datetime.fromisoformat(token_data['created_at'].replace('Z', '+00:00'))
            # Ensure current_time has timezone info if created_time does
            if created_time.tzinfo is not None and current_time.tzinfo is None:
                from datetime import timezone
                current_time = current_time.replace(tzinfo=timezone.utc)
            age_seconds = (current_time - created_time).total_seconds()
            features['token_age_hours'] = age_seconds / 3600
            features['token_age_days'] = age_seconds / 86400
        else:
            features['token_age_hours'] = 0
            features['token_age_days'] = 0

        # Time since first liquidity (if available)
        if 'first_liquidity_time' in token_data:
            first_liq_time = datetime.fromisoformat(token_data['first_liquidity_time'].replace('Z', '+00:00'))
            # Ensure current_time has timezone info if first_liq_time does
            if first_liq_time.tzinfo is not None and current_time.tzinfo is None:
                from datetime import timezone
                current_time = current_time.replace(tzinfo=timezone.utc)
            time_since_liq = (current_time - first_liq_time).total_seconds()
            features['time_since_first_liq_hours'] = time_since_liq / 3600
        else:
            features['time_since_first_liq_hours'] = 0

        return features

    def compute_liquidity_features(
        self,
        pool_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute liquidity and pool-related features

        Args:
            pool_data: Raydium pool information

        Returns:
            Dict of liquidity features
        """
        features = {}

        # Initial liquidity
        features['initial_liquidity_sol'] = pool_data.get('initial_liquidity_sol', 0)
        features['initial_liquidity_usd'] = pool_data.get('initial_liquidity_usd', 0)

        # Pool depth and ratios
        token_reserve = pool_data.get('token_reserve', 0)
        sol_reserve = pool_data.get('sol_reserve', 0)

        features['token_reserve'] = token_reserve
        features['sol_reserve'] = sol_reserve

        if token_reserve > 0 and sol_reserve > 0:
            features['reserve_ratio'] = sol_reserve / token_reserve
        else:
            features['reserve_ratio'] = 0

        # LP providers
        features['lp_provider_count'] = pool_data.get('lp_provider_count', 0)
        features['pool_locked'] = int(pool_data.get('liquidity_locked', False))

        # Price and slippage estimates
        features['initial_price_sol'] = pool_data.get('initial_price_sol', 0)

        return features

    def compute_transaction_features(
        self,
        transactions: List[Dict[str, Any]],
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        Compute transaction-based features

        Args:
            transactions: List of transaction dicts
            current_time: Reference time for windowing

        Returns:
            Dict of transaction features
        """
        features = {}

        if not transactions:
            # Return zeros if no transactions
            for window in self.lookback_windows:
                window_label = self._window_label(window)
                features[f'tx_count_{window_label}'] = 0
                features[f'unique_wallets_{window_label}'] = 0
            return features

        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        if 'block_time' not in df.columns:
            return features

        df['timestamp'] = pd.to_datetime(df['block_time'], unit='s')

        # Compute for each lookback window
        for window_seconds in self.lookback_windows:
            window_label = self._window_label(window_seconds)
            window_start = current_time - timedelta(seconds=window_seconds)

            window_txs = df[df['timestamp'] >= window_start]

            features[f'tx_count_{window_label}'] = len(window_txs)

            # Unique wallets (if available)
            if 'from_address' in window_txs.columns:
                features[f'unique_wallets_{window_label}'] = window_txs['from_address'].nunique()
            else:
                features[f'unique_wallets_{window_label}'] = 0

        return features

    def compute_holder_features(
        self,
        holders: List[Dict[str, Any]],
        total_supply: float
    ) -> Dict[str, Any]:
        """
        Compute holder distribution features

        Args:
            holders: List of holder dicts with amounts
            total_supply: Total token supply

        Returns:
            Dict of holder features
        """
        features = {}

        if not holders or total_supply == 0:
            features['holder_count'] = 0
            features['top1_holder_pct'] = 0
            features['top5_holder_pct'] = 0
            features['top10_holder_pct'] = 0
            features['gini_coefficient'] = 0
            return features

        # Sort by amount descending
        sorted_holders = sorted(holders, key=lambda x: x.get('amount', 0), reverse=True)

        features['holder_count'] = len(sorted_holders)

        # Top holder percentages
        if len(sorted_holders) >= 1:
            features['top1_holder_pct'] = sorted_holders[0]['amount'] / total_supply
        else:
            features['top1_holder_pct'] = 0

        if len(sorted_holders) >= 5:
            top5_amount = sum(h['amount'] for h in sorted_holders[:5])
            features['top5_holder_pct'] = top5_amount / total_supply
        else:
            features['top5_holder_pct'] = features['top1_holder_pct']

        if len(sorted_holders) >= 10:
            top10_amount = sum(h['amount'] for h in sorted_holders[:10])
            features['top10_holder_pct'] = top10_amount / total_supply
        else:
            features['top10_holder_pct'] = features['top5_holder_pct']

        # Gini coefficient for wealth distribution
        features['gini_coefficient'] = self._compute_gini([h['amount'] for h in sorted_holders])

        return features

    def compute_social_features(
        self,
        phanes_data: Optional[Dict[str, Any]] = None,
        twitter_data: Optional[Dict[str, Any]] = None,
        twitter_account_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compute social signal features

        Args:
            phanes_data: Phanes bot scan metrics
            twitter_data: Twitter mention/sentiment data (legacy)
            twitter_account_analysis: Comprehensive Twitter account analysis from TwitterAnalyzer

        Returns:
            Dict of social features
        """
        features = {}

        # Phanes features
        if phanes_data:
            features['phanes_scan_count'] = phanes_data.get('scan_count', 0)
            features['phanes_scan_velocity'] = phanes_data.get('avg_scan_velocity', 0)
            features['phanes_popularity_rank'] = phanes_data.get('latest_rank', 999)
            features['phanes_rug_warning'] = int(phanes_data.get('rug_warning', False))
            features['phanes_sentiment_score'] = phanes_data.get('avg_sentiment_score', 0)
        else:
            features['phanes_scan_count'] = 0
            features['phanes_scan_velocity'] = 0
            features['phanes_popularity_rank'] = 999
            features['phanes_rug_warning'] = 0
            features['phanes_sentiment_score'] = 0

        # Legacy Twitter mention features (backwards compatible)
        if twitter_data:
            features['twitter_mention_count_1h'] = twitter_data.get('mentions_1h', 0)
            features['twitter_mention_count_24h'] = twitter_data.get('mentions_24h', 0)
            features['twitter_sentiment_score'] = twitter_data.get('sentiment_score', 0)
            features['twitter_influencer_mentions'] = twitter_data.get('influencer_count', 0)
        else:
            features['twitter_mention_count_1h'] = 0
            features['twitter_mention_count_24h'] = 0
            features['twitter_sentiment_score'] = 0
            features['twitter_influencer_mentions'] = 0

        # NEW: Comprehensive Twitter account analysis features
        if twitter_account_analysis and not twitter_account_analysis.get('limited_data'):
            # Account age features
            age_analysis = twitter_account_analysis.get('age_analysis', {})
            features['twitter_account_age_days'] = age_analysis.get('account_age_days', 0)
            features['twitter_account_is_new'] = int(age_analysis.get('is_new_account', False))
            features['twitter_account_is_very_new'] = int(age_analysis.get('is_very_new_account', False))

            # Follower metrics
            follower_analysis = twitter_account_analysis.get('follower_analysis', {})
            features['twitter_followers'] = follower_analysis.get('followers_count', 0)
            features['twitter_following'] = follower_analysis.get('following_count', 0)
            features['twitter_follower_ratio'] = follower_analysis.get('follower_following_ratio', 0)
            features['twitter_low_followers'] = int(follower_analysis.get('low_follower_count', False))
            features['twitter_suspicious_following'] = int(follower_analysis.get('suspicious_following_ratio', False))

            # Engagement metrics
            engagement_analysis = twitter_account_analysis.get('engagement_analysis', {})
            features['twitter_avg_engagement'] = engagement_analysis.get('avg_engagement_rate', 0)
            features['twitter_low_engagement'] = int(engagement_analysis.get('low_engagement', False))
            features['twitter_tweets_analyzed'] = engagement_analysis.get('total_tweets_analyzed', 0)

            # Frequency metrics (bot detection)
            frequency_analysis = twitter_account_analysis.get('frequency_analysis', {})
            features['twitter_tweets_per_day'] = frequency_analysis.get('tweets_per_day', 0)
            features['twitter_excessive_frequency'] = int(frequency_analysis.get('excessive_tweet_frequency', False))

            # Sentiment from tweets
            sentiment_analysis = twitter_account_analysis.get('sentiment_analysis', {})
            features['twitter_account_sentiment'] = sentiment_analysis.get('avg_sentiment_polarity', 0)
            features['twitter_positive_ratio'] = sentiment_analysis.get('positive_tweet_ratio', 0)

            # Account verification and risk
            account_info = twitter_account_analysis.get('account_info', {})
            features['twitter_verified'] = int(account_info.get('verified', False))
            features['twitter_risk_score'] = twitter_account_analysis.get('risk_score', 5.0)
            features['twitter_has_account'] = 1

        else:
            # No Twitter account or limited data - set defaults
            features['twitter_account_age_days'] = 0
            features['twitter_account_is_new'] = 0
            features['twitter_account_is_very_new'] = 0
            features['twitter_followers'] = 0
            features['twitter_following'] = 0
            features['twitter_follower_ratio'] = 0
            features['twitter_low_followers'] = 1  # Flag as missing
            features['twitter_suspicious_following'] = 0
            features['twitter_avg_engagement'] = 0
            features['twitter_low_engagement'] = 1  # Flag as missing
            features['twitter_tweets_analyzed'] = 0
            features['twitter_tweets_per_day'] = 0
            features['twitter_excessive_frequency'] = 0
            features['twitter_account_sentiment'] = 0
            features['twitter_positive_ratio'] = 0
            features['twitter_verified'] = 0
            features['twitter_risk_score'] = 5.0  # Neutral risk
            features['twitter_has_account'] = 0  # No account linked

        return features

    def compute_dev_credibility_features(
        self,
        dev_wallet: Optional[str] = None,
        token_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compute developer credibility features using Helius

        Args:
            dev_wallet: Developer wallet address
            token_data: Token metadata (may contain dev wallet)

        Returns:
            Dict of dev credibility features
        """
        features = {}

        # Default values if no dev wallet or Helius client
        features['dev_credibility_score'] = 50.0  # Neutral score
        features['dev_wallet_age_days'] = 0
        features['dev_tokens_created_count'] = 0
        features['dev_large_sells_count'] = 0
        features['dev_rug_indicators_count'] = 0
        features['dev_is_new_wallet'] = 0
        features['dev_has_quick_dump_pattern'] = 0

        # Try to get dev wallet from token_data if not provided
        if not dev_wallet and token_data:
            dev_wallet = token_data.get('creator', token_data.get('authority', token_data.get('dev_wallet')))

        # Skip if no dev wallet or Helius client
        if not dev_wallet or not self.helius_client:
            if not self.helius_client:
                logger.debug("Helius client not available - skipping dev credibility features")
            else:
                logger.debug("No dev wallet provided - skipping dev credibility features")
            return features

        try:
            # Analyze dev wallet using Helius
            logger.info(f"Computing dev credibility for {dev_wallet[:8]}...")
            analysis = self.helius_client.analyze_dev_wallet_history(dev_wallet, lookback_days=90)

            # Extract features from analysis
            features['dev_credibility_score'] = analysis.get('credibility_score', 50.0)
            features['dev_wallet_age_days'] = analysis.get('wallet_age_days', 0)
            features['dev_tokens_created_count'] = len(analysis.get('created_tokens', []))
            features['dev_large_sells_count'] = len(analysis.get('large_sells', []))
            features['dev_rug_indicators_count'] = len(analysis.get('rug_pull_indicators', []))

            # Binary flags
            features['dev_is_new_wallet'] = int(features['dev_wallet_age_days'] < 7)
            features['dev_has_quick_dump_pattern'] = int(features['dev_rug_indicators_count'] > 0)

            # Risk category (inverse of credibility)
            if features['dev_credibility_score'] < 30:
                features['dev_risk_category'] = 2  # High risk
            elif features['dev_credibility_score'] < 60:
                features['dev_risk_category'] = 1  # Medium risk
            else:
                features['dev_risk_category'] = 0  # Low risk

            logger.info(f"Dev credibility: {features['dev_credibility_score']:.1f}/100 (Risk: {features['dev_risk_category']})")

        except Exception as e:
            logger.error(f"Error computing dev credibility: {e}")
            # Keep default values

        return features

    def compute_cabal_features(
        self,
        holders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute cabal detection features using wallet intelligence

        Args:
            holders: List of holder dicts with wallet addresses

        Returns:
            Dict of cabal detection features
        """
        features = {}

        # Default values if cabal tracker not available
        features['cabal_involvement'] = 0  # Binary flag
        features['cabal_count'] = 0
        features['cabal_total_wallets'] = 0
        features['cabal_percentage'] = 0.0
        features['cabal_avg_winrate'] = 0.0
        features['cabal_risk_score'] = 0.0  # 0=NONE, 1=NEUTRAL, 2=BULLISH, 3=TOXIC
        features['cabal_confidence_high'] = 0  # Binary: 2+ cabals detected
        features['cabal_bullish_count'] = 0
        features['cabal_toxic_count'] = 0

        if not get_cabal_tracker or not holders:
            logger.debug("Cabal tracker not available or no holders - skipping cabal features")
            return features

        try:
            # Get cabal tracker instance
            cabal_tracker = get_cabal_tracker()

            # Extract holder addresses
            holder_addresses = [h.get('owner', h.get('address', '')) for h in holders if h.get('owner') or h.get('address')]

            if not holder_addresses:
                logger.debug("No holder addresses found - skipping cabal analysis")
                return features

            # Analyze holders for cabal involvement
            logger.info(f"Analyzing {len(holder_addresses)} holders for cabal involvement...")
            cabal_analysis = cabal_tracker.analyze_token_holders(holder_addresses)

            # Extract features from analysis
            features['cabal_involvement'] = int(cabal_analysis.get('has_cabal_involvement', False))
            features['cabal_count'] = cabal_analysis.get('cabal_count', 0)
            features['cabal_total_wallets'] = cabal_analysis.get('total_cabal_wallets', 0)
            features['cabal_percentage'] = cabal_analysis.get('cabal_percentage', 0.0)
            features['cabal_avg_winrate'] = cabal_analysis.get('avg_cabal_winrate', 0.0)
            features['cabal_confidence_high'] = int(cabal_analysis.get('confidence_high', False))
            features['cabal_bullish_count'] = cabal_analysis.get('bullish_cabals', 0)
            features['cabal_toxic_count'] = cabal_analysis.get('toxic_cabals', 0)

            # Map risk assessment to numeric score
            risk_assessment = cabal_analysis.get('risk_assessment', 'NONE')
            risk_map = {'NONE': 0, 'NEUTRAL': 1, 'BULLISH': 2, 'TOXIC': 3}
            features['cabal_risk_score'] = risk_map.get(risk_assessment, 0)

            # Store full analysis for Claude (non-numeric data)
            features['cabal_analysis_full'] = cabal_analysis

            if features['cabal_involvement']:
                logger.info(f"Cabal detection: {features['cabal_count']} cabals, "
                           f"{features['cabal_total_wallets']} wallets ({features['cabal_percentage']:.1f}%), "
                           f"Risk: {risk_assessment}")

        except Exception as e:
            logger.error(f"Error computing cabal features: {e}")
            # Keep default values

        return features

    def compute_derived_features(
        self,
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute derived and interaction features

        Args:
            features: Base feature dict

        Returns:
            Enhanced feature dict with derived features
        """
        derived = {}

        # Liquidity per holder
        if features.get('holder_count', 0) > 0:
            derived['liquidity_per_holder'] = (
                features.get('initial_liquidity_sol', 0) / features['holder_count']
            )
        else:
            derived['liquidity_per_holder'] = 0

        # Social momentum (scan velocity * mention count)
        derived['social_momentum'] = (
            features.get('phanes_scan_velocity', 0) *
            features.get('twitter_mention_count_1h', 0)
        )

        # Concentration risk (top holder % * rug warning)
        derived['concentration_risk'] = (
            features.get('top1_holder_pct', 0) *
            (1 + features.get('phanes_rug_warning', 0))
        )

        # Transaction velocity per holder
        if features.get('holder_count', 0) > 0:
            derived['tx_velocity_per_holder'] = (
                features.get('tx_count_1h', 0) / features['holder_count']
            )
        else:
            derived['tx_velocity_per_holder'] = 0

        return derived

    def build_feature_vector(
        self,
        token_address: str,
        migration_time: datetime,
        token_data: Dict[str, Any],
        pool_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        holders: List[Dict[str, Any]],
        phanes_data: Optional[Dict[str, Any]] = None,
        twitter_data: Optional[Dict[str, Any]] = None,
        twitter_account_analysis: Optional[Dict[str, Any]] = None,
        dev_wallet: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build complete feature vector for a token at migration time

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            token_data: Token metadata
            pool_data: Pool information
            transactions: Transaction history
            holders: Holder list
            phanes_data: Phanes scan data
            twitter_data: Twitter mention data (legacy)
            twitter_account_analysis: Comprehensive Twitter account analysis
            dev_wallet: Developer wallet address (optional)

        Returns:
            Complete feature dict
        """
        features = {
            'token_address': token_address,
            'migration_time': migration_time.isoformat(),
        }

        # Compute feature groups
        features.update(self.compute_temporal_features(token_data, migration_time))
        features.update(self.compute_liquidity_features(pool_data))
        features.update(self.compute_transaction_features(transactions, migration_time))

        total_supply = token_data.get('supply', 1)
        features.update(self.compute_holder_features(holders, total_supply))
        features.update(self.compute_social_features(phanes_data, twitter_data, twitter_account_analysis))

        # Compute dev credibility features
        features.update(self.compute_dev_credibility_features(dev_wallet, token_data))

        # Compute cabal detection features (NEW!)
        features.update(self.compute_cabal_features(holders))

        features.update(self.compute_derived_features(features))

        logger.debug(f"Built feature vector with {len(features)} features for {token_address}")
        return features

    @staticmethod
    def _window_label(seconds: int) -> str:
        """Convert seconds to human-readable label"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        elif seconds < 86400:
            return f"{seconds // 3600}h"
        else:
            return f"{seconds // 86400}d"

    @staticmethod
    def _compute_gini(amounts: List[float]) -> float:
        """
        Compute Gini coefficient for wealth distribution

        Args:
            amounts: List of amounts

        Returns:
            Gini coefficient (0 = perfect equality, 1 = perfect inequality)
        """
        if not amounts or len(amounts) == 1:
            return 0.0

        sorted_amounts = sorted(amounts)
        n = len(sorted_amounts)
        cumsum = np.cumsum(sorted_amounts)
        total = cumsum[-1]

        if total == 0:
            return 0.0

        # Gini = (2 * sum(i * x_i)) / (n * sum(x_i)) - (n + 1) / n
        gini = (2.0 * sum((i + 1) * x for i, x in enumerate(sorted_amounts))) / (n * total) - (n + 1) / n

        return max(0.0, min(1.0, gini))


# Example usage
def main():
    engineer = FeatureEngineer()

    # Mock data
    token_data = {
        'address': 'MOCKTOKEN123',
        'created_at': '2025-01-01T00:00:00Z',
        'supply': 1000000000,
    }

    pool_data = {
        'initial_liquidity_sol': 10.0,
        'initial_liquidity_usd': 2000.0,
        'token_reserve': 500000000,
        'sol_reserve': 10.0,
        'lp_provider_count': 1,
        'liquidity_locked': True,
    }

    transactions = []
    holders = [
        {'owner': 'holder1', 'amount': 100000000},
        {'owner': 'holder2', 'amount': 50000000},
        {'owner': 'holder3', 'amount': 25000000},
    ]

    phanes_data = {
        'scan_count': 234,
        'avg_scan_velocity': 45,
        'latest_rank': 12,
        'rug_warning': False,
        'avg_sentiment_score': 0.5,
    }

    features = engineer.build_feature_vector(
        token_address='MOCKTOKEN123',
        migration_time=datetime.now(),
        token_data=token_data,
        pool_data=pool_data,
        transactions=transactions,
        holders=holders,
        phanes_data=phanes_data
    )

    print("Feature vector:")
    for key, value in features.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
