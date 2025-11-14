"""
Adaptive Risk Manager - Dynamic Stop-Loss & Take-Profit
Adjusts risk parameters based on confidence, category, volatility, and dev risk
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from loguru import logger
import numpy as np


class AdaptiveRiskManager:
    """
    Manages adaptive stop-loss and take-profit strategies
    Dynamically adjusts based on multiple factors
    """

    def __init__(self, base_config: Optional[Dict] = None):
        """
        Initialize adaptive risk manager

        Args:
            base_config: Base configuration for risk parameters
        """
        self.base_config = base_config or self._default_config()
        logger.info("Initialized Adaptive Risk Manager")

    def _default_config(self) -> Dict:
        """Default risk management configuration"""
        return {
            # Base stop-loss percentages
            'base_stop_loss': {
                'high_risk': 0.12,      # 12% for high risk tokens
                'medium_risk': 0.15,    # 15% for medium risk
                'low_risk': 0.20        # 20% for low risk
            },

            # Confidence multipliers (tighter SL for high confidence)
            'confidence_multipliers': {
                'HIGH': 0.8,      # 20% tighter
                'MEDIUM': 1.0,    # No change
                'LOW': 1.3        # 30% wider
            },

            # Category multipliers
            'category_multipliers': {
                'meme': 1.3,      # 30% wider (more volatile)
                'tech': 0.9,      # 10% tighter (less volatile)
                'viral': 1.2,     # 20% wider
                'gaming': 1.0,
                'defi': 0.9,
                'unknown': 1.0
            },

            # Dev risk adjustments (tighter SL for risky devs)
            'dev_risk_multipliers': {
                0: 1.0,     # LOW risk dev - normal SL
                1: 0.85,    # MEDIUM risk dev - 15% tighter
                2: 0.7      # HIGH risk dev - 30% tighter
            },

            # Multi-stage take-profit
            'take_profit_stages': [
                {'threshold': 0.50, 'percentage': 0.30, 'name': 'First Target'},   # +50%: sell 30%
                {'threshold': 1.00, 'percentage': 0.30, 'name': 'Second Target'},  # +100%: sell 30%
                {'threshold': 2.00, 'percentage': 0.20, 'name': 'Moon Target'}     # +200%: sell 20%
                # Remaining 20% uses trailing stop
            ],

            # Trailing stop configuration
            'trailing_stop': {
                'activation_profit': 0.30,  # Activate after +30% profit
                'trail_distance': {
                    'HIGH': 0.15,     # Trail 15% below peak (high confidence)
                    'MEDIUM': 0.20,   # Trail 20% below peak
                    'LOW': 0.25       # Trail 25% below peak
                },
                'update_frequency_minutes': 5  # Update every 5 minutes
            },

            # Time-based adjustments
            'time_decay': {
                'enabled': True,
                'hold_threshold_hours': 24,  # After 24h, tighten SL
                'decay_rate': 0.9            # Reduce SL by 10% per day
            }
        }

    def calculate_stop_loss(
        self,
        entry_price: float,
        confidence: str,
        risk_score: int,
        token_category: str = 'unknown',
        dev_risk_category: Optional[int] = None,
        volatility_multiplier: float = 1.0
    ) -> float:
        """
        Calculate adaptive stop-loss price

        Args:
            entry_price: Entry price
            confidence: HIGH/MEDIUM/LOW
            risk_score: Overall risk score (0-10)
            token_category: Token category (meme/tech/viral/etc)
            dev_risk_category: Dev risk (0=LOW, 1=MEDIUM, 2=HIGH)
            volatility_multiplier: Volatility adjustment (ATR-based)

        Returns:
            Stop-loss price
        """
        # Determine base SL based on risk score
        if risk_score >= 7:
            base_sl_pct = self.base_config['base_stop_loss']['high_risk']
        elif risk_score >= 4:
            base_sl_pct = self.base_config['base_stop_loss']['medium_risk']
        else:
            base_sl_pct = self.base_config['base_stop_loss']['low_risk']

        # Apply confidence multiplier
        conf_mult = self.base_config['confidence_multipliers'].get(confidence, 1.0)

        # Apply category multiplier
        cat_mult = self.base_config['category_multipliers'].get(token_category.lower(), 1.0)

        # Apply dev risk multiplier
        if dev_risk_category is not None:
            dev_mult = self.base_config['dev_risk_multipliers'].get(dev_risk_category, 1.0)
        else:
            dev_mult = 1.0

        # Calculate final SL percentage
        final_sl_pct = base_sl_pct * conf_mult * cat_mult * dev_mult * volatility_multiplier

        # Floor at 5%, ceiling at 30%
        final_sl_pct = max(0.05, min(0.30, final_sl_pct))

        # Calculate SL price
        sl_price = entry_price * (1 - final_sl_pct)

        logger.info(
            f"Calculated SL: {sl_price:.6f} ({final_sl_pct*100:.1f}% from entry) "
            f"[Base: {base_sl_pct*100:.0f}%, Conf: {conf_mult:.2f}x, "
            f"Cat: {cat_mult:.2f}x, Dev: {dev_mult:.2f}x, Vol: {volatility_multiplier:.2f}x]"
        )

        return sl_price

    def calculate_take_profit_stages(
        self,
        entry_price: float,
        position_size: float
    ) -> List[Dict[str, Any]]:
        """
        Calculate multi-stage take-profit targets

        Args:
            entry_price: Entry price
            position_size: Total position size

        Returns:
            List of TP stage dicts with price, size, percentage
        """
        stages = []

        for stage in self.base_config['take_profit_stages']:
            tp_price = entry_price * (1 + stage['threshold'])
            sell_amount = position_size * stage['percentage']

            stages.append({
                'name': stage['name'],
                'price': tp_price,
                'threshold_pct': stage['threshold'] * 100,
                'sell_percentage': stage['percentage'] * 100,
                'sell_amount': sell_amount,
                'executed': False
            })

        # Calculate remaining for trailing stop
        total_staged = sum(s['percentage'] for s in self.base_config['take_profit_stages'])
        trailing_pct = 1.0 - total_staged

        logger.info(f"Take-profit stages: {len(stages)} levels, {trailing_pct*100:.0f}% on trailing stop")

        return stages

    def should_activate_trailing_stop(
        self,
        entry_price: float,
        current_price: float
    ) -> bool:
        """
        Check if trailing stop should be activated

        Args:
            entry_price: Entry price
            current_price: Current price

        Returns:
            True if should activate trailing stop
        """
        profit_pct = (current_price - entry_price) / entry_price
        activation_threshold = self.base_config['trailing_stop']['activation_profit']

        should_activate = profit_pct >= activation_threshold

        if should_activate:
            logger.info(f"Trailing stop activated: {profit_pct*100:.1f}% profit (threshold: {activation_threshold*100:.0f}%)")

        return should_activate

    def calculate_trailing_stop(
        self,
        peak_price: float,
        confidence: str,
        current_price: float
    ) -> float:
        """
        Calculate trailing stop price

        Args:
            peak_price: Highest price achieved
            confidence: Trade confidence level
            current_price: Current price

        Returns:
            Trailing stop price
        """
        trail_distance = self.base_config['trailing_stop']['trail_distance'].get(confidence, 0.20)

        trailing_sl = peak_price * (1 - trail_distance)

        logger.debug(f"Trailing stop: {trailing_sl:.6f} ({trail_distance*100:.0f}% below peak {peak_price:.6f})")

        return trailing_sl

    def update_stop_loss_time_decay(
        self,
        current_sl: float,
        entry_price: float,
        entry_time: datetime,
        current_time: datetime
    ) -> float:
        """
        Apply time-based stop-loss tightening

        Args:
            current_sl: Current stop-loss price
            entry_price: Entry price
            entry_time: Entry timestamp
            current_time: Current timestamp

        Returns:
            Updated stop-loss price
        """
        if not self.base_config['time_decay']['enabled']:
            return current_sl

        # Calculate hours held
        hours_held = (current_time - entry_time).total_seconds() / 3600

        threshold_hours = self.base_config['time_decay']['hold_threshold_hours']

        if hours_held < threshold_hours:
            return current_sl  # No decay yet

        # Calculate decay periods (number of 24h periods past threshold)
        decay_periods = int((hours_held - threshold_hours) / 24)

        if decay_periods == 0:
            return current_sl

        # Apply decay
        decay_rate = self.base_config['time_decay']['decay_rate']
        decay_multiplier = decay_rate ** decay_periods

        # Current SL distance from entry
        current_sl_pct = 1 - (current_sl / entry_price)

        # Apply decay (tighten SL)
        new_sl_pct = current_sl_pct * decay_multiplier

        # Calculate new SL price
        new_sl = entry_price * (1 - new_sl_pct)

        # Only tighten, never loosen
        new_sl = max(new_sl, current_sl)

        if new_sl > current_sl:
            logger.info(f"Time decay: Tightened SL from {current_sl:.6f} to {new_sl:.6f} (held {hours_held:.1f}h)")

        return new_sl

    def should_execute_stage(
        self,
        stage: Dict[str, Any],
        current_price: float
    ) -> bool:
        """
        Check if TP stage should be executed

        Args:
            stage: TP stage dict
            current_price: Current price

        Returns:
            True if stage should execute
        """
        if stage['executed']:
            return False

        return current_price >= stage['price']

    def get_risk_summary(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit_stages: List[Dict],
        confidence: str,
        risk_score: int,
        dev_risk: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate risk/reward summary

        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            take_profit_stages: List of TP stages
            confidence: Confidence level
            risk_score: Overall risk score
            dev_risk: Dev risk category

        Returns:
            Risk summary dict
        """
        # Calculate risk
        risk_pct = (entry_price - stop_loss) / entry_price
        risk_amount_per_unit = entry_price - stop_loss

        # Calculate average reward (weighted by stage percentages)
        total_reward = 0
        for stage in take_profit_stages:
            stage_return = (stage['price'] - entry_price) / entry_price
            stage_weight = stage['sell_percentage'] / 100
            total_reward += stage_return * stage_weight

        # Risk/reward ratio
        if risk_pct > 0:
            risk_reward_ratio = total_reward / risk_pct
        else:
            risk_reward_ratio = 0

        summary = {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'risk_percentage': risk_pct * 100,
            'risk_per_unit': risk_amount_per_unit,

            'take_profit_stages': take_profit_stages,
            'expected_reward_percentage': total_reward * 100,

            'risk_reward_ratio': risk_reward_ratio,

            'confidence': confidence,
            'overall_risk_score': risk_score,
            'dev_risk_category': dev_risk,

            'assessment': self._assess_trade_quality(risk_reward_ratio, risk_score, dev_risk)
        }

        return summary

    def _assess_trade_quality(
        self,
        risk_reward_ratio: float,
        risk_score: int,
        dev_risk: Optional[int]
    ) -> str:
        """
        Assess overall trade quality

        Args:
            risk_reward_ratio: R:R ratio
            risk_score: Overall risk (0-10)
            dev_risk: Dev risk category

        Returns:
            Quality assessment string
        """
        # Start with R:R assessment
        if risk_reward_ratio >= 3.0:
            quality = "EXCELLENT"
        elif risk_reward_ratio >= 2.0:
            quality = "GOOD"
        elif risk_reward_ratio >= 1.5:
            quality = "FAIR"
        else:
            quality = "POOR"

        # Adjust for risk
        if risk_score >= 7:
            quality = "POOR"  # Override for high risk
        elif dev_risk == 2:  # HIGH dev risk
            quality = "POOR"  # Override for risky dev

        return quality


def test_adaptive_risk_manager():
    """Test the adaptive risk manager"""
    print("\nTesting Adaptive Risk Manager\n")

    manager = AdaptiveRiskManager()

    # Test case 1: High confidence, low risk tech token
    print("=" * 60)
    print("Test 1: HIGH confidence, LOW risk tech token")
    print("=" * 60)

    entry = 0.001234
    sl = manager.calculate_stop_loss(
        entry_price=entry,
        confidence='HIGH',
        risk_score=2,
        token_category='tech',
        dev_risk_category=0
    )

    tp_stages = manager.calculate_take_profit_stages(entry, position_size=100)

    summary = manager.get_risk_summary(
        entry_price=entry,
        stop_loss=sl,
        take_profit_stages=tp_stages,
        confidence='HIGH',
        risk_score=2,
        dev_risk=0
    )

    print(f"\nEntry: {entry:.6f}")
    print(f"Stop-Loss: {sl:.6f} (-{summary['risk_percentage']:.1f}%)")
    print(f"\nTake-Profit Stages:")
    for stage in tp_stages:
        print(f"  {stage['name']}: {stage['price']:.6f} (+{stage['threshold_pct']:.0f}%) - Sell {stage['sell_percentage']:.0f}%")
    print(f"\nRisk/Reward: {summary['risk_reward_ratio']:.2f}:1")
    print(f"Assessment: {summary['assessment']}")

    # Test case 2: LOW confidence, HIGH risk meme with risky dev
    print("\n" + "=" * 60)
    print("Test 2: LOW confidence, HIGH risk meme with risky dev")
    print("=" * 60)

    sl2 = manager.calculate_stop_loss(
        entry_price=entry,
        confidence='LOW',
        risk_score=9,
        token_category='meme',
        dev_risk_category=2  # HIGH risk dev
    )

    summary2 = manager.get_risk_summary(
        entry_price=entry,
        stop_loss=sl2,
        take_profit_stages=tp_stages,
        confidence='LOW',
        risk_score=9,
        dev_risk=2
    )

    print(f"\nEntry: {entry:.6f}")
    print(f"Stop-Loss: {sl2:.6f} (-{summary2['risk_percentage']:.1f}%)")
    print(f"Risk/Reward: {summary2['risk_reward_ratio']:.2f}:1")
    print(f"Assessment: {summary2['assessment']}")

    # Test trailing stop
    print("\n" + "=" * 60)
    print("Test 3: Trailing Stop Activation")
    print("=" * 60)

    peak_price = entry * 1.5  # +50% profit
    current_price = entry * 1.45

    should_trail = manager.should_activate_trailing_stop(entry, current_price)
    print(f"\nShould activate trailing stop: {should_trail}")

    if should_trail:
        trailing_sl = manager.calculate_trailing_stop(peak_price, 'HIGH', current_price)
        print(f"Trailing SL: {trailing_sl:.6f}")
        print(f"Current: {current_price:.6f}")
        print(f"Peak: {peak_price:.6f}")

    print("\nAll tests complete!\n")


if __name__ == "__main__":
    test_adaptive_risk_manager()
