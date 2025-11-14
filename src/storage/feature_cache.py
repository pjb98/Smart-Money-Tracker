"""
Feature Cache for precomputing and storing features
Avoids recomputing the same features multiple times
"""
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .datastore import DataStore
from .compact_summary import CompactSummaryGenerator
from .pattern_matcher import PatternMatcher


class FeatureCache:
    """
    Manages feature computation, storage, and retrieval
    """

    def __init__(
        self,
        datastore: DataStore,
        pattern_matcher: PatternMatcher,
        summary_generator: CompactSummaryGenerator
    ):
        """
        Initialize feature cache

        Args:
            datastore: DataStore instance
            pattern_matcher: PatternMatcher instance
            summary_generator: CompactSummaryGenerator instance
        """
        self.datastore = datastore
        self.pattern_matcher = pattern_matcher
        self.summary_generator = summary_generator

        logger.info("Initialized FeatureCache")

    def get_or_compute_features(
        self,
        token_address: str,
        migration_time: datetime,
        compute_fn: callable,
        force_recompute: bool = False
    ) -> Dict[str, Any]:
        """
        Get features from cache or compute if not cached

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            compute_fn: Function that computes features (called if not cached)
            force_recompute: Force recomputation even if cached

        Returns:
            Feature dictionary
        """
        # Check cache first (unless force recompute)
        if not force_recompute:
            cached_features = self.datastore.get_features(token_address, migration_time)

            if cached_features:
                logger.debug(f"Cache HIT for {token_address}")
                return cached_features

        # Cache miss - compute features
        logger.debug(f"Cache MISS for {token_address} - computing...")

        features = compute_fn()

        # Store in cache
        self.store_features_with_summary(
            token_address,
            migration_time,
            features
        )

        return features

    def store_features_with_summary(
        self,
        token_address: str,
        migration_time: datetime,
        features: Dict[str, Any],
        model_prediction: Optional[Dict[str, Any]] = None,
        wallet_intelligence: Optional[Dict[str, Any]] = None
    ):
        """
        Store features and generate compact summary

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            features: Full feature dictionary
            model_prediction: Optional ML prediction
            wallet_intelligence: Optional wallet intelligence
        """
        # Find similar patterns
        similar_patterns = self.pattern_matcher.get_pattern_summary_for_claude(
            features,
            top_k=3
        )

        # Generate compact summary
        compact_summary = self.summary_generator.generate_compact_summary(
            features,
            model_prediction=model_prediction,
            similar_patterns=similar_patterns,
            wallet_intelligence=wallet_intelligence
        )

        # Store both full features and compact summary
        self.datastore.store_features(
            token_address=token_address,
            migration_time=migration_time,
            features=features,
            compact_summary=compact_summary
        )

        logger.info(f"Stored features + compact summary for {token_address}")

    def get_compact_summary(
        self,
        token_address: str,
        migration_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve precomputed compact summary

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp

        Returns:
            Compact summary or None
        """
        return self.datastore.get_compact_summary(token_address, migration_time)

    def update_pattern_with_outcome(
        self,
        token_address: str,
        migration_time: datetime,
        outcome_24h: float,
        outcome_7d: Optional[float] = None,
        max_gain: Optional[float] = None,
        max_loss: Optional[float] = None
    ):
        """
        Update a pattern with its actual outcome after trading

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            outcome_24h: 24h return percentage
            outcome_7d: Optional 7d return
            max_gain: Maximum gain observed
            max_loss: Maximum loss observed
        """
        # Get original features
        features = self.datastore.get_features(token_address, migration_time)

        if not features:
            logger.warning(f"Cannot update pattern - features not found for {token_address}")
            return

        # Categorize pattern
        category = self.pattern_matcher.categorize_pattern(features)

        # Store pattern with outcome
        self.pattern_matcher.store_pattern_with_outcome(
            token_address=token_address,
            migration_time=migration_time,
            features=features,
            outcome_24h=outcome_24h,
            outcome_7d=outcome_7d,
            max_gain=max_gain,
            max_loss=max_loss,
            category=category
        )

        logger.info(f"Updated pattern for {token_address} with outcome {outcome_24h*100:.1f}%")

    def bulk_compute_and_cache(
        self,
        tokens: list,
        compute_fn: callable,
        batch_size: int = 10
    ):
        """
        Bulk compute and cache features for multiple tokens

        Args:
            tokens: List of (token_address, migration_time) tuples
            compute_fn: Function that computes features for one token
            batch_size: Batch size for progress logging
        """
        total = len(tokens)
        cached = 0
        computed = 0

        logger.info(f"Bulk caching {total} tokens...")

        for i, (token_address, migration_time) in enumerate(tokens, 1):
            # Check cache
            existing = self.datastore.get_features(token_address, migration_time)

            if existing:
                cached += 1
                continue

            # Compute
            try:
                features = compute_fn(token_address, migration_time)
                self.store_features_with_summary(token_address, migration_time, features)
                computed += 1

            except Exception as e:
                logger.error(f"Error computing features for {token_address}: {e}")

            # Progress logging
            if i % batch_size == 0:
                logger.info(f"Progress: {i}/{total} ({cached} cached, {computed} computed)")

        logger.info(f"Bulk caching complete: {cached} cached, {computed} newly computed")

    def clear_cache(self, before_date: Optional[datetime] = None):
        """
        Clear cache (use with caution!)

        Args:
            before_date: Optional - only clear entries before this date
        """
        logger.warning("Clearing feature cache...")

        # This would require adding a delete method to DataStore
        # For now, just log a warning
        logger.warning("Clear cache not implemented - manually delete data/analytics.db if needed")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Stats dict
        """
        db_stats = self.datastore.get_stats()

        return {
            'total_cached_features': db_stats.get('features', 0),
            'total_patterns': db_stats.get('patterns', 0),
            'total_claude_decisions': db_stats.get('claude_decisions', 0),
            'total_trade_outcomes': db_stats.get('trade_outcomes', 0)
        }


# Example usage
if __name__ == "__main__":
    from .datastore import DataStore
    from .pattern_matcher import PatternMatcher
    from .compact_summary import CompactSummaryGenerator

    # Initialize components
    datastore = DataStore("data/analytics.db")
    pattern_matcher = PatternMatcher(datastore)
    summary_generator = CompactSummaryGenerator()

    cache = FeatureCache(datastore, pattern_matcher, summary_generator)

    # Mock compute function
    def compute_features(token_address=None, migration_time=None):
        return {
            'token_address': token_address or 'SOL_TOKEN_123',
            'initial_liquidity_sol': 15.0,
            'holder_count': 234,
            'tx_count_1h': 87,
            # ... etc
        }

    # Test get_or_compute
    features = cache.get_or_compute_features(
        token_address="SOL_TOKEN_TEST",
        migration_time=datetime.now(),
        compute_fn=compute_features
    )

    print("Features:", features)

    # Get cache stats
    stats = cache.get_cache_stats()
    print("\nCache stats:", stats)

    datastore.close()
