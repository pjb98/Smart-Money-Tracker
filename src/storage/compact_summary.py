"""
Compact Summary Generator for Claude
Reduces 50+ features to ~10-15 key metrics + similar pattern context
"""
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime
import hashlib
import json


class CompactSummaryGenerator:
    """
    Generates compact, structured summaries for Claude to minimize token usage
    """

    # Define the most important features to send to Claude
    # Reduced from 50+ to ~12 core metrics
    CORE_FEATURES = {
        'liquidity': [
            'initial_liquidity_sol',
            'pool_locked',
            'sol_reserve'
        ],
        'distribution': [
            'holder_count',
            'top1_holder_pct',
            'top5_holder_pct',
            'concentration_risk'
        ],
        'activity': [
            'tx_count_1h',
            'unique_wallets_1h'
        ],
        'social': [
            'phanes_scan_velocity',
            'twitter_risk_score'
        ],
        'pre_migration': [
            'time_on_bonding_curve_hours',
            'buy_sell_ratio',
            'total_volume_pre_migration_sol'
        ]
    }

    def __init__(self):
        """Initialize compact summary generator"""
        logger.info("Initialized CompactSummaryGenerator")

    def generate_compact_summary(
        self,
        features: Dict[str, Any],
        model_prediction: Optional[Dict[str, Any]] = None,
        similar_patterns: Optional[Dict[str, Any]] = None,
        wallet_intelligence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate compact summary from full features

        Args:
            features: Full feature dictionary (50+ features)
            model_prediction: ML model prediction
            similar_patterns: Similar historical patterns (from PatternMatcher)
            wallet_intelligence: Wallet intelligence summary

        Returns:
            Compact summary dict (~10-15 key metrics)
        """
        # Extract core metrics
        summary = {
            'token': features.get('token_address', 'unknown')[:8] + '...',
            'migration_time': features.get('migration_time', 'unknown'),

            # Liquidity (3 metrics)
            'liquidity_sol': round(features.get('initial_liquidity_sol', 0), 2),
            'pool_locked': features.get('pool_locked', 0) == 1,
            'sol_reserve': round(features.get('sol_reserve', 0), 2),

            # Distribution (4 metrics)
            'holders': features.get('holder_count', 0),
            'top1_holder_pct': round(features.get('top1_holder_pct', 0) * 100, 1),
            'top5_holder_pct': round(features.get('top5_holder_pct', 0) * 100, 1),
            'concentration_risk': round(features.get('concentration_risk', 0), 2),

            # Activity (2 metrics)
            'tx_1h': features.get('tx_count_1h', 0),
            'wallets_1h': features.get('unique_wallets_1h', 0),

            # Social (2 metrics)
            'phanes_velocity': features.get('phanes_scan_velocity', 0),
            'twitter_risk': round(features.get('twitter_risk_score', 5.0), 1),

            # Pre-migration (3 metrics)
            'hours_on_curve': round(features.get('time_on_bonding_curve_hours', 0), 1),
            'buy_sell_ratio': round(features.get('buy_sell_ratio', 0), 2),
            'pre_volume_sol': round(features.get('total_volume_pre_migration_sol', 0), 1)
        }

        # Add model prediction if available
        if model_prediction:
            summary['ml_prediction'] = {
                'return_24h': round(model_prediction.get('return_24h', 0) * 100, 1),  # %
                'confidence': model_prediction.get('confidence', 0.5)
            }

        # Add similar patterns summary
        if similar_patterns:
            summary['similar_patterns'] = {
                'count': similar_patterns.get('similar_pattern_count', 0),
                'avg_outcome': similar_patterns.get('historical_avg_outcome', 0),  # Already %
                'win_rate': similar_patterns.get('historical_win_rate', 0),  # Already %
                'confidence': similar_patterns.get('confidence', 'NONE'),
                'top_examples': similar_patterns.get('examples', [])[:3]
            }

        # Add wallet intelligence summary
        if wallet_intelligence:
            summary['wallets'] = {
                'whale_count': wallet_intelligence.get('whale_count', 0),
                'insider_risk': wallet_intelligence.get('insider_risk_score', 0),
                'profitable_wallets': len(wallet_intelligence.get('highly_profitable_wallets', []))
            }

        logger.debug(f"Generated compact summary with {len(summary)} top-level keys")
        return summary

    def generate_input_hash(
        self,
        summary: Dict[str, Any],
        include_timestamp: bool = False
    ) -> str:
        """
        Generate hash of input for caching Claude responses

        Args:
            summary: Compact summary dict
            include_timestamp: Whether to include timestamp (set False for caching)

        Returns:
            Hash string
        """
        # Create a copy and remove timestamp if not including it
        hashable = summary.copy()

        if not include_timestamp:
            hashable.pop('migration_time', None)
            hashable.pop('token', None)  # Also remove token address

        # Convert to JSON and hash
        json_str = json.dumps(hashable, sort_keys=True)
        hash_obj = hashlib.md5(json_str.encode())
        return hash_obj.hexdigest()

    def format_for_claude_prompt(
        self,
        summary: Dict[str, Any],
        include_reasoning_context: bool = True
    ) -> str:
        """
        Format compact summary as text for Claude prompt

        Args:
            summary: Compact summary dict
            include_reasoning_context: Include similar patterns for reasoning

        Returns:
            Formatted text string
        """
        prompt = f"""TOKEN: {summary.get('token', 'N/A')}
MIGRATION: {summary.get('migration_time', 'N/A')}

=== CORE METRICS ===

Liquidity:
- SOL: {summary.get('liquidity_sol', 0):.2f}
- Pool Locked: {summary.get('pool_locked', False)}
- SOL Reserve: {summary.get('sol_reserve', 0):.2f}

Distribution:
- Holders: {summary.get('holders', 0)}
- Top 1: {summary.get('top1_holder_pct', 0):.1f}%
- Top 5: {summary.get('top5_holder_pct', 0):.1f}%
- Concentration Risk: {summary.get('concentration_risk', 0):.2f}

Activity (1h):
- Transactions: {summary.get('tx_1h', 0)}
- Unique Wallets: {summary.get('wallets_1h', 0)}

Social:
- Phanes Velocity: {summary.get('phanes_velocity', 0)}
- Twitter Risk: {summary.get('twitter_risk', 5.0)}/10

Pre-Migration:
- Hours on Curve: {summary.get('hours_on_curve', 0):.1f}h
- Buy/Sell Ratio: {summary.get('buy_sell_ratio', 0):.2f}
- Pre-Volume: {summary.get('pre_volume_sol', 0):.1f} SOL
"""

        # Add ML prediction
        if 'ml_prediction' in summary:
            ml = summary['ml_prediction']
            prompt += f"""
=== ML MODEL PREDICTION ===
- Predicted 24h Return: {ml.get('return_24h', 0):.1f}%
- Model Confidence: {ml.get('confidence', 0)*100:.0f}%
"""

        # Add similar patterns context
        if include_reasoning_context and 'similar_patterns' in summary:
            patterns = summary['similar_patterns']
            prompt += f"""
=== SIMILAR HISTORICAL PATTERNS ===
Found {patterns.get('count', 0)} similar tokens with:
- Average Outcome: {patterns.get('avg_outcome', 0):.1f}%
- Win Rate: {patterns.get('win_rate', 0):.1f}%
- Historical Confidence: {patterns.get('confidence', 'NONE')}

Top Examples:
"""
            for i, example in enumerate(patterns.get('top_examples', []), 1):
                prompt += f"  {i}. {example.get('token', 'N/A')} -> {example.get('outcome_24h', 0):+.1f}% ({example.get('category', 'unknown')})\n"

        # Add wallet intelligence
        if 'wallets' in summary:
            wallets = summary['wallets']
            prompt += f"""
=== WALLET INTELLIGENCE ===
- Whale Count (>5%): {wallets.get('whale_count', 0)}
- Insider Risk Score: {wallets.get('insider_risk', 0)}/10
- Profitable Wallets: {wallets.get('profitable_wallets', 0)}
"""

        return prompt

    def estimate_token_count(self, summary: Dict[str, Any]) -> int:
        """
        Estimate Claude API token count for this summary

        Args:
            summary: Compact summary dict

        Returns:
            Estimated token count
        """
        # Format as prompt
        prompt_text = self.format_for_claude_prompt(summary)

        # Rough estimate: ~4 chars per token
        char_count = len(prompt_text)
        estimated_tokens = char_count // 4

        return estimated_tokens

    def get_summary_stats(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about the summary

        Args:
            summary: Compact summary dict

        Returns:
            Stats dict
        """
        return {
            'total_keys': len(summary),
            'estimated_tokens': self.estimate_token_count(summary),
            'has_ml_prediction': 'ml_prediction' in summary,
            'has_similar_patterns': 'similar_patterns' in summary,
            'has_wallet_intel': 'wallets' in summary,
            'input_hash': self.generate_input_hash(summary, include_timestamp=False)
        }


# Example usage
if __name__ == "__main__":
    generator = CompactSummaryGenerator()

    # Mock full features (normally 50+)
    full_features = {
        'token_address': 'SOL_TOKEN_12345678',
        'migration_time': '2025-01-10T12:30:00',
        'initial_liquidity_sol': 15.5,
        'pool_locked': 1,
        'sol_reserve': 14.8,
        'holder_count': 234,
        'top1_holder_pct': 0.12,
        'top5_holder_pct': 0.35,
        'concentration_risk': 0.25,
        'tx_count_1h': 87,
        'unique_wallets_1h': 65,
        'phanes_scan_velocity': 42,
        'twitter_risk_score': 4.0,
        'time_on_bonding_curve_hours': 12.5,
        'buy_sell_ratio': 1.8,
        'total_volume_pre_migration_sol': 234.5,
        # ... 40+ more features normally
    }

    model_prediction = {
        'return_24h': 0.25,  # 25%
        'confidence': 0.68
    }

    similar_patterns = {
        'similar_pattern_count': 5,
        'historical_avg_outcome': 18.5,  # %
        'historical_win_rate': 60.0,  # %
        'confidence': 'MEDIUM',
        'examples': [
            {'token': 'ABC12345...', 'outcome_24h': 25.0, 'category': 'high_liquidity', 'distance': 0.12},
            {'token': 'DEF67890...', 'outcome_24h': 15.0, 'category': 'high_liquidity', 'distance': 0.18},
            {'token': 'GHI11111...', 'outcome_24h': -5.0, 'category': 'high_liquidity', 'distance': 0.22}
        ]
    }

    wallet_intelligence = {
        'whale_count': 3,
        'insider_risk_score': 4,
        'highly_profitable_wallets': [{'address': 'WALLET1'}, {'address': 'WALLET2'}]
    }

    # Generate compact summary
    summary = generator.generate_compact_summary(
        full_features,
        model_prediction,
        similar_patterns,
        wallet_intelligence
    )

    print("=== COMPACT SUMMARY ===")
    print(json.dumps(summary, indent=2))

    # Format for Claude
    print("\n=== FORMATTED FOR CLAUDE ===")
    claude_prompt = generator.format_for_claude_prompt(summary)
    print(claude_prompt)

    # Get stats
    print("\n=== SUMMARY STATS ===")
    stats = generator.get_summary_stats(summary)
    print(json.dumps(stats, indent=2))

    # Generate hash for caching
    input_hash = generator.generate_input_hash(summary, include_timestamp=False)
    print(f"\nInput Hash: {input_hash}")
