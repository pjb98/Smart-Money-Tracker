"""
Cost-Optimized Pipeline Orchestrator
Integrates all cost-saving components into the main trading pipeline
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger
import os

from src.storage.datastore import DataStore
from src.storage.feature_cache import FeatureCache
from src.storage.pattern_matcher import PatternMatcher
from src.storage.compact_summary import CompactSummaryGenerator
from src.agents.claude_agent_cached import CachedClaudeAgent
from src.features.feature_engineer import FeatureEngineer


class CostOptimizedPipeline:
    """
    Orchestrates the cost-optimized trading analysis pipeline

    Flow:
    1. Check feature cache (avoid recomputing)
    2. If not cached, compute features and store
    3. Generate compact summary (50+ features -> ~15 metrics)
    4. Find similar historical patterns
    5. Check Claude decision cache
    6. If not cached, call Claude with compact summary
    7. Store decision and patterns for future use
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        db_path: str = "data/analytics.db",
        use_cache: bool = True,
        claude_model: str = "claude-3-haiku-20240307"
    ):
        """
        Initialize cost-optimized pipeline

        Args:
            anthropic_api_key: Anthropic API key (optional)
            db_path: Path to SQLite database
            use_cache: Whether to use caching
            claude_model: Claude model to use (haiku recommended for cost)
        """
        # Initialize storage layer
        self.datastore = DataStore(db_path)

        # Initialize pattern matching and summary generation
        self.pattern_matcher = PatternMatcher(self.datastore)
        self.summary_generator = CompactSummaryGenerator()

        # Initialize feature cache
        self.feature_engineer = FeatureEngineer()
        self.feature_cache = FeatureCache(
            self.datastore,
            self.pattern_matcher,
            self.summary_generator
        )

        # Initialize Claude agent (if API key provided)
        self.claude_agent = None
        if anthropic_api_key:
            self.claude_agent = CachedClaudeAgent(
                api_key=anthropic_api_key,
                datastore=self.datastore,
                summary_generator=self.summary_generator,
                model=claude_model,
                use_cache=use_cache
            )
            logger.info("Claude agent initialized")
        else:
            logger.warning("No Claude API key - agent disabled")

        self.use_cache = use_cache

        logger.info("Cost-optimized pipeline initialized")

    def analyze_token(
        self,
        token_address: str,
        migration_time: datetime,
        token_data: Dict[str, Any],
        pool_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        holders: List[Dict[str, Any]],
        phanes_data: Optional[Dict[str, Any]] = None,
        twitter_analysis: Optional[Dict[str, Any]] = None,
        wallet_intelligence: Optional[Dict[str, Any]] = None,
        model_prediction: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze a token using the cost-optimized pipeline

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            token_data: Token metadata
            pool_data: Pool information
            transactions: Transaction history
            holders: Holder list
            phanes_data: Phanes scan data
            twitter_analysis: Twitter account analysis
            wallet_intelligence: Wallet intelligence
            model_prediction: ML model prediction
            force_refresh: Force recomputation

        Returns:
            Complete analysis including Claude decision
        """
        logger.info(f"Analyzing token {token_address[:8]}... via cost-optimized pipeline")

        # Step 1: Get or compute features (with caching)
        def compute_features_fn():
            return self.feature_engineer.build_feature_vector(
                token_address=token_address,
                migration_time=migration_time,
                token_data=token_data,
                pool_data=pool_data,
                transactions=transactions,
                holders=holders,
                phanes_data=phanes_data,
                twitter_account_analysis=twitter_analysis
            )

        features = self.feature_cache.get_or_compute_features(
            token_address=token_address,
            migration_time=migration_time,
            compute_fn=compute_features_fn,
            force_recompute=force_refresh
        )

        # Step 2: Get or generate compact summary
        compact_summary = self.feature_cache.get_compact_summary(
            token_address=token_address,
            migration_time=migration_time
        )

        if not compact_summary or force_refresh:
            # Generate new compact summary with pattern matching
            similar_patterns = self.pattern_matcher.get_pattern_summary_for_claude(
                features,
                top_k=3
            )

            compact_summary = self.summary_generator.generate_compact_summary(
                features=features,
                model_prediction=model_prediction,
                similar_patterns=similar_patterns,
                wallet_intelligence=wallet_intelligence
            )

            # Store it
            self.datastore.store_features(
                token_address=token_address,
                migration_time=migration_time,
                features=features,
                compact_summary=compact_summary
            )

        # Step 3: Get Claude decision (with caching)
        claude_analysis = None
        if self.claude_agent:
            claude_analysis = self.claude_agent.analyze_token_compact(
                token_address=token_address,
                compact_summary=compact_summary,
                force_refresh=force_refresh
            )

        # Step 4: Build comprehensive result
        result = {
            'token_address': token_address,
            'migration_time': migration_time.isoformat(),
            'features': features,
            'compact_summary': compact_summary,
            'claude_analysis': claude_analysis,
            'model_prediction': model_prediction,
            'timestamp': datetime.now().isoformat()
        }

        # Log token savings estimate
        if compact_summary:
            estimated_tokens = self.summary_generator.estimate_token_count(compact_summary)
            logger.info(f"Analysis complete - estimated {estimated_tokens} tokens for Claude call")

        return result

    def update_outcome(
        self,
        token_address: str,
        migration_time: datetime,
        outcome_24h: float,
        outcome_7d: Optional[float] = None,
        max_gain: Optional[float] = None,
        max_loss: Optional[float] = None
    ):
        """
        Update pattern database with actual trading outcome

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            outcome_24h: 24h return percentage (-1.0 to +10.0 typically)
            outcome_7d: 7d return percentage
            max_gain: Maximum gain observed
            max_loss: Maximum loss observed
        """
        self.feature_cache.update_pattern_with_outcome(
            token_address=token_address,
            migration_time=migration_time,
            outcome_24h=outcome_24h,
            outcome_7d=outcome_7d,
            max_gain=max_gain,
            max_loss=max_loss
        )

        logger.info(f"Updated outcome for {token_address[:8]}...: {outcome_24h*100:+.1f}%")

    def store_backtest_result(
        self,
        strategy_name: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any]
    ):
        """
        Store backtest summary in database

        Args:
            strategy_name: Strategy name
            parameters: Strategy parameters
            results: Backtest results dict
        """
        self.datastore.store_backtest_result(
            strategy_name=strategy_name,
            parameters=parameters,
            total_trades=results.get('num_trades', 0),
            win_rate=results.get('win_rate', 0),
            total_return_pct=results.get('total_return_pct', 0),
            sharpe_ratio=results.get('sharpe_ratio', 0),
            max_drawdown_pct=results.get('max_drawdown_pct', 0),
            avg_win=results.get('avg_win', 0),
            avg_loss=results.get('avg_loss', 0),
            profit_factor=results.get('profit_factor', 0)
        )

    def get_best_strategies(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve best backtest results

        Args:
            top_k: Number of results to return

        Returns:
            List of top strategies
        """
        return self.datastore.get_best_backtest_results(top_k=top_k)

    def get_cost_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cost and usage statistics

        Returns:
            Stats dict
        """
        stats = {
            'cache_stats': self.feature_cache.get_cache_stats(),
            'claude_stats': self.claude_agent.get_cost_stats() if self.claude_agent else {}
        }

        return stats

    def close(self):
        """Cleanup resources"""
        self.datastore.close()
        logger.info("Pipeline closed")


# Example usage and integration guide
if __name__ == "__main__":
    """
    Example: How to use the cost-optimized pipeline
    """

    # Initialize pipeline
    pipeline = CostOptimizedPipeline(
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
        db_path="data/analytics.db",
        use_cache=True,
        claude_model="claude-3-haiku-20240307"
    )

    # Mock data (in production, get from ingestion layer)
    token_address = "SOL_TOKEN_EXAMPLE"
    migration_time = datetime.now()

    token_data = {
        'address': token_address,
        'created_at': '2025-01-10T10:00:00Z',
        'supply': 1_000_000_000
    }

    pool_data = {
        'initial_liquidity_sol': 15.5,
        'sol_reserve': 14.8,
        'token_reserve': 500_000_000,
        'liquidity_locked': True
    }

    transactions = []  # Would normally have transaction history

    holders = [
        {'owner': 'holder1', 'amount': 100_000_000},
        {'owner': 'holder2', 'amount': 50_000_000},
    ]

    phanes_data = {
        'scan_count': 345,
        'avg_scan_velocity': 42,
        'latest_rank': 8
    }

    # Analyze token
    result = pipeline.analyze_token(
        token_address=token_address,
        migration_time=migration_time,
        token_data=token_data,
        pool_data=pool_data,
        transactions=transactions,
        holders=holders,
        phanes_data=phanes_data
    )

    print("\n=== ANALYSIS RESULT ===")
    print(f"Token: {result['token_address'][:8]}...")
    print(f"Recommendation: {result.get('claude_analysis', {}).get('recommendation', 'N/A')}")
    print(f"Confidence: {result.get('claude_analysis', {}).get('confidence', 'N/A')}")

    # Later, update with actual outcome
    pipeline.update_outcome(
        token_address=token_address,
        migration_time=migration_time,
        outcome_24h=0.25,  # 25% gain
        max_gain=0.45,
        max_loss=-0.05
    )

    # Get cost stats
    print("\n=== COST STATS ===")
    stats = pipeline.get_cost_stats()
    print(f"Cache stats: {stats['cache_stats']}")
    print(f"Claude stats: {stats['claude_stats']}")

    pipeline.close()
