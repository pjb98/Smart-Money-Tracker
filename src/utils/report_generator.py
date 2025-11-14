"""
Comprehensive Report Generator
Creates detailed investment rationale reports for every token analysis
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
from loguru import logger


class ReportGenerator:
    """
    Generates comprehensive, human-readable reports explaining
    why decisions were made for each token
    """

    def __init__(self, output_dir: str = "data/reports"):
        """
        Initialize report generator

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized report generator: {output_dir}")

    @staticmethod
    def _safe_get(d: Optional[Dict], key: str, default: Any = 0) -> Any:
        """
        Safely get value from dict, handling None values

        Args:
            d: Dictionary to get from (can be None)
            key: Key to retrieve
            default: Default value if key missing or value is None

        Returns:
            Value from dict or default
        """
        if d is None:
            return default
        value = d.get(key, default)
        return value if value is not None else default

    def generate_comprehensive_report(
        self,
        token_address: str,
        migration_event: Dict[str, Any],
        features: Dict[str, Any],
        prediction: Dict[str, Any],
        claude_analysis: Optional[Dict[str, Any]] = None,
        twitter_analysis: Optional[Dict[str, Any]] = None,
        wallet_intelligence: Optional[Dict[str, Any]] = None,
        pre_migration_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report

        Args:
            token_address: Token mint address
            migration_event: Migration event data
            features: Engineered features
            prediction: ML model prediction
            claude_analysis: Claude AI analysis
            twitter_analysis: Twitter account analysis
            wallet_intelligence: Wallet intelligence data
            pre_migration_metrics: Pre-migration metrics

        Returns:
            Complete report dict
        """
        logger.info(f"Generating comprehensive report for {token_address[:8]}...")

        report = {
            'report_id': self._generate_report_id(token_address),
            'generated_at': datetime.now().isoformat(),
            'token_address': token_address,
            'symbol': migration_event.get('symbol', 'UNKNOWN'),
            'name': migration_event.get('name', 'Unknown Token'),
            'migration_time': migration_event.get('migration_time'),
        }

        # SECTION 1: Executive Summary
        report['executive_summary'] = self._generate_executive_summary(
            migration_event, prediction, claude_analysis, features
        )

        # SECTION 2: Decision & Rationale
        report['decision'] = self._generate_decision_section(
            claude_analysis, prediction, features
        )

        # SECTION 3: Key Metrics Analysis
        report['key_metrics'] = self._analyze_key_metrics(
            features, pre_migration_metrics, wallet_intelligence, twitter_analysis
        )

        # SECTION 4: Risk Assessment
        report['risk_assessment'] = self._generate_risk_assessment(
            features, claude_analysis, wallet_intelligence, twitter_analysis
        )

        # SECTION 5: Opportunity Analysis
        report['opportunity_analysis'] = self._generate_opportunity_analysis(
            features, prediction, claude_analysis, pre_migration_metrics
        )

        # SECTION 6: Signal Breakdown
        report['signal_breakdown'] = self._breakdown_signals(
            features, prediction, pre_migration_metrics, twitter_analysis, wallet_intelligence
        )

        # SECTION 7: Supporting Evidence
        report['supporting_evidence'] = self._compile_supporting_evidence(
            prediction, features, claude_analysis
        )

        # SECTION 8: Red Flags & Concerns
        report['red_flags'] = self._identify_red_flags(
            features, wallet_intelligence, twitter_analysis, pre_migration_metrics
        )

        # SECTION 9: Comparative Context
        report['comparative_context'] = self._generate_comparative_context(
            features, pre_migration_metrics
        )

        # SECTION 10: Action Plan
        report['action_plan'] = self._generate_action_plan(
            claude_analysis, prediction, features
        )

        # Save full data for backtesting
        report['raw_data'] = {
            'features': features,
            'prediction': prediction,
            'claude_analysis': claude_analysis,
            'twitter_analysis': twitter_analysis,
            'wallet_intelligence': wallet_intelligence,
            'pre_migration_metrics': pre_migration_metrics
        }

        return report

    def _generate_report_id(self, token_address: str) -> str:
        """Generate unique report ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{token_address[:8]}"

    def _generate_executive_summary(
        self,
        migration_event: Dict[str, Any],
        prediction: Dict[str, Any],
        claude_analysis: Optional[Dict[str, Any]],
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary"""

        recommendation = self._safe_get(claude_analysis, 'recommendation', 'HOLD') if claude_analysis else 'UNKNOWN'
        confidence = self._safe_get(claude_analysis, 'confidence', 'MEDIUM') if claude_analysis else 'LOW'

        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'predicted_return_24h': self._safe_get(prediction, 'prediction', 0),
            'risk_score': self._safe_get(claude_analysis, 'risk_score', 5) if claude_analysis else 5,
            'opportunity_score': self._safe_get(claude_analysis, 'opportunity_score', 5) if claude_analysis else 5,
            'initial_liquidity_sol': self._safe_get(features, 'initial_liquidity_sol', 0),
            'holder_count': self._safe_get(features, 'holder_count', 0),
            'one_line_summary': self._create_one_line_summary(recommendation, confidence, prediction, features)
        }

    def _create_one_line_summary(
        self,
        recommendation: str,
        confidence: str,
        prediction: Dict[str, Any],
        features: Dict[str, Any]
    ) -> str:
        """Create concise one-line summary"""

        liquidity = self._safe_get(features, 'initial_liquidity_sol', 0)
        holders = self._safe_get(features, 'holder_count', 0)
        predicted_return = self._safe_get(prediction, 'prediction', 0) * 100

        if recommendation == 'BUY':
            return f"🟢 {confidence} confidence BUY: {predicted_return:.1f}% predicted return, {liquidity:.1f} SOL liquidity, {holders} holders"
        elif recommendation == 'AVOID':
            return f"🔴 {confidence} confidence AVOID: High risk detected with {predicted_return:.1f}% predicted return"
        else:
            return f"🟡 {confidence} confidence HOLD: Mixed signals with {predicted_return:.1f}% predicted return"

    def _generate_decision_section(
        self,
        claude_analysis: Optional[Dict[str, Any]],
        prediction: Dict[str, Any],
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate detailed decision reasoning"""

        if not claude_analysis:
            return {
                'action': 'HOLD',
                'reasoning': 'No AI analysis available - defaulting to HOLD',
                'confidence_factors': [],
                'key_drivers': []
            }

        return {
            'action': claude_analysis.get('recommendation', 'HOLD'),
            'confidence': claude_analysis.get('confidence', 'MEDIUM'),
            'reasoning': claude_analysis.get('raw_text', 'No detailed reasoning available'),
            'risk_score': claude_analysis.get('risk_score', 5),
            'opportunity_score': claude_analysis.get('opportunity_score', 5),
            'position_size_recommendation': self._recommend_position_size(
                claude_analysis.get('recommendation'),
                claude_analysis.get('confidence'),
                claude_analysis.get('risk_score', 5)
            ),
            'entry_strategy': self._recommend_entry_strategy(
                claude_analysis.get('recommendation'),
                features
            ),
            'exit_strategy': self._recommend_exit_strategy(
                prediction,
                claude_analysis.get('risk_score', 5)
            )
        }

    def _recommend_position_size(
        self,
        recommendation: str,
        confidence: str,
        risk_score: int
    ) -> str:
        """Recommend position size based on risk and confidence"""

        # Ensure risk_score is not None
        risk_score = risk_score if risk_score is not None else 5

        if recommendation == 'AVOID':
            return "0% - Do not invest"

        if recommendation == 'BUY':
            if confidence == 'HIGH' and risk_score <= 3:
                return "5-10% of portfolio (High confidence, low risk)"
            elif confidence == 'HIGH' and risk_score <= 6:
                return "3-5% of portfolio (High confidence, medium risk)"
            elif confidence == 'MEDIUM' and risk_score <= 4:
                return "2-4% of portfolio (Medium confidence, low-medium risk)"
            elif confidence == 'MEDIUM':
                return "1-2% of portfolio (Medium confidence, higher risk)"
            else:
                return "0.5-1% of portfolio (Lower confidence or higher risk)"

        return "0% - HOLD recommendation"

    def _recommend_entry_strategy(
        self,
        recommendation: str,
        features: Dict[str, Any]
    ) -> str:
        """Recommend entry strategy"""

        if recommendation != 'BUY':
            return "N/A - Not recommended for purchase"

        liquidity = features.get('initial_liquidity_sol', 0)

        if liquidity < 5:
            return "WAIT - Monitor for increased liquidity before entry"
        elif liquidity < 20:
            return "SMALL BUY - Enter with 25-50% of planned position, average in over 1-2 hours"
        else:
            return "IMMEDIATE - Can enter with full position immediately given strong liquidity"

    def _recommend_exit_strategy(
        self,
        prediction: Dict[str, Any],
        risk_score: int
    ) -> str:
        """Recommend exit strategy"""

        # Ensure risk_score is not None
        risk_score = risk_score if risk_score is not None else 5

        predicted_return = self._safe_get(prediction, 'prediction', 0) * 100

        if risk_score >= 7:
            return f"TIGHT STOPS - Set stop loss at -15%, take profit at +{predicted_return/2:.0f}% (50% of target)"
        elif risk_score >= 4:
            return f"MODERATE STOPS - Set stop loss at -25%, take profit ladder: 50% at +{predicted_return:.0f}%, 50% at +{predicted_return*1.5:.0f}%"
        else:
            return f"LOOSE STOPS - Set stop loss at -35%, take profit ladder: 30% at +{predicted_return:.0f}%, 40% at +{predicted_return*1.5:.0f}%, 30% at +{predicted_return*2:.0f}%"

    def _analyze_key_metrics(
        self,
        features: Dict[str, Any],
        pre_migration_metrics: Optional[Dict[str, Any]],
        wallet_intelligence: Optional[Dict[str, Any]],
        twitter_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze key metrics"""

        return {
            'liquidity': {
                'initial_sol': features.get('initial_liquidity_sol', 0),
                'rating': self._rate_liquidity(features.get('initial_liquidity_sol', 0)),
                'analysis': self._analyze_liquidity(features.get('initial_liquidity_sol', 0))
            },
            'holder_distribution': {
                'total_holders': features.get('holder_count', 0),
                'top1_pct': features.get('top1_holder_pct', 0) * 100,
                'top5_pct': features.get('top5_holder_pct', 0) * 100,
                'gini': features.get('gini_coefficient', 0),
                'rating': self._rate_holder_distribution(features),
                'analysis': self._analyze_holder_distribution(features)
            },
            'pre_migration_performance': self._analyze_pre_migration(pre_migration_metrics),
            'wallet_quality': self._analyze_wallet_quality(wallet_intelligence),
            'social_presence': self._analyze_social_presence(twitter_analysis, features)
        }

    def _rate_liquidity(self, liquidity_sol: float) -> str:
        """Rate liquidity quality"""
        if liquidity_sol >= 50:
            return "EXCELLENT"
        elif liquidity_sol >= 20:
            return "GOOD"
        elif liquidity_sol >= 10:
            return "FAIR"
        elif liquidity_sol >= 5:
            return "POOR"
        else:
            return "VERY POOR"

    def _analyze_liquidity(self, liquidity_sol: float) -> str:
        """Analyze liquidity implications"""
        if liquidity_sol >= 50:
            return f"{liquidity_sol:.1f} SOL is excellent liquidity. Large trades possible with minimal slippage. Reduces rug risk."
        elif liquidity_sol >= 20:
            return f"{liquidity_sol:.1f} SOL is good liquidity. Medium trades supported. Moderate rug risk."
        elif liquidity_sol >= 10:
            return f"{liquidity_sol:.1f} SOL is fair liquidity. Small trades only. Higher rug risk if unlocked."
        elif liquidity_sol >= 5:
            return f"{liquidity_sol:.1f} SOL is poor liquidity. Very small trades only. Significant rug risk."
        else:
            return f"{liquidity_sol:.1f} SOL is dangerously low liquidity. Extreme rug risk. Avoid."

    def _rate_holder_distribution(self, features: Dict[str, Any]) -> str:
        """Rate holder distribution"""
        top1 = features.get('top1_holder_pct', 0)
        gini = features.get('gini_coefficient', 0)

        if top1 < 0.10 and gini < 0.5:
            return "EXCELLENT"
        elif top1 < 0.20 and gini < 0.6:
            return "GOOD"
        elif top1 < 0.30 and gini < 0.7:
            return "FAIR"
        elif top1 < 0.40:
            return "POOR"
        else:
            return "VERY POOR"

    def _analyze_holder_distribution(self, features: Dict[str, Any]) -> str:
        """Analyze holder distribution implications"""
        top1 = features.get('top1_holder_pct', 0) * 100
        top5 = features.get('top5_holder_pct', 0) * 100
        gini = features.get('gini_coefficient', 0)
        holders = features.get('holder_count', 0)

        analysis = f"{holders} total holders. "

        if top1 > 30:
            analysis += f"⚠️ Top holder controls {top1:.1f}% - EXTREME concentration risk. "
        elif top1 > 20:
            analysis += f"⚠️ Top holder controls {top1:.1f}% - High concentration risk. "
        elif top1 > 10:
            analysis += f"Top holder controls {top1:.1f}% - Moderate concentration. "
        else:
            analysis += f"✅ Top holder only controls {top1:.1f}% - Good distribution. "

        if top5 > 60:
            analysis += f"Top 5 control {top5:.1f}% - Whale dominated."
        elif top5 > 40:
            analysis += f"Top 5 control {top5:.1f}% - Moderately concentrated."
        else:
            analysis += f"Top 5 control {top5:.1f}% - Well distributed."

        return analysis

    def _analyze_pre_migration(self, pre_migration_metrics: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze pre-migration performance"""
        if not pre_migration_metrics:
            return {'available': False, 'analysis': 'No pre-migration data available'}

        time_on_curve = pre_migration_metrics.get('time_on_bonding_curve_hours', 0)
        buy_sell_ratio = pre_migration_metrics.get('buy_sell_ratio', 1)
        unique_wallets = pre_migration_metrics.get('unique_wallets_pre_migration', 0)
        volume = pre_migration_metrics.get('total_volume_pre_migration_sol', 0)

        analysis = ""
        if time_on_curve < 1:
            analysis += f"⚠️ Only {time_on_curve:.1f}h on bonding curve - Very fast migration. "
        elif time_on_curve < 6:
            analysis += f"Fast migration ({time_on_curve:.1f}h on curve). "
        elif time_on_curve > 48:
            analysis += f"✅ Slow steady growth ({time_on_curve:.1f}h on curve). "
        else:
            analysis += f"Normal migration speed ({time_on_curve:.1f}h on curve). "

        if buy_sell_ratio > 2:
            analysis += f"✅ Strong buy pressure (ratio: {buy_sell_ratio:.1f}). "
        elif buy_sell_ratio < 0.8:
            analysis += f"⚠️ Sell pressure dominates (ratio: {buy_sell_ratio:.1f}). "

        analysis += f"{unique_wallets} unique wallets, {volume:.1f} SOL volume."

        return {
            'available': True,
            'time_on_curve_hours': time_on_curve,
            'buy_sell_ratio': buy_sell_ratio,
            'unique_wallets': unique_wallets,
            'volume_sol': volume,
            'rating': 'GOOD' if buy_sell_ratio > 1.5 and time_on_curve > 6 else 'FAIR' if buy_sell_ratio > 1 else 'POOR',
            'analysis': analysis
        }

    def _analyze_wallet_quality(self, wallet_intelligence: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze wallet intelligence"""
        if not wallet_intelligence:
            return {'available': False, 'analysis': 'No wallet intelligence available'}

        whale_count = wallet_intelligence.get('whale_count', 0)
        whale_pct = wallet_intelligence.get('whale_total_percentage', 0)
        insider_risk = wallet_intelligence.get('insider_risk_score', 0)
        profitable_wallets = len(wallet_intelligence.get('highly_profitable_wallets', []))

        analysis = ""
        if insider_risk > 7:
            analysis += f"🚨 CRITICAL: Insider risk score {insider_risk}/10 - Likely insider trading. "
        elif insider_risk > 5:
            analysis += f"⚠️ WARNING: Insider risk score {insider_risk}/10 - Possible insider activity. "
        elif insider_risk > 3:
            analysis += f"⚠️ Moderate insider risk ({insider_risk}/10). "
        else:
            analysis += f"✅ Low insider risk ({insider_risk}/10). "

        analysis += f"{whale_count} whales control {whale_pct:.1f}%. "

        if profitable_wallets > 5:
            analysis += f"✅ {profitable_wallets} proven profitable wallets detected - Smart money present."
        elif profitable_wallets > 0:
            analysis += f"{profitable_wallets} profitable wallets detected."

        return {
            'available': True,
            'whale_count': whale_count,
            'whale_percentage': whale_pct,
            'insider_risk_score': insider_risk,
            'profitable_wallet_count': profitable_wallets,
            'rating': 'POOR' if insider_risk > 6 else 'FAIR' if insider_risk > 4 else 'GOOD' if insider_risk <= 2 and profitable_wallets > 3 else 'FAIR',
            'analysis': analysis
        }

    def _analyze_social_presence(
        self,
        twitter_analysis: Optional[Dict[str, Any]],
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze social media presence"""
        if not twitter_analysis or twitter_analysis.get('limited_data'):
            return {
                'available': False,
                'analysis': 'No Twitter account or limited data'
            }

        risk_score = twitter_analysis.get('risk_score', 5)
        followers = twitter_analysis.get('follower_analysis', {}).get('followers_count', 0)
        verified = twitter_analysis.get('account_info', {}).get('verified', False)
        age_days = twitter_analysis.get('age_analysis', {}).get('account_age_days', 0)

        analysis = ""
        if verified:
            analysis += "✅ Verified Twitter account. "

        if age_days < 7:
            analysis += f"🚨 Brand new account ({age_days} days) - Major red flag. "
        elif age_days < 30:
            analysis += f"⚠️ New account ({age_days} days). "
        else:
            analysis += f"✅ Established account ({age_days} days). "

        if followers > 10000:
            analysis += f"✅ Strong following ({followers:,} followers)."
        elif followers > 1000:
            analysis += f"Moderate following ({followers:,} followers)."
        else:
            analysis += f"⚠️ Small following ({followers:,} followers)."

        return {
            'available': True,
            'risk_score': risk_score,
            'followers': followers,
            'verified': verified,
            'account_age_days': age_days,
            'rating': 'EXCELLENT' if verified and followers > 10000 else 'GOOD' if followers > 5000 and age_days > 90 else 'FAIR' if followers > 1000 else 'POOR',
            'analysis': analysis
        }

    def _generate_risk_assessment(
        self,
        features: Dict[str, Any],
        claude_analysis: Optional[Dict[str, Any]],
        wallet_intelligence: Optional[Dict[str, Any]],
        twitter_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate comprehensive risk assessment"""

        risks = []

        # Liquidity risk
        liquidity = self._safe_get(features, 'initial_liquidity_sol', 0)
        if liquidity < 5:
            risks.append({
                'type': 'LIQUIDITY',
                'severity': 'CRITICAL',
                'description': f'Extremely low liquidity ({liquidity:.1f} SOL) - High rug risk'
            })
        elif liquidity < 10:
            risks.append({
                'type': 'LIQUIDITY',
                'severity': 'HIGH',
                'description': f'Low liquidity ({liquidity:.1f} SOL) - Moderate rug risk'
            })

        # Concentration risk
        top1 = self._safe_get(features, 'top1_holder_pct', 0)
        if top1 > 0.3:
            risks.append({
                'type': 'CONCENTRATION',
                'severity': 'CRITICAL',
                'description': f'Top holder controls {top1*100:.1f}% - Extreme dump risk'
            })
        elif top1 > 0.2:
            risks.append({
                'type': 'CONCENTRATION',
                'severity': 'HIGH',
                'description': f'Top holder controls {top1*100:.1f}% - High dump risk'
            })

        # Insider risk
        if wallet_intelligence:
            insider_risk = self._safe_get(wallet_intelligence, 'insider_risk_score', 0)
            if insider_risk > 6:
                risks.append({
                    'type': 'INSIDER',
                    'severity': 'CRITICAL',
                    'description': f'Insider risk score {insider_risk}/10 - Likely coordinated pump'
                })
            elif insider_risk > 4:
                risks.append({
                    'type': 'INSIDER',
                    'severity': 'MEDIUM',
                    'description': f'Insider risk score {insider_risk}/10 - Possible insider activity'
                })

        # Social risk
        if twitter_analysis and not twitter_analysis.get('limited_data'):
            twitter_risk = self._safe_get(twitter_analysis, 'risk_score', 5)
            if twitter_risk > 7:
                risks.append({
                    'type': 'SOCIAL',
                    'severity': 'HIGH',
                    'description': f'Suspicious Twitter account (risk {twitter_risk}/10) - Possible scam'
                })
            elif twitter_risk > 5:
                risks.append({
                    'type': 'SOCIAL',
                    'severity': 'MEDIUM',
                    'description': f'Twitter account concerns (risk {twitter_risk}/10)'
                })

        # Calculate overall risk score
        overall_risk = self._safe_get(claude_analysis, 'risk_score', 5) if claude_analysis else 5

        return {
            'overall_risk_score': overall_risk,
            'risk_level': 'HIGH' if overall_risk >= 7 else 'MEDIUM' if overall_risk >= 4 else 'LOW',
            'identified_risks': risks,
            'risk_count': len(risks),
            'critical_risks': len([r for r in risks if r['severity'] == 'CRITICAL'])
        }

    def _generate_opportunity_analysis(
        self,
        features: Dict[str, Any],
        prediction: Dict[str, Any],
        claude_analysis: Optional[Dict[str, Any]],
        pre_migration_metrics: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate opportunity analysis"""

        opportunities = []

        # Strong liquidity
        liquidity = self._safe_get(features, 'initial_liquidity_sol', 0)
        if liquidity > 50:
            opportunities.append({
                'type': 'LIQUIDITY',
                'strength': 'HIGH',
                'description': f'Excellent liquidity ({liquidity:.1f} SOL) supports large trades'
            })

        # Good holder distribution
        top1 = self._safe_get(features, 'top1_holder_pct', 0)
        if top1 < 0.1:
            opportunities.append({
                'type': 'DISTRIBUTION',
                'strength': 'HIGH',
                'description': f'Well distributed ownership (top holder {top1*100:.1f}%)'
            })

        # Strong pre-migration performance
        if pre_migration_metrics:
            buy_sell_ratio = self._safe_get(pre_migration_metrics, 'buy_sell_ratio', 1)
            if buy_sell_ratio > 2:
                opportunities.append({
                    'type': 'MOMENTUM',
                    'strength': 'MEDIUM',
                    'description': f'Strong buy pressure (ratio {buy_sell_ratio:.1f})'
                })

        # High predicted return
        predicted_return = self._safe_get(prediction, 'prediction', 0) * 100
        if predicted_return > 30:
            opportunities.append({
                'type': 'RETURN',
                'strength': 'HIGH',
                'description': f'High predicted return ({predicted_return:.1f}%)'
            })
        elif predicted_return > 15:
            opportunities.append({
                'type': 'RETURN',
                'strength': 'MEDIUM',
                'description': f'Moderate predicted return ({predicted_return:.1f}%)'
            })

        opportunity_score = self._safe_get(claude_analysis, 'opportunity_score', 5) if claude_analysis else 5

        return {
            'overall_opportunity_score': opportunity_score,
            'opportunity_level': 'HIGH' if opportunity_score >= 7 else 'MEDIUM' if opportunity_score >= 4 else 'LOW',
            'identified_opportunities': opportunities,
            'opportunity_count': len(opportunities),
            'predicted_return_24h': predicted_return
        }

    def _breakdown_signals(
        self,
        features: Dict[str, Any],
        prediction: Dict[str, Any],
        pre_migration_metrics: Optional[Dict[str, Any]],
        twitter_analysis: Optional[Dict[str, Any]],
        wallet_intelligence: Optional[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Break down all signals into categories"""

        bullish_signals = []
        bearish_signals = []
        neutral_signals = []

        # Analyze each signal
        # ... (this would be a long function analyzing all features)

        return {
            'bullish': bullish_signals,
            'bearish': bearish_signals,
            'neutral': neutral_signals
        }

    def _compile_supporting_evidence(
        self,
        prediction: Dict[str, Any],
        features: Dict[str, Any],
        claude_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compile supporting evidence for the decision"""

        top_features = prediction.get('top_features', [])[:5] if prediction else []

        return {
            'ml_prediction': {
                'return_24h': prediction.get('prediction', 0) * 100,
                'confidence': 'Based on historical patterns',
                'top_features': top_features
            },
            'claude_insights': claude_analysis.get('key_insights', []) if claude_analysis else [],
            'data_completeness': self._assess_data_completeness(features)
        }

    def _assess_data_completeness(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how complete the data is"""

        has_pre_migration = features.get('time_on_bonding_curve_hours', 0) > 0
        has_twitter = features.get('twitter_has_account', 0) == 1
        has_wallet_intel = features.get('holder_count', 0) > 0

        completeness = 0
        if has_pre_migration:
            completeness += 33
        if has_twitter:
            completeness += 33
        if has_wallet_intel:
            completeness += 34

        return {
            'completeness_percentage': completeness,
            'has_pre_migration_data': has_pre_migration,
            'has_twitter_data': has_twitter,
            'has_wallet_intelligence': has_wallet_intel
        }

    def _identify_red_flags(
        self,
        features: Dict[str, Any],
        wallet_intelligence: Optional[Dict[str, Any]],
        twitter_analysis: Optional[Dict[str, Any]],
        pre_migration_metrics: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Identify specific red flags"""

        red_flags = []

        # Check all major red flags
        liquidity = self._safe_get(features, 'initial_liquidity_sol', 0)
        if liquidity < 5:
            red_flags.append({
                'severity': 'CRITICAL',
                'flag': 'Dangerously low liquidity',
                'detail': f"Only {liquidity:.1f} SOL - Extreme rug risk"
            })

        top1 = self._safe_get(features, 'top1_holder_pct', 0)
        if top1 > 0.3:
            red_flags.append({
                'severity': 'CRITICAL',
                'flag': 'Extreme holder concentration',
                'detail': f"Top holder controls {top1*100:.1f}%"
            })

        if wallet_intelligence:
            insider_risk = self._safe_get(wallet_intelligence, 'insider_risk_score', 0)
            if insider_risk > 6:
                red_flags.append({
                    'severity': 'CRITICAL',
                    'flag': 'High insider risk detected',
                    'detail': f"Insider risk score {insider_risk}/10"
                })

        if twitter_analysis:
            twitter_risk = self._safe_get(twitter_analysis, 'risk_score', 0)
            if twitter_risk > 7:
                red_flags.append({
                    'severity': 'HIGH',
                    'flag': 'Suspicious Twitter account',
                    'detail': f"Twitter risk score {twitter_risk}/10"
                })

        if pre_migration_metrics:
            buy_sell_ratio = self._safe_get(pre_migration_metrics, 'buy_sell_ratio', 1)
            if buy_sell_ratio < 0.5:
                red_flags.append({
                    'severity': 'MEDIUM',
                    'flag': 'Heavy sell pressure pre-migration',
                    'detail': f"Buy/sell ratio only {buy_sell_ratio:.2f}"
                })

        return red_flags

    def _generate_comparative_context(
        self,
        features: Dict[str, Any],
        pre_migration_metrics: Optional[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Generate comparative context"""

        liquidity = features.get('initial_liquidity_sol', 0)
        holders = features.get('holder_count', 0)

        context = {}

        if liquidity > 50:
            context['liquidity'] = "Top 10% of migrated tokens"
        elif liquidity > 20:
            context['liquidity'] = "Above average liquidity"
        elif liquidity > 10:
            context['liquidity'] = "Average liquidity"
        else:
            context['liquidity'] = "Below average liquidity"

        if holders > 500:
            context['holders'] = "Strong holder base"
        elif holders > 200:
            context['holders'] = "Average holder base"
        else:
            context['holders'] = "Small holder base"

        return context

    def _generate_action_plan(
        self,
        claude_analysis: Optional[Dict[str, Any]],
        prediction: Dict[str, Any],
        features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate actionable plan"""

        if not claude_analysis:
            return {
                'immediate_actions': ['Wait for more data'],
                'monitoring_plan': 'Monitor for 24 hours',
                'exit_conditions': 'N/A'
            }

        recommendation = claude_analysis.get('recommendation', 'HOLD')

        if recommendation == 'BUY':
            immediate = [
                'Review position size recommendation',
                'Check current price and slippage',
                'Set stop loss orders',
                'Prepare exit strategy'
            ]
        elif recommendation == 'AVOID':
            immediate = [
                'Do not invest',
                'Monitor for changes',
                'Document red flags for learning'
            ]
        else:
            immediate = [
                'Continue monitoring',
                'Wait for clearer signals',
                'Re-evaluate in 1 hour'
            ]

        return {
            'immediate_actions': immediate,
            'monitoring_plan': claude_analysis.get('next_actions', []),
            'revaluation_time': '1 hour' if recommendation == 'HOLD' else '4 hours'
        }

    def save_report(self, report: Dict[str, Any], format: str = 'json') -> Path:
        """
        Save report to disk

        Args:
            report: Report dict
            format: Format to save (json, txt, html)

        Returns:
            Path to saved file
        """
        report_id = report['report_id']

        if format == 'json':
            filepath = self.output_dir / f"{report_id}.json"
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)

        elif format == 'txt':
            filepath = self.output_dir / f"{report_id}.txt"
            with open(filepath, 'w') as f:
                f.write(self._format_report_text(report))

        elif format == 'html':
            filepath = self.output_dir / f"{report_id}.html"
            with open(filepath, 'w') as f:
                f.write(self._format_report_html(report))

        logger.info(f"Report saved: {filepath}")
        return filepath

    def _format_report_text(self, report: Dict[str, Any]) -> str:
        """Format report as readable text"""

        lines = []
        lines.append("=" * 80)
        lines.append(f"INVESTMENT ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"")
        lines.append(f"Token: {report['name']} ({report['symbol']})")
        lines.append(f"Address: {report['token_address']}")
        lines.append(f"Migration Time: {report['migration_time']}")
        lines.append(f"Report Generated: {report['generated_at']}")
        lines.append(f"")

        # Executive Summary
        summary = report['executive_summary']
        lines.append("=" * 80)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("=" * 80)
        lines.append(summary['one_line_summary'])
        lines.append(f"")
        lines.append(f"Recommendation: {summary['recommendation']} ({summary['confidence']} confidence)")
        lines.append(f"Risk Score: {summary['risk_score']}/10")
        lines.append(f"Opportunity Score: {summary['opportunity_score']}/10")
        lines.append(f"Predicted 24h Return: {summary['predicted_return_24h']*100:.1f}%")
        lines.append(f"")

        # Decision Rationale
        decision = report['decision']
        lines.append("=" * 80)
        lines.append("DECISION RATIONALE")
        lines.append("=" * 80)
        lines.append(f"Action: {decision['action']}")
        lines.append(f"Position Size: {decision['position_size_recommendation']}")
        lines.append(f"Entry Strategy: {decision['entry_strategy']}")
        lines.append(f"Exit Strategy: {decision['exit_strategy']}")
        lines.append(f"")

        # Key Metrics
        metrics = report['key_metrics']
        lines.append("=" * 80)
        lines.append("KEY METRICS")
        lines.append("=" * 80)
        lines.append(f"Liquidity: {metrics['liquidity']['rating']} - {metrics['liquidity']['analysis']}")
        lines.append(f"Holder Distribution: {metrics['holder_distribution']['rating']} - {metrics['holder_distribution']['analysis']}")
        lines.append(f"")

        # Red Flags
        red_flags = report['red_flags']
        if red_flags:
            lines.append("=" * 80)
            lines.append("RED FLAGS")
            lines.append("=" * 80)
            for flag in red_flags:
                lines.append(f"[{flag['severity']}] {flag['flag']}: {flag['detail']}")
            lines.append(f"")

        # Action Plan
        action_plan = report['action_plan']
        lines.append("=" * 80)
        lines.append("ACTION PLAN")
        lines.append("=" * 80)
        for action in action_plan['immediate_actions']:
            lines.append(f"• {action}")
        lines.append(f"")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_report_html(self, report: Dict[str, Any]) -> str:
        """Format report as HTML (basic template)"""
        # Basic HTML template - could be enhanced
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Token Analysis Report - {report['symbol']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .metric {{ margin: 10px 0; }}
        .red-flag {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Investment Analysis Report</h1>
    <h2>{report['name']} ({report['symbol']})</h2>
    <div class="summary">
        <p><strong>Recommendation:</strong> {report['executive_summary']['recommendation']}</p>
        <p><strong>Confidence:</strong> {report['executive_summary']['confidence']}</p>
        <p>{report['executive_summary']['one_line_summary']}</p>
    </div>
    <!-- More HTML content -->
</body>
</html>
"""
