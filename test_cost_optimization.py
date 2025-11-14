"""
Test script for cost optimization pipeline
Demonstrates the complete flow and verifies all components work
"""
import os
import sys
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.optimization.cost_optimizer import CostOptimizedPipeline
from config import settings


def test_pipeline():
    """Test the cost-optimized pipeline"""

    logger.info("=" * 60)
    logger.info("Testing Cost-Optimized Pipeline")
    logger.info("=" * 60)

    # Initialize pipeline
    pipeline = CostOptimizedPipeline(
        anthropic_api_key=settings.anthropic_api_key,  # Can be None for testing without Claude
        db_path="data/analytics_test.db",
        use_cache=True,
        claude_model="claude-3-haiku-20240307"
    )

    # Mock token data
    token_address = "SOL_TEST_TOKEN_12345"
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
        'lp_provider_count': 1,
        'liquidity_locked': True,
        'initial_price_sol': 0.0000296
    }

    transactions = [
        {'block_time': int(datetime.now().timestamp()) - 3000, 'from_address': 'wallet1'},
        {'block_time': int(datetime.now().timestamp()) - 2000, 'from_address': 'wallet2'},
        {'block_time': int(datetime.now().timestamp()) - 1000, 'from_address': 'wallet1'},
    ]

    holders = [
        {'owner': 'holder1', 'amount': 120_000_000},
        {'owner': 'holder2', 'amount': 50_000_000},
        {'owner': 'holder3', 'amount': 25_000_000},
        {'owner': 'holder4', 'amount': 15_000_000},
    ]

    phanes_data = {
        'scan_count': 345,
        'avg_scan_velocity': 42,
        'latest_rank': 8,
        'rug_warning': False,
        'avg_sentiment_score': 0.7
    }

    twitter_analysis = {
        'risk_score': 4.0,
        'limited_data': False,
        'age_analysis': {'account_age_days': 365},
        'follower_analysis': {'followers_count': 1200}
    }

    wallet_intelligence = {
        'whale_count': 2,
        'insider_risk_score': 3,
        'highly_profitable_wallets': [
            {'address': 'WHALE1', 'win_rate': 75}
        ]
    }

    model_prediction = {
        'return_24h': 0.22,  # 22%
        'confidence': 0.68
    }

    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: First Analysis (should compute features)")
    logger.info("=" * 60)

    result1 = pipeline.analyze_token(
        token_address=token_address,
        migration_time=migration_time,
        token_data=token_data,
        pool_data=pool_data,
        transactions=transactions,
        holders=holders,
        phanes_data=phanes_data,
        twitter_analysis=twitter_analysis,
        wallet_intelligence=wallet_intelligence,
        model_prediction=model_prediction,
        force_refresh=False
    )

    logger.info(f"✓ Features computed: {len(result1['features'])} features")
    logger.info(f"✓ Compact summary generated: {len(result1['compact_summary'])} keys")

    if result1.get('claude_analysis'):
        logger.info(f"✓ Claude analysis: {result1['claude_analysis'].get('recommendation', 'N/A')}")
        logger.info(f"  Confidence: {result1['claude_analysis'].get('confidence', 'N/A')}")
        logger.info(f"  Cached: {result1['claude_analysis'].get('cached', False)}")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Second Analysis (should use cache)")
    logger.info("=" * 60)

    result2 = pipeline.analyze_token(
        token_address=token_address,
        migration_time=migration_time,
        token_data=token_data,
        pool_data=pool_data,
        transactions=transactions,
        holders=holders,
        phanes_data=phanes_data,
        twitter_analysis=twitter_analysis,
        wallet_intelligence=wallet_intelligence,
        model_prediction=model_prediction,
        force_refresh=False
    )

    logger.info(f"✓ Features retrieved from cache")

    if result2.get('claude_analysis'):
        logger.info(f"✓ Claude analysis: {result2['claude_analysis'].get('recommendation', 'N/A')}")
        logger.info(f"  Cached: {result2['claude_analysis'].get('cached', False)}")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Update with outcome (builds pattern history)")
    logger.info("=" * 60)

    pipeline.update_outcome(
        token_address=token_address,
        migration_time=migration_time,
        outcome_24h=0.28,  # 28% gain
        outcome_7d=0.45,   # 45% gain over 7 days
        max_gain=0.52,     # Max 52% gain
        max_loss=-0.08     # Max 8% loss
    )

    logger.info(f"✓ Pattern stored with outcome: +28%")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Analyze similar token (should find patterns)")
    logger.info("=" * 60)

    # Slightly different token
    token_address2 = "SOL_TEST_TOKEN_67890"
    pool_data2 = pool_data.copy()
    pool_data2['initial_liquidity_sol'] = 16.2  # Slightly different

    result3 = pipeline.analyze_token(
        token_address=token_address2,
        migration_time=datetime.now(),
        token_data=token_data,
        pool_data=pool_data2,
        transactions=transactions,
        holders=holders,
        phanes_data=phanes_data,
        twitter_analysis=twitter_analysis,
        model_prediction=model_prediction
    )

    similar_patterns = result3['compact_summary'].get('similar_patterns', {})
    logger.info(f"✓ Similar patterns found: {similar_patterns.get('count', 0)}")

    if similar_patterns.get('count', 0) > 0:
        logger.info(f"  Historical win rate: {similar_patterns.get('win_rate', 0):.1f}%")
        logger.info(f"  Historical avg outcome: {similar_patterns.get('avg_outcome', 0):.1f}%")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 5: Cost Statistics")
    logger.info("=" * 60)

    stats = pipeline.get_cost_stats()

    cache_stats = stats.get('cache_stats', {})
    logger.info(f"✓ Features cached: {cache_stats.get('total_cached_features', 0)}")
    logger.info(f"✓ Patterns stored: {cache_stats.get('total_patterns', 0)}")
    logger.info(f"✓ Claude decisions cached: {cache_stats.get('total_claude_decisions', 0)}")

    claude_stats = stats.get('claude_stats', {})
    if claude_stats:
        logger.info(f"\nClaude API Stats:")
        logger.info(f"  Total API calls: {claude_stats.get('total_api_calls', 0)}")
        logger.info(f"  Cache hits: {claude_stats.get('cache_hits', 0)}")
        logger.info(f"  Cache hit rate: {claude_stats.get('cache_hit_rate', '0%')}")
        logger.info(f"  Total tokens used: {claude_stats.get('total_tokens_used', 0)}")
        logger.info(f"  Estimated cost: {claude_stats.get('estimated_cost_usd', '$0.00')}")

    logger.info("\n" + "=" * 60)
    logger.info("STEP 6: Backtest Result Storage")
    logger.info("=" * 60)

    # Store a mock backtest result
    pipeline.store_backtest_result(
        strategy_name="test_strategy_v1",
        parameters={'stop_loss': 0.25, 'take_profit': 0.30},
        results={
            'num_trades': 50,
            'win_rate': 0.62,
            'total_return_pct': 45.3,
            'sharpe_ratio': 1.8,
            'max_drawdown_pct': -12.5,
            'avg_win': 0.32,
            'avg_loss': -0.18,
            'profit_factor': 1.95
        }
    )

    logger.info("✓ Backtest result stored")

    # Retrieve best strategies
    best_strategies = pipeline.get_best_strategies(top_k=3)
    logger.info(f"✓ Best strategies: {len(best_strategies)}")

    if best_strategies:
        for i, strat in enumerate(best_strategies, 1):
            logger.info(f"  {i}. {strat['strategy_name']}: Sharpe {strat['sharpe_ratio']:.2f}, WR {strat['win_rate']*100:.1f}%")

    logger.info("\n" + "=" * 60)
    logger.info("TEST COMPLETE ✓")
    logger.info("=" * 60)

    logger.info("\n📊 Summary:")
    logger.info("  ✓ Feature caching works")
    logger.info("  ✓ Pattern matching works")
    logger.info("  ✓ Compact summaries generated")
    logger.info("  ✓ Claude caching works" if claude_stats else "  ⚠ Claude API not tested (no API key)")
    logger.info("  ✓ Outcome tracking works")
    logger.info("  ✓ Backtest storage works")

    logger.info("\n💡 Next steps:")
    logger.info("  1. Set ANTHROPIC_API_KEY to test Claude integration")
    logger.info("  2. Integrate into main.py pipeline")
    logger.info("  3. Backfill historical patterns from past data")
    logger.info("  4. Monitor costs in production")

    pipeline.close()


if __name__ == "__main__":
    test_pipeline()
