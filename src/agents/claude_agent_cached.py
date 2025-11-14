"""
Cached Claude Agent Wrapper
Adds caching and compact summary support to ClaudeAgent
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
import json

from .claude_agent import ClaudeAgent
from src.storage.datastore import DataStore
from src.storage.compact_summary import CompactSummaryGenerator


class CachedClaudeAgent:
    """
    Wrapper around ClaudeAgent that adds:
    1. Response caching to avoid redundant API calls
    2. Compact summary usage to reduce token costs
    3. Cost tracking and analytics
    """

    def __init__(
        self,
        api_key: str,
        datastore: DataStore,
        summary_generator: CompactSummaryGenerator,
        model: str = "claude-3-haiku-20240307",
        use_cache: bool = True
    ):
        """
        Initialize cached Claude agent

        Args:
            api_key: Anthropic API key
            datastore: DataStore for caching
            summary_generator: CompactSummaryGenerator instance
            model: Claude model to use (haiku for cost savings)
            use_cache: Whether to use caching
        """
        self.agent = ClaudeAgent(api_key=api_key, model=model)
        self.datastore = datastore
        self.summary_generator = summary_generator
        self.use_cache = use_cache

        # Cost tracking
        self.total_api_calls = 0
        self.cache_hits = 0
        self.total_tokens_used = 0
        self.total_tokens_saved = 0

        logger.info(f"Initialized CachedClaudeAgent (cache={'ON' if use_cache else 'OFF'})")

    def analyze_token_compact(
        self,
        token_address: str,
        compact_summary: Dict[str, Any],
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze token using compact summary instead of full features

        Args:
            token_address: Token address
            compact_summary: Compact summary dict (from CompactSummaryGenerator)
            force_refresh: Force new API call even if cached

        Returns:
            Analysis dict
        """
        # Generate input hash for caching
        input_hash = self.summary_generator.generate_input_hash(
            compact_summary,
            include_timestamp=False
        )

        # Check cache first
        if self.use_cache and not force_refresh:
            cached = self.datastore.get_cached_decision(input_hash)

            if cached:
                logger.info(f"Cache HIT for {token_address[:8]}... (saved API call)")
                self.cache_hits += 1

                # Estimate tokens saved
                estimated_tokens = self.summary_generator.estimate_token_count(compact_summary)
                self.total_tokens_saved += estimated_tokens

                return {
                    'token_address': token_address,
                    'recommendation': cached['recommendation'],
                    'confidence': cached['confidence'],
                    'risk_score': cached['risk_score'],
                    'opportunity_score': cached['opportunity_score'],
                    'reasoning': cached['reasoning'],
                    'cached': True,
                    'timestamp': cached['created_at']
                }

        # Cache miss - call Claude API
        logger.info(f"Cache MISS for {token_address[:8]}... - calling Claude API")

        # Build simplified prompt using compact summary
        prompt = self._build_compact_prompt(compact_summary)

        # Call Claude
        try:
            response = self.agent.client.messages.create(
                model=self.agent.model,
                max_tokens=1500,  # Reduced from 2000 (more concise responses)
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )

            analysis_text = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Track costs
            self.total_api_calls += 1
            self.total_tokens_used += tokens_used

            # Parse response
            analysis = self._parse_analysis(analysis_text)
            analysis['token_address'] = token_address
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['raw_response'] = analysis_text
            analysis['cached'] = False
            analysis['tokens_used'] = tokens_used

            # Cache the decision
            if self.use_cache:
                self.datastore.cache_claude_decision(
                    token_address=token_address,
                    migration_time=datetime.fromisoformat(compact_summary.get('migration_time', datetime.now().isoformat())),
                    input_hash=input_hash,
                    recommendation=analysis.get('recommendation', 'HOLD'),
                    confidence=analysis.get('confidence', 'MEDIUM'),
                    risk_score=analysis.get('risk_score', 5),
                    opportunity_score=analysis.get('opportunity_score', 5),
                    reasoning=analysis,
                    model_used=self.agent.model,
                    tokens_used=tokens_used
                )

            logger.info(f"Claude analysis complete for {token_address[:8]}... ({tokens_used} tokens)")
            return analysis

        except Exception as e:
            logger.error(f"Error in Claude analysis: {e}")
            return {
                'token_address': token_address,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'cached': False
            }

    def _build_compact_prompt(self, compact_summary: Dict[str, Any]) -> str:
        """
        Build Claude prompt using compact summary

        Args:
            compact_summary: Compact summary dict

        Returns:
            Prompt string
        """
        # Use the summary generator to format for Claude
        formatted_metrics = self.summary_generator.format_for_claude_prompt(
            compact_summary,
            include_reasoning_context=True
        )

        # Add decision instructions
        prompt = f"""{formatted_metrics}

=== YOUR TASK ===

Analyze this token and provide a CONCISE trading decision.

IMPORTANT: Keep your response SHORT and FOCUSED. We're optimizing for cost.

Provide:

1. RISK ASSESSMENT (1-10):
   - Overall risk score: X/10
   - Top 3 risk factors (brief bullet points)

2. OPPORTUNITY ASSESSMENT (1-10):
   - Overall opportunity score: X/10
   - Top 3 bullish signals (brief bullet points)

3. RECOMMENDATION:
   - Action: BUY / HOLD / AVOID
   - Confidence: HIGH / MEDIUM / LOW
   - Position size: X% of portfolio
   - One-line reasoning

4. KEY INSIGHT (1 sentence):
   - What's the single most important factor for this decision?

5. PATTERN ALIGNMENT:
   - Do the similar patterns support this decision? (Yes/No + 1 sentence why)

Be concise. Total response should be <300 words.
"""

        return prompt

    def _parse_analysis(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's compact response

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed analysis dict
        """
        analysis = {
            'raw_text': response_text,
            'risk_score': 5,
            'opportunity_score': 5,
            'recommendation': 'HOLD',
            'confidence': 'MEDIUM',
            'key_insights': [],
            'risk_factors': [],
            'bullish_signals': []
        }

        lines = response_text.split('\n')

        for line in lines:
            line_lower = line.lower()

            # Extract risk score
            if 'risk' in line_lower and 'score' in line_lower:
                try:
                    import re
                    matches = re.findall(r'(\d+)/10', line)
                    if matches:
                        analysis['risk_score'] = int(matches[0])
                except:
                    pass

            # Extract opportunity score
            if 'opportunity' in line_lower and 'score' in line_lower:
                try:
                    import re
                    matches = re.findall(r'(\d+)/10', line)
                    if matches:
                        analysis['opportunity_score'] = int(matches[0])
                except:
                    pass

            # Extract recommendation
            if 'action:' in line_lower:
                if 'buy' in line_lower:
                    analysis['recommendation'] = 'BUY'
                elif 'avoid' in line_lower:
                    analysis['recommendation'] = 'AVOID'
                elif 'hold' in line_lower:
                    analysis['recommendation'] = 'HOLD'

            # Extract confidence
            if 'confidence:' in line_lower:
                if 'high' in line_lower:
                    analysis['confidence'] = 'HIGH'
                elif 'low' in line_lower:
                    analysis['confidence'] = 'LOW'
                else:
                    analysis['confidence'] = 'MEDIUM'

        return analysis

    def get_cost_stats(self) -> Dict[str, Any]:
        """
        Get cost and usage statistics

        Returns:
            Stats dict
        """
        # Estimate cost (approximate rates for Claude 3 Haiku)
        # Input: $0.25 / 1M tokens, Output: $1.25 / 1M tokens
        # Rough estimate: average $0.50 / 1M tokens
        estimated_cost = (self.total_tokens_used / 1_000_000) * 0.50

        # Estimate savings from caching
        estimated_savings = (self.total_tokens_saved / 1_000_000) * 0.50

        cache_hit_rate = (
            self.cache_hits / (self.total_api_calls + self.cache_hits)
            if (self.total_api_calls + self.cache_hits) > 0
            else 0
        )

        return {
            'total_api_calls': self.total_api_calls,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': f"{cache_hit_rate*100:.1f}%",
            'total_tokens_used': self.total_tokens_used,
            'total_tokens_saved': self.total_tokens_saved,
            'estimated_cost_usd': f"${estimated_cost:.4f}",
            'estimated_savings_usd': f"${estimated_savings:.4f}"
        }

    def reset_stats(self):
        """Reset cost tracking stats"""
        self.total_api_calls = 0
        self.cache_hits = 0
        self.total_tokens_used = 0
        self.total_tokens_saved = 0
        logger.info("Cost stats reset")


# Example usage
if __name__ == "__main__":
    import os
    from src.storage.datastore import DataStore
    from src.storage.compact_summary import CompactSummaryGenerator

    # Initialize
    api_key = os.getenv('ANTHROPIC_API_KEY', 'your-api-key')
    datastore = DataStore("data/analytics.db")
    summary_generator = CompactSummaryGenerator()

    agent = CachedClaudeAgent(
        api_key=api_key,
        datastore=datastore,
        summary_generator=summary_generator,
        use_cache=True
    )

    # Mock compact summary
    compact_summary = {
        'token': 'SOL_TOK...',
        'migration_time': datetime.now().isoformat(),
        'liquidity_sol': 15.5,
        'pool_locked': True,
        'sol_reserve': 14.8,
        'holders': 234,
        'top1_holder_pct': 12.0,
        'top5_holder_pct': 35.0,
        'concentration_risk': 0.25,
        'tx_1h': 87,
        'wallets_1h': 65,
        'phanes_velocity': 42,
        'twitter_risk': 4.0,
        'hours_on_curve': 12.5,
        'buy_sell_ratio': 1.8,
        'pre_volume_sol': 234.5,
        'ml_prediction': {
            'return_24h': 25.0,
            'confidence': 0.68
        },
        'similar_patterns': {
            'count': 5,
            'avg_outcome': 18.5,
            'win_rate': 60.0,
            'confidence': 'MEDIUM',
            'top_examples': [
                {'token': 'ABC...', 'outcome_24h': 25.0, 'category': 'high_liquidity'},
                {'token': 'DEF...', 'outcome_24h': 15.0, 'category': 'high_liquidity'}
            ]
        }
    }

    # Analyze
    result = agent.analyze_token_compact(
        token_address="SOL_TOKEN_TEST",
        compact_summary=compact_summary
    )

    print("Analysis:", json.dumps(result, indent=2))

    # Get cost stats
    print("\nCost Stats:", json.dumps(agent.get_cost_stats(), indent=2))

    datastore.close()
