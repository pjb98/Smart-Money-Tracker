"""
Trading Mode Management System
Controls operation modes: Observation, Paper Trading, Training, Live Trading
"""
from enum import Enum
from pathlib import Path
import json
from datetime import datetime
from loguru import logger
from typing import Optional, Dict, Any


class TradingMode(Enum):
    """Available trading modes"""
    OFF = "off"  # System is off, not processing
    OBSERVATION = "observation"  # Watch and analyze but don't trade
    PAPER_TRADING = "paper_trading"  # Simulate trades with virtual capital
    TRAINING = "training"  # Backtest on historical data
    TRAINING_PAPER = "training_paper"  # Train + simulate paper trades
    LIVE = "live"  # REAL TRADING (requires confirmation)


class TradingModeManager:
    """
    Manages trading mode state and transitions
    Provides safety checks and mode persistence
    """

    def __init__(self, settings_file: str = "data/trading_settings.json"):
        """
        Initialize trading mode manager

        Args:
            settings_file: Path to settings file
        """
        self.settings_file = Path(settings_file)
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Load current mode
        self.current_mode = TradingMode.OFF
        self.is_enabled = False
        self.auto_start_mode = TradingMode.OBSERVATION

        # Safety settings
        self.require_live_confirmation = True
        self.max_daily_trades = 50
        self.max_position_size_usd = 10000
        self.emergency_stop_enabled = True

        # Statistics
        self.trades_today = 0
        self.last_trade_time = None
        self.mode_history = []

        self._load_settings()

    def _load_settings(self):
        """Load settings from disk"""
        if not self.settings_file.exists():
            logger.info("No settings file found, using defaults")
            self._save_settings()
            return

        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)

            # Load mode
            mode_str = data.get('current_mode', 'off')
            self.current_mode = TradingMode(mode_str)

            self.is_enabled = data.get('is_enabled', False)

            auto_start = data.get('auto_start_mode', 'observation')
            self.auto_start_mode = TradingMode(auto_start)

            # Load safety settings
            safety = data.get('safety_settings', {})
            self.require_live_confirmation = safety.get('require_live_confirmation', True)
            self.max_daily_trades = safety.get('max_daily_trades', 50)
            self.max_position_size_usd = safety.get('max_position_size_usd', 10000)
            self.emergency_stop_enabled = safety.get('emergency_stop_enabled', True)

            # Load stats
            self.trades_today = data.get('trades_today', 0)
            last_trade = data.get('last_trade_time')
            if last_trade:
                self.last_trade_time = datetime.fromisoformat(last_trade)

            self.mode_history = data.get('mode_history', [])

            logger.info(f"Loaded settings: Mode={self.current_mode.value}, Enabled={self.is_enabled}")

        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._save_settings()

    def _save_settings(self):
        """Save settings to disk"""
        data = {
            'current_mode': self.current_mode.value,
            'is_enabled': self.is_enabled,
            'auto_start_mode': self.auto_start_mode.value,
            'safety_settings': {
                'require_live_confirmation': self.require_live_confirmation,
                'max_daily_trades': self.max_daily_trades,
                'max_position_size_usd': self.max_position_size_usd,
                'emergency_stop_enabled': self.emergency_stop_enabled
            },
            'trades_today': self.trades_today,
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
            'mode_history': self.mode_history,
            'last_updated': datetime.now().isoformat()
        }

        with open(self.settings_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_mode(self) -> TradingMode:
        """Get current trading mode"""
        return self.current_mode

    def is_active(self) -> bool:
        """Check if system is active (enabled and not OFF)"""
        return self.is_enabled and self.current_mode != TradingMode.OFF

    def can_trade(self) -> bool:
        """Check if trading is allowed"""
        if not self.is_active():
            return False

        # Only these modes can trade
        if self.current_mode not in [TradingMode.PAPER_TRADING, TradingMode.TRAINING_PAPER, TradingMode.LIVE]:
            return False

        # Check daily trade limit
        if self.trades_today >= self.max_daily_trades:
            logger.warning(f"Daily trade limit reached: {self.trades_today}/{self.max_daily_trades}")
            return False

        return True

    def can_analyze(self) -> bool:
        """Check if analysis is allowed"""
        if not self.is_active():
            return False

        # All modes except OFF can analyze
        return self.current_mode != TradingMode.OFF

    def set_mode(self, new_mode: TradingMode, force: bool = False) -> bool:
        """
        Set trading mode with safety checks

        Args:
            new_mode: New mode to set
            force: Force mode change (skip confirmation)

        Returns:
            True if mode was changed successfully
        """
        # Safety check for LIVE mode
        if new_mode == TradingMode.LIVE and not force:
            if self.require_live_confirmation:
                logger.error("⚠️  LIVE TRADING MODE REQUIRES CONFIRMATION")
                logger.error("   Use: mode_manager.confirm_live_trading() first")
                logger.error("   Or: mode_manager.set_mode(TradingMode.LIVE, force=True)")
                return False

        old_mode = self.current_mode
        self.current_mode = new_mode

        # Add to history
        self.mode_history.append({
            'from': old_mode.value,
            'to': new_mode.value,
            'timestamp': datetime.now().isoformat(),
            'forced': force
        })

        # Keep only last 100 mode changes
        if len(self.mode_history) > 100:
            self.mode_history = self.mode_history[-100:]

        self._save_settings()

        logger.info(f"🔄 Mode changed: {old_mode.value} → {new_mode.value}")
        return True

    def enable(self):
        """Enable the system"""
        if not self.is_enabled:
            self.is_enabled = True
            logger.info(f"✅ System ENABLED (Mode: {self.current_mode.value})")

            # If currently OFF, switch to auto-start mode
            if self.current_mode == TradingMode.OFF:
                self.set_mode(self.auto_start_mode)

            self._save_settings()

    def disable(self):
        """Disable the system"""
        if self.is_enabled:
            self.is_enabled = False
            logger.warning(f"⏸️  System DISABLED (Mode: {self.current_mode.value})")
            self._save_settings()

    def emergency_stop(self, reason: str = "Emergency stop triggered"):
        """Emergency stop - immediately disable everything"""
        logger.error("🚨 EMERGENCY STOP 🚨")
        logger.error(f"   Reason: {reason}")

        self.is_enabled = False
        old_mode = self.current_mode
        self.current_mode = TradingMode.OFF

        self.mode_history.append({
            'from': old_mode.value,
            'to': 'off',
            'timestamp': datetime.now().isoformat(),
            'reason': 'EMERGENCY_STOP',
            'details': reason
        })

        self._save_settings()

        logger.error("   System is now DISABLED and OFF")

    def confirm_live_trading(self, confirmation_code: str = "CONFIRM_LIVE") -> bool:
        """
        Confirm intention to use live trading mode

        Args:
            confirmation_code: Required confirmation code

        Returns:
            True if confirmed successfully
        """
        if confirmation_code != "CONFIRM_LIVE":
            logger.error("❌ Invalid confirmation code for live trading")
            return False

        logger.warning("⚠️  LIVE TRADING CONFIRMED")
        logger.warning("   You are about to enable REAL trading with REAL money")
        logger.warning("   Make sure you understand the risks")

        # Temporarily disable requirement
        self.require_live_confirmation = False
        self._save_settings()

        return True

    def record_trade(self):
        """Record that a trade was executed"""
        self.trades_today += 1
        self.last_trade_time = datetime.now()
        self._save_settings()

    def reset_daily_stats(self):
        """Reset daily statistics (call at midnight)"""
        self.trades_today = 0
        self._save_settings()
        logger.info("Daily stats reset")

    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'mode': self.current_mode.value,
            'enabled': self.is_enabled,
            'active': self.is_active(),
            'can_trade': self.can_trade(),
            'can_analyze': self.can_analyze(),
            'trades_today': self.trades_today,
            'max_daily_trades': self.max_daily_trades,
            'last_trade': self.last_trade_time.isoformat() if self.last_trade_time else None,
            'safety': {
                'require_live_confirmation': self.require_live_confirmation,
                'max_position_size_usd': self.max_position_size_usd,
                'emergency_stop_enabled': self.emergency_stop_enabled
            }
        }

    def get_mode_description(self, mode: Optional[TradingMode] = None) -> str:
        """Get human-readable mode description"""
        if mode is None:
            mode = self.current_mode

        descriptions = {
            TradingMode.OFF: "System is OFF - Not processing any events",
            TradingMode.OBSERVATION: "Watch and analyze tokens but don't trade",
            TradingMode.PAPER_TRADING: "Simulate trades with virtual capital",
            TradingMode.TRAINING: "Backtest on historical data only",
            TradingMode.TRAINING_PAPER: "Backtest + simulate paper trades",
            TradingMode.LIVE: "⚠️  REAL TRADING with REAL money ⚠️"
        }

        return descriptions.get(mode, "Unknown mode")

    def display_status(self):
        """Display current status in console"""
        status = self.get_status()

        print("\n" + "="*70)
        print("TRADING SYSTEM STATUS")
        print("="*70)

        # Enabled status
        if status['enabled']:
            print("🟢 System: ENABLED")
        else:
            print("🔴 System: DISABLED")

        # Mode
        mode_emoji = {
            'off': '⚫',
            'observation': '👁️ ',
            'paper_trading': '📄',
            'training': '🎓',
            'training_paper': '🎓📄',
            'live': '🔴'
        }
        emoji = mode_emoji.get(status['mode'], '❓')

        print(f"{emoji} Mode: {status['mode'].upper()}")
        print(f"   {self.get_mode_description()}")

        # Trading status
        print(f"\n📊 Trading Status:")
        if status['can_trade']:
            print(f"   ✅ Trading: ENABLED")
        else:
            print(f"   ❌ Trading: DISABLED")

        if status['can_analyze']:
            print(f"   ✅ Analysis: ENABLED")
        else:
            print(f"   ❌ Analysis: DISABLED")

        # Stats
        print(f"\n📈 Statistics:")
        print(f"   Trades Today: {status['trades_today']}/{status['max_daily_trades']}")
        if status['last_trade']:
            print(f"   Last Trade: {status['last_trade']}")

        # Safety
        print(f"\n🛡️  Safety:")
        if status['safety']['require_live_confirmation']:
            print(f"   🔒 Live Trading: Requires confirmation")
        print(f"   💰 Max Position: ${status['safety']['max_position_size_usd']:,}")
        if status['safety']['emergency_stop_enabled']:
            print(f"   🚨 Emergency Stop: ENABLED")

        print("="*70)

    def validate_mode_transition(self, from_mode: TradingMode, to_mode: TradingMode) -> tuple[bool, str]:
        """
        Validate if mode transition is safe

        Args:
            from_mode: Current mode
            to_mode: Desired mode

        Returns:
            (is_valid, reason)
        """
        # Can always turn OFF
        if to_mode == TradingMode.OFF:
            return True, "OK"

        # Can't go to LIVE without confirmation
        if to_mode == TradingMode.LIVE and self.require_live_confirmation:
            return False, "Live trading requires confirmation"

        # Can't go from TRAINING to LIVE directly
        if from_mode in [TradingMode.TRAINING, TradingMode.TRAINING_PAPER] and to_mode == TradingMode.LIVE:
            return False, "Cannot switch directly from training to live trading. Use paper trading first."

        # All other transitions are OK
        return True, "OK"


# Global instance
_mode_manager = None


def get_mode_manager() -> TradingModeManager:
    """Get global mode manager instance"""
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = TradingModeManager()
    return _mode_manager
