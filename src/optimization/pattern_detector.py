"""
AI-Powered Pattern Detection
Uses Claude to analyze trading results and identify patterns
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from loguru import logger

from src.agents.claude_agent import ClaudeAgent


class PatternDetector:
    """Uses Claude AI to detect patterns in trading results"""

    def __init__(self):
        """Initialize pattern detector"""
        self.claude_agent = ClaudeAgent()

    async def analyze_trading_performance(
        self,
        trades: List[Dict[str, Any]],
        current_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze trading performance and identify patterns

        Args:
            trades: List of completed trades
            current_parameters: Current strategy parameters

        Returns:
            Analysis with patterns and recommendations
        """
        logger.info(f"Analyzing {len(trades)} trades with Claude AI...")

        # Build comprehensive prompt
        prompt = self._build_analysis_prompt(trades, current_parameters)

        # Send to Claude for analysis
        try:
            response = await self.claude_agent._call_claude(prompt)

            # Parse Claude's response
            analysis = self._parse_claude_response(response)

            logger.info(f"Claude identified {len(analysis.get('patterns', []))} patterns")
            logger.info(f"Claude suggested {len(analysis.get('recommendations', []))} adjustments")

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing with Claude: {e}")
            return {
                'error': str(e),
                'patterns': [],
                'recommendations': []
            }

    def _build_analysis_prompt(
        self,
        trades: List[Dict[str, Any]],
        current_parameters: Dict[str, Any]
    ) -> str:
        """Build detailed prompt for Claude analysis"""

        # Calculate summary statistics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        # Group by categories
        by_token_type = {}
        by_entry_strategy = {}
        by_confidence = {}
        by_risk_score = {}

        for trade in trades:
            # By token type
            token_type = trade.get('token_type', 'unknown')
            if token_type not in by_token_type:
                by_token_type[token_type] = []
            by_token_type[token_type].append(trade)

            # By entry strategy
            entry_strategy = trade.get('entry_strategy', 'unknown')
            if entry_strategy not in by_entry_strategy:
                by_entry_strategy[entry_strategy] = []
            by_entry_strategy[entry_strategy].append(trade)

            # By confidence
            confidence = trade.get('confidence', 'MEDIUM')
            if confidence not in by_confidence:
                by_confidence[confidence] = []
            by_confidence[confidence].append(trade)

            # By risk score
            risk = trade.get('risk_score', 5)
            risk_bucket = 'low' if risk <= 3 else 'medium' if risk <= 6 else 'high'
            if risk_bucket not in by_risk_score:
                by_risk_score[risk_bucket] = []
            by_risk_score[risk_bucket].append(trade)

        # Build prompt
        prompt = f"""You are an expert trading strategy analyst. Analyze these paper trading results and identify patterns to optimize the strategy.

=== OVERALL PERFORMANCE ===
Total Trades: {total_trades}
Winning Trades: {len(winning_trades)} ({win_rate*100:.1f}%)
Losing Trades: {len(losing_trades)} ({(1-win_rate)*100:.1f}%)
Average Win: ${avg_win:.2f}
Average Loss: ${avg_loss:.2f}
Profit Factor: {abs(avg_win / avg_loss) if avg_loss != 0 else 0:.2f}x

=== CURRENT STRATEGY PARAMETERS ===
{json.dumps(current_parameters, indent=2)}

=== PERFORMANCE BY TOKEN TYPE ===
"""

        for token_type, type_trades in by_token_type.items():
            type_wins = [t for t in type_trades if t.get('pnl', 0) > 0]
            type_win_rate = len(type_wins) / len(type_trades) if type_trades else 0
            type_avg_pnl = sum(t['pnl'] for t in type_trades) / len(type_trades) if type_trades else 0

            prompt += f"""
{token_type.upper()}:
  Trades: {len(type_trades)}
  Win Rate: {type_win_rate*100:.1f}%
  Avg P&L: ${type_avg_pnl:.2f}
"""

        prompt += "\n=== PERFORMANCE BY ENTRY STRATEGY ===\n"

        for strategy, strat_trades in by_entry_strategy.items():
            strat_wins = [t for t in strat_trades if t.get('pnl', 0) > 0]
            strat_win_rate = len(strat_wins) / len(strat_trades) if strat_trades else 0
            strat_avg_pnl = sum(t['pnl'] for t in strat_trades) / len(strat_trades) if strat_trades else 0

            prompt += f"""
{strategy.upper()}:
  Trades: {len(strat_trades)}
  Win Rate: {strat_win_rate*100:.1f}%
  Avg P&L: ${strat_avg_pnl:.2f}
"""

        prompt += "\n=== PERFORMANCE BY CONFIDENCE LEVEL ===\n"

        for conf, conf_trades in by_confidence.items():
            conf_wins = [t for t in conf_trades if t.get('pnl', 0) > 0]
            conf_win_rate = len(conf_wins) / len(conf_trades) if conf_trades else 0
            conf_avg_pnl = sum(t['pnl'] for t in conf_trades) / len(conf_trades) if conf_trades else 0

            prompt += f"""
{conf}:
  Trades: {len(conf_trades)}
  Win Rate: {conf_win_rate*100:.1f}%
  Avg P&L: ${conf_avg_pnl:.2f}
"""

        prompt += "\n=== PERFORMANCE BY RISK SCORE ===\n"

        for risk, risk_trades in by_risk_score.items():
            risk_wins = [t for t in risk_trades if t.get('pnl', 0) > 0]
            risk_win_rate = len(risk_wins) / len(risk_trades) if risk_trades else 0
            risk_avg_pnl = sum(t['pnl'] for t in risk_trades) / len(risk_trades) if risk_trades else 0

            prompt += f"""
{risk.upper()} RISK (0-3=low, 4-6=medium, 7-10=high):
  Trades: {len(risk_trades)}
  Win Rate: {risk_win_rate*100:.1f}%
  Avg P&L: ${risk_avg_pnl:.2f}
"""

        # Add sample winning and losing trades
        prompt += "\n=== SAMPLE WINNING TRADES (Top 3) ===\n"
        top_wins = sorted(winning_trades, key=lambda t: t.get('pnl', 0), reverse=True)[:3]
        for i, trade in enumerate(top_wins, 1):
            prompt += f"""
Trade {i}:
  Symbol: {trade.get('symbol', 'N/A')}
  Token Type: {trade.get('token_type', 'N/A')}
  Entry Strategy: {trade.get('entry_strategy', 'N/A')}
  Confidence: {trade.get('confidence', 'N/A')}
  Risk Score: {trade.get('risk_score', 'N/A')}/10
  Entry Price: ${trade.get('entry_price', 0):.8f}
  Exit Price: ${trade.get('exit_price', 0):.8f}
  Return: {trade.get('return_pct', 0)*100:.1f}%
  P&L: ${trade.get('pnl', 0):.2f}
  Exit Reason: {trade.get('exit_reason', 'N/A')}
"""

        prompt += "\n=== SAMPLE LOSING TRADES (Worst 3) ===\n"
        worst_losses = sorted(losing_trades, key=lambda t: t.get('pnl', 0))[:3]
        for i, trade in enumerate(worst_losses, 1):
            prompt += f"""
Trade {i}:
  Symbol: {trade.get('symbol', 'N/A')}
  Token Type: {trade.get('token_type', 'N/A')}
  Entry Strategy: {trade.get('entry_strategy', 'N/A')}
  Confidence: {trade.get('confidence', 'N/A')}
  Risk Score: {trade.get('risk_score', 'N/A')}/10
  Entry Price: ${trade.get('entry_price', 0):.8f}
  Exit Price: ${trade.get('exit_price', 0):.8f}
  Return: {trade.get('return_pct', 0)*100:.1f}%
  P&L: ${trade.get('pnl', 0):.2f}
  Exit Reason: {trade.get('exit_reason', 'N/A')}
"""

        # Ask Claude for specific analysis
        prompt += """

=== YOUR TASK ===

Analyze this trading data and provide:

1. **KEY PATTERNS IDENTIFIED**
   - What's working well? (e.g., "Tech tokens with wait_for_dip have 80% win rate")
   - What's not working? (e.g., "Viral memes with immediate entry losing 60% of time")
   - Any surprising insights?

2. **ROOT CAUSE ANALYSIS**
   - WHY are certain patterns winning/losing?
   - Are stop losses too tight/loose?
   - Are take profit targets realistic?
   - Is token classification accurate?
   - Is entry timing optimal?

3. **SPECIFIC RECOMMENDATIONS** (Be very specific with numbers)
   - Stop Loss adjustments: "Increase tech token SL from 25% to 32%"
   - Take Profit adjustments: "Lower viral meme TP1 from 25% to 15%"
   - Entry strategy changes: "Use wait_for_dip for all tokens with <10 SOL liquidity"
   - Filtering rules: "Only trade HIGH confidence tokens"
   - Position sizing: "Reduce size for risk >7 from 10% to 5%"

4. **PRIORITY ACTIONS** (What to change first)
   - List 3-5 highest impact changes
   - Explain expected improvement

5. **RISKS & CAUTIONS**
   - What could go wrong with these changes?
   - What to monitor after implementing?

Respond in JSON format:
{
  "overall_assessment": "Brief summary of performance",
  "patterns": [
    {
      "category": "token_type|entry_strategy|confidence|risk|other",
      "description": "What you found",
      "metric": "win_rate|avg_pnl|profit_factor",
      "current_value": 0.65,
      "significance": "high|medium|low"
    }
  ],
  "recommendations": [
    {
      "category": "stop_loss|take_profit|entry_strategy|filtering|position_sizing",
      "parameter": "specific parameter name",
      "current_value": "current setting",
      "recommended_value": "new setting",
      "reasoning": "why this change",
      "expected_impact": "what improvement expected",
      "priority": "high|medium|low",
      "risk": "what could go wrong"
    }
  ],
  "priority_actions": [
    "Most important change to make first",
    "Second most important",
    "Third most important"
  ],
  "cautions": [
    "What to watch out for"
  ]
}

Be specific, data-driven, and actionable. These recommendations will be automatically implemented.
"""

        return prompt

    def _parse_claude_response(self, response: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response

        Args:
            response: Raw response from Claude

        Returns:
            Parsed analysis
        """
        try:
            # Try to find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                analysis = json.loads(json_str)
                return analysis
            else:
                logger.warning("No JSON found in Claude response, parsing as text")
                return {
                    'overall_assessment': response,
                    'patterns': [],
                    'recommendations': [],
                    'priority_actions': [],
                    'cautions': []
                }

        except Exception as e:
            logger.error(f"Error parsing Claude response: {e}")
            return {
                'error': f"Parse error: {e}",
                'raw_response': response,
                'patterns': [],
                'recommendations': []
            }

    async def close(self):
        """Cleanup"""
        await self.claude_agent.close()
