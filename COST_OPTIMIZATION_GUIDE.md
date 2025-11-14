# Cost Optimization Architecture Guide

## Overview

This guide explains the cost-optimized architecture for the PumpFun trading agent. The system minimizes Claude API costs while maintaining high-quality decision-making.

## Problem Statement

**Before optimization:**
- Sending 50+ raw features to Claude every time
- No caching of responses
- Recomputing features repeatedly
- High token usage (~2000+ tokens per call)
- No pattern matching or historical context

**After optimization:**
- Compact summaries (~15 key metrics)
- Response caching (avoid redundant calls)
- Precomputed features (compute once, use many times)
- Pattern matching (learn from history)
- Token usage reduced to ~500-800 tokens per call
- Cache hit rate: 30-50% expected

## Architecture Components

### 1. DataStore (`src/storage/datastore.py`)

SQLite-based storage for:
- Precomputed features
- Historical patterns with outcomes
- Claude decisions (for caching)
- Backtest results
- Trade outcomes

**Key Methods:**
```python
# Store features
datastore.store_features(token_address, migration_time, features, compact_summary)

# Get cached features
features = datastore.get_features(token_address, migration_time)

# Store pattern with outcome
datastore.store_pattern(token_address, migration_time, pattern_vector, outcome_24h=0.25)

# Cache Claude decision
datastore.cache_claude_decision(token_address, migration_time, input_hash, recommendation, ...)

# Get cached decision
decision = datastore.get_cached_decision(input_hash)
```

### 2. PatternMatcher (`src/storage/pattern_matcher.py`)

Pattern matching system that:
- Extracts compact feature vectors (15 values from 50+ features)
- Normalizes features for comparison
- Finds similar historical situations
- Categorizes patterns automatically

**Key Methods:**
```python
# Extract pattern vector
vector = pattern_matcher.extract_pattern_vector(features, normalize=True)

# Find similar patterns
similar = pattern_matcher.find_similar_patterns(features, top_k=5)

# Store pattern with outcome
pattern_matcher.store_pattern_with_outcome(
    token_address, migration_time, features,
    outcome_24h=0.25, category="high_liquidity"
)

# Get summary for Claude
summary = pattern_matcher.get_pattern_summary_for_claude(features, top_k=3)
```

### 3. CompactSummaryGenerator (`src/storage/compact_summary.py`)

Reduces 50+ features to ~15 key metrics:

**Compact Summary Format:**
```json
{
  "liquidity_sol": 15.5,
  "pool_locked": true,
  "holders": 234,
  "top1_holder_pct": 12.0,
  "tx_1h": 87,
  "phanes_velocity": 42,
  "twitter_risk": 4.0,
  "ml_prediction": {
    "return_24h": 25.0,
    "confidence": 0.68
  },
  "similar_patterns": {
    "count": 5,
    "avg_outcome": 18.5,
    "win_rate": 60.0,
    "top_examples": [...]
  }
}
```

**Key Methods:**
```python
# Generate compact summary
summary = summary_generator.generate_compact_summary(
    features, model_prediction, similar_patterns, wallet_intelligence
)

# Format for Claude prompt
prompt_text = summary_generator.format_for_claude_prompt(summary)

# Generate hash for caching
hash = summary_generator.generate_input_hash(summary, include_timestamp=False)

# Estimate token count
tokens = summary_generator.estimate_token_count(summary)
```

### 4. FeatureCache (`src/storage/feature_cache.py`)

Manages feature computation and caching:

**Key Methods:**
```python
# Get or compute features
features = feature_cache.get_or_compute_features(
    token_address, migration_time,
    compute_fn=lambda: engineer.build_feature_vector(...)
)

# Store features with summary
feature_cache.store_features_with_summary(
    token_address, migration_time, features, model_prediction
)

# Update pattern with outcome
feature_cache.update_pattern_with_outcome(
    token_address, migration_time, outcome_24h=0.25
)

# Get cache stats
stats = feature_cache.get_cache_stats()
```

### 5. CachedClaudeAgent (`src/agents/claude_agent_cached.py`)

Wrapper around ClaudeAgent with caching:

**Key Methods:**
```python
# Analyze with caching
analysis = cached_agent.analyze_token_compact(
    token_address, compact_summary, force_refresh=False
)

# Get cost stats
stats = cached_agent.get_cost_stats()
# Returns: {
#   'total_api_calls': 50,
#   'cache_hits': 25,
#   'cache_hit_rate': '33.3%',
#   'total_tokens_used': 25000,
#   'estimated_cost_usd': '$0.0125'
# }
```

### 6. CostOptimizedPipeline (`src/optimization/cost_optimizer.py`)

Orchestrator that ties everything together:

**Complete Pipeline Flow:**
```python
# Initialize pipeline
pipeline = CostOptimizedPipeline(
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
    db_path="data/analytics.db",
    use_cache=True
)

# Analyze token (uses caching at every step)
result = pipeline.analyze_token(
    token_address=token_address,
    migration_time=migration_time,
    token_data=token_data,
    pool_data=pool_data,
    transactions=transactions,
    holders=holders,
    phanes_data=phanes_data,
    twitter_analysis=twitter_analysis,
    wallet_intelligence=wallet_intelligence,
    model_prediction=model_prediction
)

# Later, update with outcome (builds historical patterns)
pipeline.update_outcome(
    token_address, migration_time,
    outcome_24h=0.25,  # 25% gain
    max_gain=0.45
)

# Get cost stats
stats = pipeline.get_cost_stats()
```

## Integration with Existing Code

### In `main.py`:

```python
from src.optimization.cost_optimizer import CostOptimizedPipeline

class PumpfunAgent:
    def __init__(self, use_mock_data: bool = True):
        # ... existing initialization ...

        # Add cost-optimized pipeline
        self.cost_pipeline = CostOptimizedPipeline(
            anthropic_api_key=settings.anthropic_api_key,
            db_path="data/analytics.db",
            use_cache=True,
            claude_model="claude-3-haiku-20240307"
        )

    async def process_migration(self, token_address: str, migration_time: datetime):
        """Process new migration with cost optimization"""

        # ... existing data gathering ...

        # Use cost-optimized pipeline instead of direct Claude call
        result = self.cost_pipeline.analyze_token(
            token_address=token_address,
            migration_time=migration_time,
            token_data=token_data,
            pool_data=pool_data,
            transactions=transactions,
            holders=holders,
            phanes_data=phanes_data,
            twitter_analysis=twitter_analysis,
            wallet_intelligence=wallet_intelligence,
            model_prediction=model_prediction
        )

        # Get Claude's decision
        claude_analysis = result['claude_analysis']
        recommendation = claude_analysis.get('recommendation', 'HOLD')

        # ... execute trade decision ...

        return result
```

### In paper trader / backtester:

```python
# After trade completes, update patterns
pipeline.update_outcome(
    token_address=token_address,
    migration_time=migration_time,
    outcome_24h=actual_return_24h,
    outcome_7d=actual_return_7d,
    max_gain=max_gain_observed,
    max_loss=max_loss_observed
)
```

## Cost Savings Estimates

### Before Optimization:
- **Tokens per analysis:** ~2000-2500
- **Cost per analysis:** ~$0.001 (Haiku)
- **Monthly (1000 tokens):** ~$1.00
- **Cache hit rate:** 0%

### After Optimization:
- **Tokens per analysis:** ~500-800 (compact summary)
- **Cost per analysis:** ~$0.0003
- **Cache hit rate:** 30-50% (estimate)
- **Effective cost per analysis:** ~$0.00015-$0.0002
- **Monthly savings:** ~70-80%

### Additional Benefits:
- **Faster responses** (cache hits are instant)
- **Pattern learning** (builds historical knowledge)
- **Backtest insights** (query past performance)
- **Cost tracking** (detailed analytics)

## Database Schema

### Tables Created:

1. **features** - Precomputed features + compact summaries
2. **patterns** - Historical patterns with outcomes
3. **claude_decisions** - Cached Claude responses
4. **backtest_results** - Strategy backtest summaries
5. **trade_outcomes** - Actual trade results

### Database Location:
`data/analytics.db` (SQLite)

### Inspect Database:
```bash
sqlite3 data/analytics.db

.tables
SELECT COUNT(*) FROM features;
SELECT COUNT(*) FROM patterns;
SELECT * FROM claude_decisions ORDER BY created_at DESC LIMIT 5;
```

## Best Practices

### 1. Feature Computation
- **Always use the cache:** `get_or_compute_features()`
- **Batch compute** for historical data
- **Update patterns** with actual outcomes

### 2. Claude API Calls
- **Use compact summaries** (not full features)
- **Enable caching** (use_cache=True)
- **Use Haiku model** for routine decisions
- **Reserve Opus** for complex edge cases

### 3. Pattern Matching
- **Build history first:** Backfill patterns from historical data
- **Update continuously:** Store outcomes after every trade
- **Filter by category:** Use pattern categories for better matching

### 4. Monitoring Costs
```python
# Check costs regularly
stats = pipeline.get_cost_stats()
print(f"Cache hit rate: {stats['claude_stats']['cache_hit_rate']}")
print(f"Estimated cost: {stats['claude_stats']['estimated_cost_usd']}")
```

## Troubleshooting

### Cache not working?
- Check that `use_cache=True`
- Verify database is writable
- Check input hash generation

### High token usage?
- Verify compact summaries are being used
- Check that pattern context isn't too large
- Review Claude prompt length

### Poor pattern matching?
- Need more historical data (>100 patterns minimum)
- Check normalization of pattern vectors
- Verify outcome data is being stored

## Migration from Old System

### Step 1: Initialize new components
```python
from src.optimization.cost_optimizer import CostOptimizedPipeline

pipeline = CostOptimizedPipeline(
    anthropic_api_key=settings.anthropic_api_key,
    use_cache=True
)
```

### Step 2: Backfill historical data (optional)
```python
# For each past token:
pipeline.feature_cache.store_features_with_summary(...)
pipeline.update_outcome(...)
```

### Step 3: Replace Claude calls
```python
# OLD:
# analysis = claude_agent.analyze_token(token_address, features, ...)

# NEW:
result = pipeline.analyze_token(
    token_address, migration_time, token_data, pool_data, ...
)
analysis = result['claude_analysis']
```

### Step 4: Monitor costs
```python
# Check stats after 100 tokens
stats = pipeline.get_cost_stats()
print(stats)
```

## Next Steps

1. **Test with mock data** - Verify all components work
2. **Backfill patterns** - Add historical outcomes
3. **Integrate into main.py** - Replace old Claude calls
4. **Monitor costs** - Track savings over time
5. **Tune thresholds** - Optimize based on results

## Questions?

Check the example usage in each module's `__main__` block for detailed examples.
