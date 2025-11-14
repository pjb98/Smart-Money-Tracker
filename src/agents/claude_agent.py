"""
Claude AI Agent for autonomous token analysis and decision-making
Acts as reasoning layer on top of ML predictions
"""
import anthropic
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
import json


class ClaudeAgent:
    """Claude-powered autonomous agent for token analysis"""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        Initialize Claude agent

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.conversation_history: List[Dict] = []
        logger.info(f"Initialized Claude agent with model {model}")

    def analyze_token(
        self,
        token_address: str,
        features: Dict[str, Any],
        model_prediction: Dict[str, Any],
        phanes_data: Optional[Dict[str, Any]] = None,
        recent_history: Optional[List[Dict]] = None,
        wallet_intelligence: Optional[Dict[str, Any]] = None,
        pre_migration_metrics: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a token and provide reasoning + recommendations

        Args:
            token_address: Token address
            features: Engineered features dict
            model_prediction: ML model output
            phanes_data: Phanes scan data
            recent_history: Recent similar tokens

        Returns:
            Analysis dict with reasoning and recommendations
        """
        logger.info(f"Analyzing token {token_address} with Claude")

        # Construct prompt
        prompt = self._build_analysis_prompt(
            token_address,
            features,
            model_prediction,
            phanes_data,
            recent_history,
            wallet_intelligence,
            pre_migration_metrics,
            additional_context
        )

        # Call Claude
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )

            analysis_text = response.content[0].text

            # Parse structured output
            analysis = self._parse_analysis(analysis_text)
            analysis['token_address'] = token_address
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['raw_response'] = analysis_text

            logger.info(f"Analysis complete for {token_address}")
            return analysis

        except Exception as e:
            logger.error(f"Error in Claude analysis: {e}")
            return {
                'token_address': token_address,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _build_analysis_prompt(
        self,
        token_address: str,
        features: Dict[str, Any],
        model_prediction: Dict[str, Any],
        phanes_data: Optional[Dict[str, Any]],
        recent_history: Optional[List[Dict]],
        wallet_intelligence: Optional[Dict[str, Any]],
        pre_migration_metrics: Optional[Dict[str, Any]],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build comprehensive analysis prompt"""

        prompt = f"""You are an expert crypto analyst specializing in Solana token migrations from Pumpfun to Raydium.

⚠️ IMPORTANT CONTEXT ABOUT PUMP.FUN MIGRATIONS:
- Pump.fun tokens migrate to Raydium ONLY after reaching ~$69k market cap on the bonding curve
- ALL migrated tokens have BURNED LIQUIDITY (automatically locked forever on Raydium)
- ALL migrated tokens have RENOUNCED CONTRACTS (no mint authority by design)
- ALL migrated tokens MUST have holders (required to reach graduation threshold)
- If holder_count shows as 0, this is a DATA COLLECTION ERROR - the token definitely has holders
- If initial_liquidity_sol shows as 0, this is a DATA COLLECTION ERROR - liquidity was burned on migration
- Focus your analysis on transaction patterns, holder distribution quality, and social signals

Analyze the following token that just migrated to Raydium and provide insights:

TOKEN: {token_address}
MIGRATION TIME: {features.get('migration_time', 'Unknown')}

=== ML MODEL PREDICTION ===
{json.dumps(model_prediction, indent=2)}

=== ON-CHAIN FEATURES ===
Liquidity:
- Initial SOL: {features.get('initial_liquidity_sol', 0):.2f}
- Token Reserve: {features.get('token_reserve', 0):.0f}
- SOL Reserve: {features.get('sol_reserve', 0):.2f}
- Pool Locked: {features.get('pool_locked', False)}

Holders:
- Total Holders: {features.get('holder_count', 0)}
- Top 1 Holder: {features.get('top1_holder_pct', 0)*100:.2f}%
- Top 5 Holders: {features.get('top5_holder_pct', 0)*100:.2f}%
- Gini Coefficient: {features.get('gini_coefficient', 0):.3f}

Transactions (recent):
- Last 1h: {features.get('tx_count_1h', 0)}
- Last 24h: {features.get('tx_count_24h', 0)}
- Unique Wallets (1h): {features.get('unique_wallets_1h', 0)}
"""

        # Add Dev Credibility features if available
        dev_cred_score = features.get('dev_credibility_score', None)
        if dev_cred_score is not None:
            risk_category = features.get('dev_risk_category', 1)
            risk_level = ['LOW', 'MEDIUM', 'HIGH'][risk_category]

            prompt += f"""
=== DEVELOPER CREDIBILITY & RUG RISK ===
Dev Credibility Score: {dev_cred_score:.1f}/100 (Risk Level: {risk_level})

Wallet Analysis:
- Wallet Age: {features.get('dev_wallet_age_days', 0)} days
- Is New Wallet (<7 days): {features.get('dev_is_new_wallet', 0) == 1}
- Tokens Created Count: {features.get('dev_tokens_created_count', 0)}
- Large Sells (>10 SOL) Count: {features.get('dev_large_sells_count', 0)}
- Rug Pull Indicators Found: {features.get('dev_rug_indicators_count', 0)}
- Quick Dump Pattern Detected: {features.get('dev_has_quick_dump_pattern', 0) == 1}

⚠️ CRITICAL RUG RISK FACTORS:
"""
            # Add warnings based on dev behavior
            warnings = []
            if features.get('dev_is_new_wallet', 0) == 1:
                warnings.append("🚩 VERY NEW DEVELOPER WALLET - High risk of inexperience or throwaway wallet")
            if features.get('dev_tokens_created_count', 0) > 10:
                warnings.append("🚩 SERIAL TOKEN CREATOR - Created 10+ tokens (possible rug factory)")
            if features.get('dev_large_sells_count', 0) > 5:
                warnings.append("🚩 HISTORY OF LARGE SELLS - Sold >10 SOL on 5+ occasions")
            if features.get('dev_has_quick_dump_pattern', 0) == 1:
                warnings.append("🚨 QUICK DUMP DETECTED - Created token then immediately sold (RUG PATTERN)")
            if dev_cred_score < 30:
                warnings.append("🚨 EXTREMELY LOW CREDIBILITY - Very high likelihood of rug pull")

            if warnings:
                for warning in warnings:
                    prompt += f"  {warning}\n"
            else:
                prompt += "  ✅ No major red flags detected in developer history\n"

            prompt += f"""
RECOMMENDATION: {"AVOID THIS TOKEN" if dev_cred_score < 30 else "EXTREME CAUTION" if dev_cred_score < 60 else "Proceed with normal risk assessment"}
"""

        # Add Phanes data if available
        if phanes_data:
            prompt += f"""
=== PHANES BOT SCAN DATA ===
- Scan Count: {phanes_data.get('scan_count', 0)}
- Scan Velocity: {phanes_data.get('avg_scan_velocity', 0)} scans/hour
- Popularity Rank: #{phanes_data.get('latest_rank', 999)}
- Rug Warning: {phanes_data.get('rug_warning', False)}
- Sentiment: {phanes_data.get('latest_sentiment', 'neutral')} (score: {phanes_data.get('avg_sentiment_score', 0):.2f})
"""

        # Add pre-migration metrics if available
        if pre_migration_metrics:
            prompt += f"""
=== PRE-MIGRATION METRICS (Pump.fun Bonding Curve) ===
Time on Curve:
- Hours: {pre_migration_metrics.get('time_on_bonding_curve_hours', 0):.2f}h
- Days: {pre_migration_metrics.get('time_on_bonding_curve_days', 0):.2f}d

Volume Metrics:
- Total Volume: {pre_migration_metrics.get('total_volume_pre_migration_sol', 0):.2f} SOL
- Buy Volume: {pre_migration_metrics.get('buy_volume_pre_migration_sol', 0):.2f} SOL
- Sell Volume: {pre_migration_metrics.get('sell_volume_pre_migration_sol', 0):.2f} SOL
- Total Trades: {pre_migration_metrics.get('total_trades_pre_migration', 0)}

Trading Behavior:
- Buy Count: {pre_migration_metrics.get('buy_count_pre_migration', 0)}
- Sell Count: {pre_migration_metrics.get('sell_count_pre_migration', 0)}
- Buy/Sell Ratio: {pre_migration_metrics.get('buy_sell_ratio', 0):.2f}

Wallet Activity:
- Unique Wallets: {pre_migration_metrics.get('unique_wallets_pre_migration', 0)}
- Unique Buyers: {pre_migration_metrics.get('unique_buyers_pre_migration', 0)}
- Unique Sellers: {pre_migration_metrics.get('unique_sellers_pre_migration', 0)}

Trade Sizes:
- Avg Trade: {pre_migration_metrics.get('avg_trade_size_sol', 0):.4f} SOL
- Avg Buy: {pre_migration_metrics.get('avg_buy_size_sol', 0):.4f} SOL
- Avg Sell: {pre_migration_metrics.get('avg_sell_size_sol', 0):.4f} SOL

Velocity:
- Trades/Hour: {pre_migration_metrics.get('trades_per_hour', 0):.2f}
- Volume/Hour: {pre_migration_metrics.get('volume_per_hour_sol', 0):.2f} SOL

Market Metrics:
- Market Cap: ${pre_migration_metrics.get('market_cap_usd', 0):.2f} ({pre_migration_metrics.get('market_cap_sol', 0):.2f} SOL)
- Bonding Curve Progress: {pre_migration_metrics.get('bonding_curve_progress_pct', 0):.2f}%
"""

        # Add wallet intelligence if available
        if wallet_intelligence:
            prompt += f"""
=== WALLET INTELLIGENCE (Whale & Insider Detection) ===
Whale Analysis:
- Total Whales (>5% holders): {wallet_intelligence.get('whale_count', 0)}
- Whale Combined Ownership: {wallet_intelligence.get('whale_total_percentage', 0):.2f}%

Profitable Wallet Detection:
- Highly Profitable Wallets (>70% win rate): {len(wallet_intelligence.get('highly_profitable_wallets', []))}

Insider Risk:
- Potential Insider Wallets: {len(wallet_intelligence.get('insider_wallets', []))}
- Insider Risk Score: {wallet_intelligence.get('insider_risk_score', 0)}/10

CRITICAL: Insider wallets are holders that are BOTH whales (>5%) AND have historically high win rates (>70%).
This is a RED FLAG if insider risk score > 5.
"""

            # Add details about specific whales if present
            whale_wallets = wallet_intelligence.get('whale_wallets', [])
            if whale_wallets:
                prompt += "\nTop Whale Holders:\n"
                for i, whale in enumerate(whale_wallets[:3], 1):
                    prompt += f"  {i}. {whale.get('address', '')[:8]}... - {whale.get('percentage', 0):.2f}%\n"

            # Add details about profitable wallets
            profitable = wallet_intelligence.get('highly_profitable_wallets', [])
            if profitable:
                prompt += "\nHighly Profitable Wallets Detected:\n"
                for i, wallet in enumerate(profitable[:3], 1):
                    prompt += f"  {i}. {wallet.get('address', '')[:8]}... - Win Rate: {wallet.get('win_rate', 0):.1f}% | Avg ROI: {wallet.get('avg_roi', 0):.1f}%\n"

            # Add details about insiders
            insiders = wallet_intelligence.get('insider_wallets', [])
            if insiders:
                prompt += "\n🚨 INSIDER WALLETS DETECTED:\n"
                for i, insider in enumerate(insiders, 1):
                    prompt += f"  {i}. {insider.get('address', '')[:8]}... - Holds {insider.get('percentage_held', 0):.2f}% | Win Rate: {insider.get('win_rate', 0):.1f}%\n"

        # Add Cabal Detection if available (NEW - #1 predictive indicator!)
        cabal_analysis = features.get('cabal_analysis_full')
        if cabal_analysis and cabal_analysis.get('has_cabal_involvement'):
            risk_assessment = cabal_analysis.get('risk_assessment', 'NONE')

            # Map risk to emoji
            risk_emoji = {
                'BULLISH': '🟢',
                'NEUTRAL': '🟡',
                'TOXIC': '🔴',
                'NONE': '⚪'
            }.get(risk_assessment, '⚪')

            prompt += f"""
=== CABAL WALLET DETECTION (🎯 #1 PREDICTIVE INDICATOR) ===
{risk_emoji} Risk Assessment: {risk_assessment}

Cabal Summary:
- Cabals Detected: {cabal_analysis.get('cabal_count', 0)}
- Total Cabal Wallets: {cabal_analysis.get('total_cabal_wallets', 0)}
- Cabal Percentage of Holders: {cabal_analysis.get('cabal_percentage', 0):.2f}%
- Average Cabal Win Rate: {cabal_analysis.get('avg_cabal_winrate', 0)*100:.1f}%
- Bullish Cabals: {cabal_analysis.get('bullish_cabals', 0)}
- Toxic Cabals: {cabal_analysis.get('toxic_cabals', 0)}
- High Confidence Signal: {cabal_analysis.get('confidence_high', False)} (2+ cabals = high confidence)

"""
            # Add details about each detected cabal
            cabals_detected = cabal_analysis.get('cabals_detected', [])
            if cabals_detected:
                prompt += "Detected Cabals:\n"
                for i, cabal in enumerate(cabals_detected, 1):
                    cabal_risk = cabal.get('risk_level', 'UNKNOWN')
                    cabal_emoji = {
                        'BULLISH': '🟢',
                        'NEUTRAL': '🟡',
                        'TOXIC': '🔴',
                        'UNKNOWN': '⚪'
                    }.get(cabal_risk, '⚪')

                    prompt += f"  {i}. {cabal_emoji} {cabal.get('cabal_name', 'Unknown')} (ID: {cabal.get('cabal_id', 'N/A')})\n"
                    prompt += f"     - Win Rate: {cabal.get('winrate', 0)*100:.1f}%\n"
                    prompt += f"     - Risk Level: {cabal_risk}\n"
                    prompt += f"     - Wallets in Token: {cabal.get('wallet_count', 0)}\n"

            prompt += """
⚠️ CRITICAL CABAL INTERPRETATION:
- BULLISH CABALS (🟢): High win rate groups that create real pump momentum. Their involvement INCREASES confidence.
- NEUTRAL CABALS (🟡): Mixed track record. Proceed with normal caution.
- TOXIC CABALS (🔴): Known rug pullers with coordinated exit scams. AVOID or use extremely tight stop loss.
- Multiple cabals detected = HIGH CONFIDENCE signal (they rarely coordinate unless opportunity is real)
- High cabal % + BULLISH = Strong buy signal with larger position size
- ANY toxic cabal involvement = Major red flag that may override all positive signals
"""

        elif features.get('cabal_involvement', 0) == 0:
            # Explicitly note no cabal involvement
            prompt += """
=== CABAL WALLET DETECTION ===
⚪ No Known Cabal Involvement Detected

Note: This token shows no involvement from tracked cabal groups. Rely on other indicators for analysis.
"""

        # Add Twitter analysis if available
        if additional_context and 'twitter_analysis' in additional_context:
            twitter_analysis = additional_context['twitter_analysis']
            if not twitter_analysis.get('limited_data'):
                prompt += f"""
=== TWITTER ACCOUNT ANALYSIS (Social Legitimacy) ===
Account: @{twitter_analysis.get('username', 'N/A')}
Risk Score: {twitter_analysis.get('risk_score', 'N/A')}/10 ({twitter_analysis.get('risk_level', 'UNKNOWN')})

Account Age:
- Age: {twitter_analysis.get('age_analysis', {}).get('account_age_days', 0)} days
- New Account Flag: {twitter_analysis.get('age_analysis', {}).get('is_new_account', False)}
- Very New Account Flag: {twitter_analysis.get('age_analysis', {}).get('is_very_new_account', False)}

Follower Metrics:
- Followers: {twitter_analysis.get('follower_analysis', {}).get('followers_count', 0):,}
- Following: {twitter_analysis.get('follower_analysis', {}).get('following_count', 0):,}
- Follower Ratio: {twitter_analysis.get('follower_analysis', {}).get('follower_following_ratio', 0):.2f}
- Verified: {twitter_analysis.get('account_info', {}).get('verified', False)}

Engagement:
- Avg Engagement: {twitter_analysis.get('engagement_analysis', {}).get('avg_engagement_rate', 0):.1f} per tweet
- Tweets Analyzed: {twitter_analysis.get('engagement_analysis', {}).get('total_tweets_analyzed', 0)}

Key Insights:
"""
                for insight in twitter_analysis.get('insights', []):
                    prompt += f"  {insight}\n"

        # Add recent history context
        if recent_history:
            prompt += f"""
=== RECENT SIMILAR TOKENS ===
Here are {len(recent_history)} recent similar tokens for context:
{json.dumps(recent_history[:3], indent=2)}
"""

        # Request structured analysis with DETAILED reasoning
        prompt += """
Based on ALL the data above, provide a comprehensive structured analysis.

IMPORTANT: This analysis will be stored for backtesting and future learning. Be VERY DETAILED in your reasoning so we can understand WHY you made this decision later.

1. RISK ASSESSMENT (1-10 scale):
   - Overall risk score: X/10
   - Rug risk: Explain WHY (specific factors like liquidity, holder concentration, insider activity, **DEV CREDIBILITY SCORE**, **CABAL INVOLVEMENT**)
   - Developer risk: **CRITICAL** - What's the dev credibility score? Are there rug patterns? New wallet?
   - Cabal risk: **#1 PREDICTIVE INDICATOR** - Are toxic cabals involved? Bullish cabals? How many? Win rates?
   - Liquidity risk: Quantify and explain
   - Concentration risk: Specific numbers and implications
   - Social/legitimacy risk: Based on Twitter and online presence
   - List ALL major risk factors found (include dev red flags AND cabal warnings if any)

2. OPPORTUNITY ASSESSMENT (1-10 scale):
   - Overall opportunity score: X/10
   - Growth potential: WHY do you think this could pump? Specific evidence
   - Cabal opportunity: **#1 PREDICTIVE INDICATOR** - Are BULLISH cabals involved? What are their win rates? High confidence signal?
   - Community/hype: What signals suggest strong community?
   - Momentum: Pre and post-migration momentum analysis
   - Smart money: Are proven profitable wallets investing? (Include cabal wallets)
   - List ALL bullish signals found (especially cabal involvement)

3. DETAILED DECISION RATIONALE:
   - WHY are you making this recommendation? (Be specific - reference actual numbers)
   - What are the TOP 3 reasons to invest (if BUY) or avoid (if AVOID)? **PRIORITIZE cabal signals if present**
   - What are the TOP 3 concerns even if recommending BUY?
   - How do all the signals (on-chain, social, ML prediction, wallet intelligence, **CABAL DETECTION**) align?
   - **How heavily did cabal involvement influence your decision?** (This is the #1 indicator)
   - What's the risk/reward ratio?

4. RECOMMENDATION:
   - Action: BUY / HOLD / AVOID (and explain WHY in 2-3 sentences)
   - Confidence: HIGH / MEDIUM / LOW (explain what would increase confidence)
   - Position size: X% of portfolio (justify based on risk/reward)
   - Entry strategy: Specific plan (e.g., "Enter 50% now at market, 50% if dips below X")
   - Exit strategy: Specific targets (e.g., "Take 50% profit at +30%, stop loss at -20%")
   - Time horizon: How long should this position be held?

5. SUPPORTING EVIDENCE:
   - Which specific data points most influenced your decision?
   - What does the ML model predict and do you agree with it? Why/why not?
   - How does this compare to typical successful/failed tokens?

6. RED FLAGS & CONCERNS:
   - List EVERY red flag identified (even minor ones, **especially toxic cabal involvement**)
   - Which red flags are most concerning and why?
   - **CRITICAL: Is there toxic cabal involvement?** If yes, this is a MAJOR red flag
   - Are any red flags severe enough to override positive signals? (Toxic cabals usually are)

7. IF THIS DECISION IS WRONG:
   - What would we learn if this turns out to be a bad call?
   - What warning signs should we watch for?
   - At what point should we cut losses or re-evaluate?

8. NEXT ACTIONS:
   - Immediate actions to take in next 5 minutes
   - Monitoring plan for next 1-6 hours
   - Alerts to set up
   - Re-evaluation schedule

Be extremely detailed. Write as if you're explaining your reasoning to your future self for backtesting analysis."""

        return prompt

    def _parse_analysis(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's response into structured format"""

        analysis = {
            'raw_text': response_text,
            'risk_score': None,
            'opportunity_score': None,
            'recommendation': 'HOLD',
            'confidence': 'MEDIUM',
            'key_insights': [],
            'next_actions': []
        }

        # Simple parsing (could be enhanced with structured output)
        lines = response_text.split('\n')

        for line in lines:
            line_lower = line.lower()

            # Extract risk score
            if 'rug risk' in line_lower or 'risk assessment' in line_lower:
                try:
                    # Look for numbers 1-10
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

    def generate_alert(
        self,
        token_address: str,
        analysis: Dict[str, Any],
        alert_type: str = "NEW_MIGRATION"
    ) -> str:
        """
        Generate human-readable alert message

        Args:
            token_address: Token address
            analysis: Analysis dict from analyze_token
            alert_type: Type of alert

        Returns:
            Alert message string
        """
        prompt = f"""Generate a concise Telegram/Discord alert message for this token analysis:

TOKEN: {token_address}
ANALYSIS: {json.dumps(analysis, indent=2)}
ALERT TYPE: {alert_type}

Create a short (2-3 paragraphs) alert message that includes:
- Token address (truncated)
- ML prediction
- Risk assessment
- Recommendation
- Key action items

Use emojis sparingly for emphasis. Be professional but engaging."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )

            alert_message = response.content[0].text
            return alert_message

        except Exception as e:
            logger.error(f"Error generating alert: {e}")
            # Fallback alert
            return f"New token migration: {token_address[:8]}...\nRecommendation: {analysis.get('recommendation', 'UNKNOWN')}"

    def detect_anomaly(
        self,
        token_data: Dict[str, Any],
        threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Detect if token shows anomalous patterns

        Args:
            token_data: Token features and metrics
            threshold: Anomaly threshold

        Returns:
            Anomaly detection result
        """
        prompt = f"""Analyze this token data for anomalous or suspicious patterns:

{json.dumps(token_data, indent=2)}

Look for:
- Unusual holder concentration
- Suspicious transaction patterns
- Signs of bot activity
- Potential rug pull indicators
- Unrealistic hype vs fundamentals

Respond with:
1. Is this token anomalous? (YES/NO)
2. Anomaly score (0-1)
3. Specific red flags found
4. Recommendation (INVESTIGATE / FLAG / SAFE)
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.5,
                messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse result
            is_anomalous = 'yes' in result_text.lower()[:200]

            return {
                'is_anomalous': is_anomalous,
                'analysis': result_text,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return {
                'is_anomalous': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


# Example usage
def main():
    import os

    # Initialize agent (requires ANTHROPIC_API_KEY env var)
    api_key = os.getenv('ANTHROPIC_API_KEY', 'your-api-key-here')

    if api_key == 'your-api-key-here':
        print("Please set ANTHROPIC_API_KEY environment variable")
        return

    agent = ClaudeAgent(api_key=api_key)

    # Mock data
    token_address = "MOCK" + "x" * 40
    features = {
        'migration_time': datetime.now().isoformat(),
        'initial_liquidity_sol': 10.5,
        'holder_count': 234,
        'top1_holder_pct': 0.15,
        'top5_holder_pct': 0.35,
        'gini_coefficient': 0.45,
        'tx_count_1h': 87,
        'tx_count_24h': 456,
        'pool_locked': True
    }

    model_prediction = {
        'prediction': 0.25,
        'return_24h': 0.25,
        'pump_24h_probability': 0.68
    }

    phanes_data = {
        'scan_count': 345,
        'avg_scan_velocity': 42,
        'latest_rank': 8,
        'rug_warning': False,
        'latest_sentiment': 'bullish',
        'avg_sentiment_score': 0.7
    }

    # Analyze
    analysis = agent.analyze_token(
        token_address,
        features,
        model_prediction,
        phanes_data
    )

    print("Analysis:", json.dumps(analysis, indent=2))

    # Generate alert
    alert = agent.generate_alert(token_address, analysis)
    print("\nAlert:\n", alert)


if __name__ == "__main__":
    main()
