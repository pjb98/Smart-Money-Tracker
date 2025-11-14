# Mode Management System

Complete guide to the trading mode system, including observation, paper trading, backtesting, and live trading.

## Overview

The mode management system provides safety controls and operational modes for the Pumpfun agent. It ensures you never accidentally trade with real money and allows you to progressively test your strategy.

## Available Modes

### ⚫ OFF Mode
**System is completely disabled**

- ❌ No analysis
- ❌ No trading
- ❌ No monitoring

**Use when:**
- Taking a break
- Updating configuration
- System maintenance

### 👁️ OBSERVATION Mode
**Watch and analyze, but don't trade**

- ✅ Real-time migration detection
- ✅ AI analysis and recommendations
- ❌ No trading (paper or live)

**Use when:**
- Learning how the system works
- Reviewing AI recommendations
- Collecting data for later backtesting

### 📄 PAPER_TRADING Mode
**Simulate trades with virtual capital**

- ✅ Real-time migration detection
- ✅ AI analysis and recommendations
- ✅ Simulated trading with SL/TP
- ✅ Trading journal
- ❌ No real money

**Use when:**
- Testing your strategy risk-free
- Optimizing entry/exit logic
- Building track record before going live

### 🎓 TRAINING Mode
**Backtest on historical data**

- ✅ Analysis of past migrations
- ✅ Strategy evaluation
- ❌ No trading simulation
- ❌ No real-time monitoring

**Use when:**
- Testing strategy on historical data
- Evaluating AI performance
- Learning from past migrations

### 🎓📄 TRAINING_PAPER Mode
**Backtest + simulate paper trades**

- ✅ Analysis of past migrations
- ✅ Simulated trading on historical data
- ✅ Trading journal
- ❌ No real-time monitoring

**Use when:**
- Backtesting complete trading strategy
- Evaluating SL/TP logic
- Building historical performance metrics

### 🔴 LIVE Mode (⚠️ Real Money)
**REAL TRADING with REAL money**

- ✅ Real-time migration detection
- ✅ AI analysis
- ✅ Automatic trade execution
- ⚠️ USES REAL MONEY

**Use when:**
- You have tested extensively in paper trading
- You understand all risks
- You are ready to trade with real capital

**Safety Requirements:**
- Requires explicit confirmation
- Cannot switch directly from TRAINING modes
- Daily trade limits enforced
- Emergency stop available

## Control Panel Commands

### View Status
```bash
# Show current mode and system status
python control_panel.py --status
```

**Output:**
```
TRADING SYSTEM STATUS
======================================================================
🟢 System: ENABLED
📄 Mode: PAPER_TRADING
   Simulate trades with virtual capital

📊 Trading Status:
   ✅ Trading: ENABLED
   ✅ Analysis: ENABLED

📈 Statistics:
   Trades Today: 5/50
   Last Trade: 2025-01-10T14:32:15

🛡️  Safety:
   🔒 Live Trading: Requires confirmation
   💰 Max Position: $10,000
   🚨 Emergency Stop: ENABLED
======================================================================
```

### Enable/Disable System
```bash
# Enable system (activates auto-start mode)
python control_panel.py --enable

# Disable system (stops all activity)
python control_panel.py --disable
```

### Switch Modes
```bash
# Switch to observation mode
python control_panel.py --mode observation

# Switch to paper trading mode
python control_panel.py --mode paper_trading

# Switch to training mode
python control_panel.py --mode training

# Switch to training + paper mode
python control_panel.py --mode training_paper
```

### List Available Modes
```bash
python control_panel.py --list-modes
```

### Live Trading Confirmation (⚠️)
```bash
# Step 1: Confirm you understand the risks
python control_panel.py --confirm-live

# Step 2: Switch to live mode
python control_panel.py --mode live
```

**Confirmation process:**
```
⚠️  LIVE TRADING CONFIRMATION ⚠️
======================================================================
You are about to enable REAL trading with REAL money.

⚠️  RISKS:
  - You can LOSE money
  - Trades execute automatically
  - No undo button
  - Market volatility can cause losses
  - Smart contracts can have bugs

✅ BEFORE ENABLING:
  - Test thoroughly in paper trading mode
  - Understand all risks
  - Start with small position sizes
  - Set appropriate stop losses
  - Monitor actively

Type 'CONFIRM_LIVE' to enable live trading (or anything else to cancel):
```

### Emergency Stop
```bash
python control_panel.py --emergency-stop
```

Immediately:
- Disables system
- Switches to OFF mode
- Stops all monitoring and trading
- Logs reason to mode history

## Running Monitors

### Real-time Observation/Paper Trading
```bash
# Start real-time monitor (uses current mode)
python monitor_realtime.py

# OR: Start paper trading monitor
python paper_trade_monitor.py --capital 10000
```

**Behavior based on mode:**
- **OFF**: Nothing happens (system disabled)
- **OBSERVATION**: Analyzes migrations, no trading
- **PAPER_TRADING**: Analyzes + simulates trades
- **TRAINING**: Not applicable (use backtest_trainer.py)
- **LIVE**: Analyzes + executes real trades

### Backtesting (Training Modes)
```bash
# Backtest last 7 days (analysis only)
python backtest_trainer.py --days 7

# Backtest with paper trading simulation
python backtest_trainer.py --days 7 --paper-trading

# Backtest specific date range
python backtest_trainer.py --start-date 2025-01-01 --end-date 2025-01-10

# Backtest with custom capital
python backtest_trainer.py --days 30 --paper-trading --capital 50000
```

**Automatically switches to:**
- `TRAINING` mode (without --paper-trading)
- `TRAINING_PAPER` mode (with --paper-trading)

## Recommended Workflow

### Phase 1: Learning (Days 1-3)
```bash
# Set to observation mode
python control_panel.py --mode observation
python control_panel.py --enable

# Run real-time monitor
python monitor_realtime.py
```

**Goals:**
- Understand how migrations work
- See AI recommendations
- Learn token patterns
- No trading pressure

### Phase 2: Paper Trading (Weeks 1-4)
```bash
# Switch to paper trading
python control_panel.py --mode paper_trading

# Run paper trading monitor
python paper_trade_monitor.py --capital 10000
```

**Goals:**
- Test strategy with virtual capital
- Optimize SL/TP levels
- Build 30-50 trades
- Achieve 55%+ win rate

**Review daily:**
```bash
python view_trading_journal.py --summary
```

**Analyze weekly:**
```bash
python view_trading_journal.py --analyze
```

### Phase 3: Backtesting (Week 2-4)
```bash
# Run backtest on collected data
python backtest_trainer.py --days 30 --paper-trading
```

**Goals:**
- Validate strategy on historical data
- Identify patterns
- Compare backtest vs. live paper trading results

### Phase 4: Refinement (Ongoing)
- Adjust SL/TP based on results
- Filter by confidence/risk levels
- Optimize position sizing
- Improve token classification

### Phase 5: Live Trading (After 50+ successful paper trades)
```bash
# Confirm live trading
python control_panel.py --confirm-live

# Switch to live mode
python control_panel.py --mode live

# Start with small capital
python monitor_realtime.py
```

**Before going live:**
- ✅ 50+ paper trades completed
- ✅ Win rate > 55%
- ✅ Profit factor > 1.5
- ✅ Understand why trades win/lose
- ✅ Tested on historical data
- ✅ Comfortable with risk
- ✅ Start with 10-20% of intended capital

## Safety Features

### 1. Live Trading Confirmation
- LIVE mode requires explicit confirmation
- Cannot accidentally enable real trading
- Must type "CONFIRM_LIVE" to proceed

### 2. Mode Transition Validation
- Cannot switch directly from TRAINING to LIVE
- Must use paper trading first
- Validates safe transitions

### 3. Daily Trade Limits
- Default: 50 trades per day
- Prevents runaway trading
- Resets at midnight

### 4. Max Position Size
- Default: $10,000 per position
- Protects against oversized trades
- Configurable in settings

### 5. Emergency Stop
- Immediately disables everything
- Accessible via control panel
- Logs reason for audit trail

### 6. Persistent Settings
- Mode and settings saved to disk
- Survives restarts
- Settings file: `data/trading_settings.json`

## Settings File

Location: `data/trading_settings.json`

```json
{
  "current_mode": "paper_trading",
  "is_enabled": true,
  "auto_start_mode": "observation",
  "safety_settings": {
    "require_live_confirmation": true,
    "max_daily_trades": 50,
    "max_position_size_usd": 10000,
    "emergency_stop_enabled": true
  },
  "trades_today": 5,
  "last_trade_time": "2025-01-10T14:32:15",
  "mode_history": [
    {
      "from": "off",
      "to": "observation",
      "timestamp": "2025-01-10T10:00:00",
      "forced": false
    },
    {
      "from": "observation",
      "to": "paper_trading",
      "timestamp": "2025-01-10T12:00:00",
      "forced": false
    }
  ]
}
```

## Mode History Tracking

Every mode change is logged:
- From mode
- To mode
- Timestamp
- Whether it was forced
- Reason (for emergency stops)

**View history:**
```bash
cat data/trading_settings.json | grep -A 10 mode_history
```

## Troubleshooting

### Monitor not processing migrations
**Check if system is enabled:**
```bash
python control_panel.py --status
```

**If disabled, enable it:**
```bash
python control_panel.py --enable
```

### System enabled but not trading
**Check current mode:**
- OFF: No activity
- OBSERVATION: Analysis only, no trading
- PAPER_TRADING: Trading enabled
- TRAINING: Use backtest_trainer.py instead
- LIVE: Requires confirmation

### Cannot switch to LIVE mode
**Error: "Live trading requires confirmation"**

**Solution:**
```bash
python control_panel.py --confirm-live
python control_panel.py --mode live
```

### Accidentally enabled live trading
**Use emergency stop:**
```bash
python control_panel.py --emergency-stop
```

## Integration with Existing Tools

### Paper Trading Monitor
- Automatically checks mode before trading
- Displays mode status on startup
- Respects system enable/disable

### Realtime Monitor
- Automatically checks mode before analysis
- Displays mode status on startup
- Respects system enable/disable

### Trading Journal
- Works with all trading modes
- Tracks paper trades from PAPER_TRADING mode
- Tracks backtest trades from TRAINING_PAPER mode

## Advanced Usage

### Programmatic Mode Control

```python
from src.utils.trading_mode import TradingMode, get_mode_manager

# Get mode manager
mode_manager = get_mode_manager()

# Check current mode
current_mode = mode_manager.get_mode()
print(f"Current mode: {current_mode.value}")

# Check if system is active
if mode_manager.is_active():
    print("System is active")

# Check permissions
can_trade = mode_manager.can_trade()
can_analyze = mode_manager.can_analyze()

# Change mode
mode_manager.set_mode(TradingMode.PAPER_TRADING)

# Enable/disable
mode_manager.enable()
mode_manager.disable()

# Emergency stop
mode_manager.emergency_stop("Testing emergency stop")

# Get status
status = mode_manager.get_status()
```

### Custom Safety Settings

Edit `data/trading_settings.json`:

```json
{
  "safety_settings": {
    "max_daily_trades": 100,        // Increase daily limit
    "max_position_size_usd": 5000   // Decrease max position
  }
}
```

## Best Practices

### 1. Always Start with Observation
Learn the system before trading

### 2. Paper Trade for Weeks
Build confidence and track record

### 3. Use Emergency Stop When Needed
Don't hesitate to stop if something seems wrong

### 4. Review Mode History
Understand your mode changes over time

### 5. Respect Safety Guardrails
They exist to protect you

### 6. Start Small in Live Mode
Use 10-20% of intended capital at first

### 7. Monitor Actively
Especially in LIVE mode

### 8. Keep Backups
`data/trading_settings.json` is important

## Files

- `src/utils/trading_mode.py` - Core mode management
- `control_panel.py` - CLI for mode control
- `backtest_trainer.py` - Training mode implementation
- `data/trading_settings.json` - Persistent settings
- `data/backtest_results.json` - Backtest results

## Summary

The mode system provides:
- ✅ Safety controls for live trading
- ✅ Progressive testing workflow
- ✅ Flexible operation modes
- ✅ Persistent state management
- ✅ Emergency controls
- ✅ Audit trail

**Remember: Paper trading is free. Real trading has consequences. Take your time!** 🚀
