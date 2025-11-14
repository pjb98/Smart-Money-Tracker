"""
Pattern Matching for Similar Historical Situations
Converts features to compact vectors and finds similar past patterns
"""
import numpy as np
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime

from .datastore import DataStore


class PatternMatcher:
    """
    Pattern matching system for finding similar historical trading situations
    """

    # Define which features to use for pattern matching
    # These are the most predictive features (reduce from 50+ to ~10-15)
    PATTERN_FEATURES = [
        # Liquidity (most important)
        'initial_liquidity_sol',
        'sol_reserve',

        # Holder distribution
        'holder_count',
        'top1_holder_pct',
        'top5_holder_pct',
        'gini_coefficient',

        # Transaction activity
        'tx_count_1h',
        'unique_wallets_1h',

        # Social signals
        'phanes_scan_velocity',
        'twitter_risk_score',

        # Pre-migration metrics
        'time_on_bonding_curve_hours',
        'buy_sell_ratio',
        'unique_wallets_pre_migration',

        # Derived
        'concentration_risk',
        'liquidity_per_holder'
    ]

    def __init__(self, datastore: DataStore):
        """
        Initialize pattern matcher

        Args:
            datastore: DataStore instance
        """
        self.datastore = datastore
        logger.info("Initialized PatternMatcher")

    def extract_pattern_vector(
        self,
        features: Dict[str, Any],
        normalize: bool = True
    ) -> List[float]:
        """
        Extract compact pattern vector from full features

        Args:
            features: Full feature dictionary
            normalize: Whether to normalize values (recommended)

        Returns:
            Compact pattern vector (10-15 values)
        """
        vector = []

        for feature_name in self.PATTERN_FEATURES:
            value = features.get(feature_name, 0)

            # Handle None values
            if value is None:
                value = 0

            # Convert to float
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0.0

            vector.append(value)

        # Normalize if requested
        if normalize:
            vector = self._normalize_vector(vector)

        return vector

    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """
        Normalize vector values to 0-1 range using simple min-max scaling

        Args:
            vector: Raw vector values

        Returns:
            Normalized vector
        """
        # Use sensible ranges for each feature type
        # These are approximate maximums based on pumpfun token characteristics
        max_values = [
            50.0,    # initial_liquidity_sol (rarely >50 SOL)
            50.0,    # sol_reserve
            1000,    # holder_count
            1.0,     # top1_holder_pct (already 0-1)
            1.0,     # top5_holder_pct (already 0-1)
            1.0,     # gini_coefficient (already 0-1)
            500,     # tx_count_1h
            500,     # unique_wallets_1h
            100,     # phanes_scan_velocity
            10.0,    # twitter_risk_score (already 0-10)
            72.0,    # time_on_bonding_curve_hours (3 days max typical)
            10.0,    # buy_sell_ratio
            1000,    # unique_wallets_pre_migration
            5.0,     # concentration_risk (derived)
            1.0      # liquidity_per_holder
        ]

        normalized = []
        for value, max_val in zip(vector, max_values):
            # Clip and normalize
            clipped = min(value, max_val)
            norm_val = clipped / max_val if max_val > 0 else 0
            normalized.append(norm_val)

        return normalized

    def find_similar_patterns(
        self,
        features: Dict[str, Any],
        top_k: int = 5,
        category: Optional[str] = None,
        min_outcome: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar historical patterns

        Args:
            features: Current token features
            top_k: Number of similar patterns to return
            category: Optional category filter
            min_outcome: Optional minimum outcome filter (e.g., 0.1 for 10%+ winners)

        Returns:
            List of similar patterns with outcomes
        """
        # Extract pattern vector
        pattern_vector = self.extract_pattern_vector(features, normalize=True)

        # Query datastore for similar patterns
        similar = self.datastore.get_similar_patterns(
            pattern_vector,
            top_k=top_k * 2,  # Get more candidates for filtering
            category=category
        )

        # Filter by outcome if requested
        if min_outcome is not None:
            similar = [
                p for p in similar
                if p.get('outcome_24h') is not None and p['outcome_24h'] >= min_outcome
            ]

        # Return top-k
        return similar[:top_k]

    def store_pattern_with_outcome(
        self,
        token_address: str,
        migration_time: datetime,
        features: Dict[str, Any],
        outcome_24h: Optional[float] = None,
        outcome_7d: Optional[float] = None,
        max_gain: Optional[float] = None,
        max_loss: Optional[float] = None,
        category: Optional[str] = None
    ):
        """
        Store a new pattern with its outcome for future matching

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            features: Full feature dictionary
            outcome_24h: 24h return percentage
            outcome_7d: 7d return percentage
            max_gain: Maximum gain observed
            max_loss: Maximum loss observed
            category: Pattern category
        """
        # Extract pattern vector
        pattern_vector = self.extract_pattern_vector(features, normalize=True)

        # Store in datastore
        self.datastore.store_pattern(
            token_address=token_address,
            migration_time=migration_time,
            pattern_vector=pattern_vector,
            outcome_24h=outcome_24h,
            outcome_7d=outcome_7d,
            max_gain=max_gain,
            max_loss=max_loss,
            category=category
        )

        logger.debug(f"Stored pattern for {token_address} with outcome {outcome_24h}%")

    def categorize_pattern(self, features: Dict[str, Any]) -> str:
        """
        Automatically categorize a pattern based on features

        Args:
            features: Feature dictionary

        Returns:
            Category string
        """
        liquidity = features.get('initial_liquidity_sol', 0)
        holders = features.get('holder_count', 0)
        concentration = features.get('top1_holder_pct', 0)
        social_score = features.get('phanes_scan_velocity', 0)
        twitter_risk = features.get('twitter_risk_score', 5.0)

        # Categorization logic
        if liquidity >= 20:
            return "high_liquidity"
        elif social_score >= 50:
            return "viral_meme"
        elif concentration >= 0.2:
            return "whale_concentrated"
        elif holders >= 200 and twitter_risk <= 3:
            return "community_token"
        elif twitter_risk >= 7:
            return "high_risk"
        else:
            return "standard"

    def analyze_similar_patterns(
        self,
        similar_patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a set of similar patterns to generate insights

        Args:
            similar_patterns: List of similar patterns from find_similar_patterns

        Returns:
            Analysis summary
        """
        if not similar_patterns:
            return {
                'count': 0,
                'avg_outcome': 0,
                'win_rate': 0,
                'best_outcome': 0,
                'worst_outcome': 0,
                'confidence': 'NONE'
            }

        outcomes = [
            p['outcome_24h']
            for p in similar_patterns
            if p.get('outcome_24h') is not None
        ]

        if not outcomes:
            return {
                'count': len(similar_patterns),
                'avg_outcome': 0,
                'win_rate': 0,
                'best_outcome': 0,
                'worst_outcome': 0,
                'confidence': 'LOW'
            }

        winners = [o for o in outcomes if o > 0]
        win_rate = len(winners) / len(outcomes)
        avg_outcome = sum(outcomes) / len(outcomes)

        # Determine confidence based on consistency
        if len(outcomes) >= 5:
            if win_rate >= 0.7:
                confidence = 'HIGH'
            elif win_rate >= 0.5:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'
        else:
            confidence = 'LOW'  # Not enough data

        return {
            'count': len(similar_patterns),
            'avg_outcome': avg_outcome,
            'win_rate': win_rate,
            'best_outcome': max(outcomes),
            'worst_outcome': min(outcomes),
            'confidence': confidence,
            'sample_tokens': [
                p['token_address'][:8] + '...'
                for p in similar_patterns[:3]
            ]
        }

    def get_pattern_summary_for_claude(
        self,
        features: Dict[str, Any],
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Generate compact pattern summary for Claude

        Args:
            features: Current token features
            top_k: Number of similar patterns to include

        Returns:
            Compact summary dict for Claude
        """
        # Find similar patterns
        similar = self.find_similar_patterns(features, top_k=top_k)

        # Analyze them
        analysis = self.analyze_similar_patterns(similar)

        # Build compact summary
        summary = {
            'similar_pattern_count': analysis['count'],
            'historical_avg_outcome': round(analysis['avg_outcome'] * 100, 1),  # Convert to %
            'historical_win_rate': round(analysis['win_rate'] * 100, 1),  # Convert to %
            'confidence': analysis['confidence'],
            'examples': []
        }

        # Add top examples with outcomes
        for pattern in similar[:top_k]:
            if pattern.get('outcome_24h') is not None:
                summary['examples'].append({
                    'token': pattern['token_address'][:8] + '...',
                    'outcome_24h': round(pattern['outcome_24h'] * 100, 1),  # %
                    'category': pattern.get('category', 'unknown'),
                    'distance': round(pattern.get('distance', 0), 3)
                })

        return summary


# Example usage
if __name__ == "__main__":
    from .datastore import DataStore

    # Initialize
    store = DataStore("data/analytics.db")
    matcher = PatternMatcher(store)

    # Mock features
    features = {
        'initial_liquidity_sol': 15.0,
        'sol_reserve': 14.5,
        'holder_count': 234,
        'top1_holder_pct': 0.12,
        'top5_holder_pct': 0.35,
        'gini_coefficient': 0.45,
        'tx_count_1h': 87,
        'unique_wallets_1h': 65,
        'phanes_scan_velocity': 42,
        'twitter_risk_score': 4.0,
        'time_on_bonding_curve_hours': 12.5,
        'buy_sell_ratio': 1.8,
        'unique_wallets_pre_migration': 156,
        'concentration_risk': 0.25,
        'liquidity_per_holder': 0.064
    }

    # Extract pattern vector
    vector = matcher.extract_pattern_vector(features, normalize=True)
    print("Pattern vector:", vector)

    # Categorize
    category = matcher.categorize_pattern(features)
    print("Category:", category)

    # Store pattern with outcome
    matcher.store_pattern_with_outcome(
        token_address="SOL_TOKEN_123",
        migration_time=datetime.now(),
        features=features,
        outcome_24h=0.25,  # 25% gain
        outcome_7d=0.45,
        max_gain=0.67,
        max_loss=-0.10,
        category=category
    )

    # Find similar patterns
    similar = matcher.find_similar_patterns(features, top_k=3)
    print("\nSimilar patterns:", similar)

    # Get summary for Claude
    summary = matcher.get_pattern_summary_for_claude(features, top_k=3)
    print("\nSummary for Claude:", summary)

    store.close()
