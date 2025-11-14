"""
Parameter Tuner - Applies AI recommendations to strategy
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json
from loguru import logger


class ParameterTuner:
    """Applies and manages strategy parameter adjustments"""

    def __init__(self, parameters_file: str = "data/strategy_parameters.json"):
        """
        Initialize parameter tuner

        Args:
            parameters_file: Path to parameters file
        """
        self.parameters_file = Path(parameters_file)
        self.parameters_file.parent.mkdir(parents=True, exist_ok=True)

        # Current parameters
        self.parameters = self._load_parameters()

        # Parameter history (for rollback)
        self.history = []
        self.history_file = Path("data/parameter_history.json")

    def _load_parameters(self) -> Dict[str, Any]:
        """Load current parameters from file"""
        if not self.parameters_file.exists():
            # Default parameters
            return self._get_default_parameters()

        try:
            with open(self.parameters_file, 'r') as f:
                params = json.load(f)
            logger.info(f"Loaded strategy parameters from {self.parameters_file}")
            return params
        except Exception as e:
            logger.error(f"Error loading parameters: {e}, using defaults")
            return self._get_default_parameters()

    def _get_default_parameters(self) -> Dict[str, Any]:
        """Get default strategy parameters"""
        return {
            # Stop Loss settings
            'stop_loss': {
                'high_risk_pct': 0.15,      # 15% for risk 7-10
                'medium_risk_pct': 0.25,    # 25% for risk 4-6
                'low_risk_pct': 0.35,       # 35% for risk 0-3
                'tech_multiplier': 1.3,     # Tech tokens get wider stops
                'viral_multiplier': 0.8     # Viral memes get tighter stops
            },

            # Take Profit settings
            'take_profit': {
                'high_risk': {
                    'tp1_mult': 0.4,        # 40% of predicted return
                    'tp2_mult': 0.7,        # 70% of predicted return
                    'tp3_mult': 1.0,        # 100% of predicted return
                    'tp1_exit_pct': 0.50,   # Exit 50% at TP1
                    'tp2_exit_pct': 0.30,   # Exit 30% at TP2
                    'tp3_exit_pct': 0.20    # Exit 20% at TP3
                },
                'medium_risk': {
                    'tp1_mult': 0.5,
                    'tp2_mult': 1.0,
                    'tp3_mult': 1.5,
                    'tp1_exit_pct': 0.30,
                    'tp2_exit_pct': 0.40,
                    'tp3_exit_pct': 0.30
                },
                'low_risk': {
                    'tp1_mult': 1.0,
                    'tp2_mult': 1.5,
                    'tp3_mult': 2.0,
                    'tp1_exit_pct': 0.30,
                    'tp2_exit_pct': 0.40,
                    'tp3_exit_pct': 0.30
                }
            },

            # Entry strategy settings
            'entry_strategy': {
                'viral_meme_immediate_liquidity_threshold': 20,  # SOL
                'tech_wait_for_dip_liquidity_threshold': 10,     # SOL
                'wait_for_dip_max_hours': 6,
                'wait_for_dip_target_pct': 0.075  # 7.5% dip
            },

            # Position sizing
            'position_sizing': {
                'max_position_pct': 0.10,      # 10% max per trade
                'high_confidence_mult': 1.0,
                'medium_confidence_mult': 0.6,
                'low_confidence_mult': 0.3,
                'high_risk_reduction': 0.5     # Reduce by 50% for high risk
            },

            # Filtering rules
            'filters': {
                'min_confidence': None,        # None = accept all, or 'HIGH', 'MEDIUM'
                'max_risk_score': 10,          # 0-10, reject above this
                'min_liquidity_sol': 5,        # Minimum initial liquidity
                'enabled_token_types': ['tech', 'viral_meme', 'unknown']  # Which types to trade
            },

            # Metadata
            'last_updated': datetime.now().isoformat(),
            'version': 1
        }

    def _save_parameters(self):
        """Save parameters to file"""
        self.parameters['last_updated'] = datetime.now().isoformat()

        try:
            with open(self.parameters_file, 'w') as f:
                json.dump(self.parameters, f, indent=2)
            logger.info(f"Saved parameters to {self.parameters_file}")
        except Exception as e:
            logger.error(f"Error saving parameters: {e}")

    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameters"""
        return self.parameters.copy()

    def apply_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        auto_apply: bool = False,
        min_priority: str = 'medium'
    ) -> Dict[str, Any]:
        """
        Apply Claude's recommendations

        Args:
            recommendations: List of recommendations from Claude
            auto_apply: If True, apply without confirmation
            min_priority: Only apply recommendations with this priority or higher

        Returns:
            Summary of applied changes
        """
        if not recommendations:
            logger.info("No recommendations to apply")
            return {'applied': 0, 'skipped': 0, 'changes': []}

        # Filter by priority
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        min_priority_value = priority_order.get(min_priority, 2)

        filtered = [
            r for r in recommendations
            if priority_order.get(r.get('priority', 'low'), 1) >= min_priority_value
        ]

        logger.info(f"Applying {len(filtered)}/{len(recommendations)} recommendations (priority >= {min_priority})")

        # Save current state for rollback
        self._save_to_history("Before applying AI recommendations")

        applied = 0
        skipped = 0
        changes = []

        for rec in filtered:
            category = rec.get('category')
            parameter = rec.get('parameter')
            current_value = rec.get('current_value')
            recommended_value = rec.get('recommended_value')
            reasoning = rec.get('reasoning', '')

            logger.info(f"\nRecommendation: {category} - {parameter}")
            logger.info(f"  Current: {current_value}")
            logger.info(f"  Recommended: {recommended_value}")
            logger.info(f"  Reason: {reasoning}")

            # Apply based on category
            try:
                if self._apply_recommendation(rec):
                    applied += 1
                    changes.append({
                        'category': category,
                        'parameter': parameter,
                        'old_value': current_value,
                        'new_value': recommended_value,
                        'reasoning': reasoning
                    })
                    logger.info(f"  ✅ Applied")
                else:
                    skipped += 1
                    logger.info(f"  ⏭️  Skipped (could not apply)")

            except Exception as e:
                logger.error(f"  ❌ Error applying: {e}")
                skipped += 1

        # Save updated parameters
        self._save_parameters()

        summary = {
            'applied': applied,
            'skipped': skipped,
            'changes': changes,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"\n✅ Applied {applied} recommendations, skipped {skipped}")

        return summary

    def _apply_recommendation(self, rec: Dict[str, Any]) -> bool:
        """
        Apply a single recommendation

        Args:
            rec: Recommendation dict

        Returns:
            True if applied successfully
        """
        category = rec.get('category')
        parameter = rec.get('parameter')
        recommended_value = rec.get('recommended_value')

        # Parse the recommended value
        try:
            # Try to convert to appropriate type
            if isinstance(recommended_value, str):
                # Try float
                try:
                    recommended_value = float(recommended_value)
                except:
                    pass

            # Apply based on category
            if category == 'stop_loss':
                return self._apply_stop_loss_change(parameter, recommended_value)
            elif category == 'take_profit':
                return self._apply_take_profit_change(parameter, recommended_value)
            elif category == 'entry_strategy':
                return self._apply_entry_strategy_change(parameter, recommended_value)
            elif category == 'position_sizing':
                return self._apply_position_sizing_change(parameter, recommended_value)
            elif category == 'filtering':
                return self._apply_filtering_change(parameter, recommended_value)
            else:
                logger.warning(f"Unknown category: {category}")
                return False

        except Exception as e:
            logger.error(f"Error applying recommendation: {e}")
            return False

    def _apply_stop_loss_change(self, parameter: str, value: Any) -> bool:
        """Apply stop loss parameter change"""
        valid_params = {
            'high_risk_pct', 'medium_risk_pct', 'low_risk_pct',
            'tech_multiplier', 'viral_multiplier'
        }

        if parameter in valid_params:
            self.parameters['stop_loss'][parameter] = float(value)
            return True
        return False

    def _apply_take_profit_change(self, parameter: str, value: Any) -> bool:
        """Apply take profit parameter change"""
        # Parameter format: "medium_risk.tp1_mult" or similar
        if '.' in parameter:
            risk_level, param = parameter.split('.', 1)
            if risk_level in self.parameters['take_profit']:
                self.parameters['take_profit'][risk_level][param] = float(value)
                return True
        return False

    def _apply_entry_strategy_change(self, parameter: str, value: Any) -> bool:
        """Apply entry strategy parameter change"""
        valid_params = {
            'viral_meme_immediate_liquidity_threshold',
            'tech_wait_for_dip_liquidity_threshold',
            'wait_for_dip_max_hours',
            'wait_for_dip_target_pct'
        }

        if parameter in valid_params:
            self.parameters['entry_strategy'][parameter] = float(value)
            return True
        return False

    def _apply_position_sizing_change(self, parameter: str, value: Any) -> bool:
        """Apply position sizing parameter change"""
        valid_params = {
            'max_position_pct', 'high_confidence_mult',
            'medium_confidence_mult', 'low_confidence_mult',
            'high_risk_reduction'
        }

        if parameter in valid_params:
            self.parameters['position_sizing'][parameter] = float(value)
            return True
        return False

    def _apply_filtering_change(self, parameter: str, value: Any) -> bool:
        """Apply filtering rule change"""
        valid_params = {
            'min_confidence', 'max_risk_score',
            'min_liquidity_sol', 'enabled_token_types'
        }

        if parameter in valid_params:
            self.parameters['filters'][parameter] = value
            return True
        return False

    def _save_to_history(self, reason: str):
        """Save current parameters to history"""
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'parameters': self.parameters.copy()
        }

        self.history.append(history_entry)

        # Save to file
        try:
            # Load existing history
            existing_history = []
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    existing_history = json.load(f)

            # Append new entry
            existing_history.append(history_entry)

            # Keep only last 50 entries
            if len(existing_history) > 50:
                existing_history = existing_history[-50:]

            # Save
            with open(self.history_file, 'w') as f:
                json.dump(existing_history, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving parameter history: {e}")

    def rollback_to_previous(self) -> bool:
        """
        Rollback to previous parameters

        Returns:
            True if rollback successful
        """
        try:
            # Load history
            if not self.history_file.exists():
                logger.error("No parameter history available for rollback")
                return False

            with open(self.history_file, 'r') as f:
                history = json.load(f)

            if len(history) < 2:
                logger.error("Need at least 2 history entries to rollback")
                return False

            # Get previous parameters (second to last)
            previous = history[-2]
            self.parameters = previous['parameters']

            # Save rolled back parameters
            self._save_parameters()

            logger.info(f"✅ Rolled back to parameters from {previous['timestamp']}")
            logger.info(f"   Reason: {previous['reason']}")

            return True

        except Exception as e:
            logger.error(f"Error rolling back parameters: {e}")
            return False

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get parameter change history

        Args:
            limit: Number of history entries to return

        Returns:
            List of history entries
        """
        try:
            if not self.history_file.exists():
                return []

            with open(self.history_file, 'r') as f:
                history = json.load(f)

            return history[-limit:]

        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []
