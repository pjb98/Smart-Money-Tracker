# AI-Powered Strategy Optimization

## Overview

The AI optimization system uses Claude AI to continuously analyze your trading results and automatically improve your strategy. Instead of manually adjusting parameters, Claude identifies patterns and suggests optimizations based on real performance data.

## How It Works

### 1. **Continuous Learning Loop**
```
Trade → Analyze Results → Claude Identifies Patterns → Adjust Parameters → Trade Better
```

Every N trades (default: 10), the system:
1. Analyzes all completed trades
2. Sends performance data to Claude
3. Claude identifies what's working and what's not
4. Claude suggests specific parameter adjustments
5. Parameters are updated automatically (or with approval)
6. Next trades use improved settings

### 2. **What Claude Analyzes**

**Performance Metrics:**
- Win rate by token type, entry strategy, confidence level
- Average P&L by category
- Profit factor
- Best/worst trades

**Pattern Detection:**
- "Tech tokens with wait_for_dip have 80% win rate"
- "Viral memes hitting stop loss 65% of time"
- "HIGH confidence trades outperforming by 2x"

**Root Cause Analysis:**
- WHY are certain patterns winning/losing?
- Are stop losses too tight/loose?
- Are take profit targets realistic?
- Is entry timing optimal?

**Specific Recommendations:**
- "Increase tech token SL from 25% to 32%"
- "Lower viral meme TP1 from 25% to 15%"
- "Only trade HIGH confidence tokens"
- "Use wait_for_dip for tokens with <10 SOL liquidity"

## Quick Start

### Option 1: Manual Optimization (Run on demand)

```bash
# After 10+ trades, run optimization
python strategy_optimizer.py --run-once

# Claude will analyze and suggest improvements
# You'll be asked to approve changes
```

### Option 2: Continuous Auto-Optimization

```bash
# Start continuous optimizer (runs in background)
python strategy_optimizer.py --monitor --auto-apply

# Optimizes every 10 trades automatically
# No approval needed
```

### Option 3: Integrated with Paper Trading

```bash
# Paper trading monitor with AI optimization enabled
python paper_trade_monitor.py

# After every 10 trades, you'll see:
# "🤖 10 trades completed - AI optimization recommended!"
# Then run: python strategy_optimizer.py --run-once
```

## Commands

### Run Optimization

```bash
# Run once
python strategy_optimizer.py --run-once

# Force optimization (even with <10 trades)
python strategy_optimizer.py --run-once --force

# Optimize every 5 trades instead of 10
python strategy_optimizer.py --run-once --every 5
```

### Continuous Monitoring

```bash
# Auto-optimize in background
python strategy_optimizer.py --monitor --auto-apply

# Monitor but ask for approval
python strategy_optimizer.py --monitor

# Check every 5 minutes (default: 5 min)
python strategy_optimizer.py --monitor --check-interval 300
```

### Priority Control

```bash
# Only apply HIGH priority changes
python strategy_optimizer.py --run-once --min-priority high

# Apply medium and high (default)
python strategy_optimizer.py --run-once --min-priority medium

# Apply all recommendations
python strategy_optimizer.py --run-once --min-priority low
```

### View History

```bash
# View past optimizations
python strategy_optimizer.py --view-history

# Rollback to previous parameters
python strategy_optimizer.py --rollback
```

## Example Output

### Analysis Phase

```
🤖 AI STRATEGY OPTIMIZATION
======================================================================
Total trades: 30
New trades since last optimization: 10

🔍 Analyzing trading performance with Claude AI...

📊 CLAUDE'S ANALYSIS
======================================================================

Overall: Performance is mixed. Tech tokens showing strong results (75% win rate)
but viral memes underperforming (40% win rate). Stop losses on memes too loose.

🔍 PATTERNS IDENTIFIED (5)

🔴 VIRAL_MEME tokens with immediate entry losing frequently
   Category: entry_strategy
   Metric: win_rate = 0.40
   Significance: HIGH

🟡 TECH tokens with wait_for_dip outperforming
   Category: entry_strategy
   Metric: win_rate = 0.75
   Significance: HIGH

🟡 Stop loss hit rate high on viral memes (60%)
   Category: exit_reason
   Metric: sl_hit_rate = 0.60
   Significance: MEDIUM

💡 RECOMMENDATIONS (4)

🔴 Recommendation 1 [HIGH]
   Category: stop_loss
   Parameter: viral_multiplier
   Change: 0.8 → 0.65
   Reason: Viral memes dumping before hitting SL, tighten to 65% of base
   Expected: Reduce avg loss by 30%, improve profit factor
   ⚠️  Risk: May get stopped out on volatility spikes

🔴 Recommendation 2 [HIGH]
   Category: filtering
   Parameter: min_confidence
   Change: None → HIGH
   Reason: HIGH confidence trades have 70% win rate vs 45% overall
   Expected: Win rate improvement to 65%+
   ⚠️  Risk: Fewer trading opportunities

⚡ PRIORITY ACTIONS
   1. Tighten viral meme stop losses immediately
   2. Filter for HIGH confidence only
   3. Use wait_for_dip more aggressively

⚠️  CAUTIONS
   - Monitor if tighter SL causes more whipsaws
   - Track if HIGH-only filter reduces opportunity set too much
```

### Application Phase

```
📝 APPLYING RECOMMENDATIONS
======================================================================

Recommendation: stop_loss - viral_multiplier
  Current: 0.8
  Recommended: 0.65
  Reason: Viral memes dumping before hitting SL...
  ✅ Applied

Recommendation: filtering - min_confidence
  Current: None
  Recommended: HIGH
  Reason: HIGH confidence trades have 70% win rate...
  ✅ Applied

✅ Applied 2 changes, skipped 0

📝 Optimization log saved to data/optimization_log.json
```

## What Gets Optimized

### Stop Loss Parameters
- `high_risk_pct`: SL for risk 7-10
- `medium_risk_pct`: SL for risk 4-6
- `low_risk_pct`: SL for risk 0-3
- `tech_multiplier`: Tech token SL adjustment
- `viral_multiplier`: Viral meme SL adjustment

### Take Profit Parameters
- `tp1_mult`, `tp2_mult`, `tp3_mult`: TP target multipliers
- `tp1_exit_pct`, `tp2_exit_pct`, `tp3_exit_pct`: Exit percentages
- Separate settings for high/medium/low risk

### Entry Strategy
- `viral_meme_immediate_liquidity_threshold`: When to enter immediately
- `tech_wait_for_dip_liquidity_threshold`: When to wait for dip
- `wait_for_dip_max_hours`: How long to wait
- `wait_for_dip_target_pct`: Dip percentage to wait for

### Position Sizing
- `max_position_pct`: Max position size
- `high_confidence_mult`: Size multiplier for HIGH confidence
- `medium_confidence_mult`: Size multiplier for MEDIUM
- `low_confidence_mult`: Size multiplier for LOW
- `high_risk_reduction`: Reduce size for high risk tokens

### Filtering Rules
- `min_confidence`: Minimum confidence to trade (None/MEDIUM/HIGH)
- `max_risk_score`: Maximum risk score to accept
- `min_liquidity_sol`: Minimum initial liquidity
- `enabled_token_types`: Which token types to trade

## Files

```
src/optimization/
├── pattern_detector.py         # Claude AI analysis
├── parameter_tuner.py          # Parameter management
└── __init__.py

strategy_optimizer.py           # Main optimizer
data/
├── strategy_parameters.json    # Current parameters
├── parameter_history.json      # Parameter change history
└── optimization_log.json       # Optimization results
```

## Integration with Paper Trading

The paper trader automatically:
1. Loads AI-optimized parameters on startup
2. Uses optimized values for SL/TP calculations
3. Triggers optimization notification every N trades
4. Reloads parameters after optimization runs

**In paper_trade_monitor.py:**
```python
# AI optimization enabled by default
paper_trader = PaperTrader(
    initial_capital=10000,
    use_ai_optimization=True,      # Use AI parameters
    optimize_every_n_trades=10     # Notify every 10 trades
)
```

**After 10 trades, you'll see:**
```
======================================================================
🤖 10 trades completed - AI optimization recommended!
   Run: python strategy_optimizer.py --run-once
   Or wait for continuous optimizer to trigger
======================================================================
```

## Workflow Examples

### Workflow 1: Semi-Automatic (Recommended)

```bash
# Day 1: Start paper trading
python control_panel.py --mode paper_trading --enable
python paper_trade_monitor.py

# After 10 trades (notification appears)
python strategy_optimizer.py --run-once
# Review recommendations → Approve

# After 10 more trades
python strategy_optimizer.py --run-once
# Review → Approve

# Continue...
```

### Workflow 2: Fully Automatic

```bash
# Terminal 1: Paper trading
python paper_trade_monitor.py

# Terminal 2: Continuous optimizer
python strategy_optimizer.py --monitor --auto-apply --every 10

# Both run together, optimizer auto-tunes every 10 trades
```

### Workflow 3: Manual Control

```bash
# Run paper trading (AI parameters disabled)
python paper_trade_monitor.py

# Manually run optimization when you want
python strategy_optimizer.py --run-once --force

# Review and approve each change
```

## Safety Features

### 1. Parameter History & Rollback
Every parameter change is logged. Can rollback if performance degrades:
```bash
python strategy_optimizer.py --rollback
```

### 2. Priority Filtering
Only apply high-priority changes:
```bash
python strategy_optimizer.py --run-once --min-priority high
```

### 3. Approval Required (unless --auto-apply)
Default behavior asks for confirmation before applying changes.

### 4. Performance Tracking
Optimization log tracks before/after metrics to measure impact.

## Advanced Usage

### Custom Optimization Frequency

```python
# In paper_trade_monitor.py
paper_trader = PaperTrader(
    initial_capital=10000,
    optimize_every_n_trades=5  # Optimize more frequently
)
```

### View Current Parameters

```bash
cat data/strategy_parameters.json
```

### View Optimization History

```bash
cat data/optimization_log.json
```

### Manually Adjust Parameters

Edit `data/strategy_parameters.json` directly:
```json
{
  "stop_loss": {
    "high_risk_pct": 0.12,  // Changed from 0.15
    "medium_risk_pct": 0.25,
    "low_risk_pct": 0.35
  }
}
```

Paper trader will use new values on next reload.

## Troubleshooting

### "No trades available"
- Need at least 1 completed trade
- Use `--force` to analyze with minimal data

### "Optimizer not available"
- Import error - check src/optimization/ exists
- Try: `pip install -r requirements.txt`

### "No recommendations from AI"
- Not enough data for patterns
- Wait for more trades
- Performance may already be optimal

### Parameters not updating
- Check if `use_ai_optimization=True` in paper trader
- Verify `data/strategy_parameters.json` was updated
- Restart paper trading monitor

### Rollback failed
- Need at least 2 history entries
- Check `data/parameter_history.json` exists

## Best Practices

### 1. Let It Learn Gradually
- Start with 10-20 trades before first optimization
- Don't optimize too frequently (every 10+ trades is good)
- Give each change time to show results

### 2. Review Recommendations
- Read Claude's reasoning carefully
- Understand WHY each change is suggested
- Don't blind auto-apply at first

### 3. Track Impact
- Compare win rate before/after optimizations
- Check if changes improved or degraded performance
- Rollback if performance drops

### 4. Start Conservative
- Use --min-priority high at first
- Manually approve changes
- Build confidence in the system

### 5. Monitor Patterns
- Pay attention to what Claude identifies
- Learn from the insights
- Adjust your expectations/strategy

## How This Improves Trading

**Before AI Optimization:**
- Fixed parameters for all situations
- Manually guess at adjustments
- Trial and error
- Slow learning

**With AI Optimization:**
- Dynamic parameters based on results
- Data-driven adjustments
- Automated pattern detection
- Continuous improvement

**Example Results:**
```
Week 1 (No optimization):
- Win rate: 52%
- Profit factor: 1.2x

Week 2 (After 2 optimizations):
- Win rate: 64%
- Profit factor: 1.8x
- Tighter SL on memes reduced losses
- Filtering for HIGH confidence improved selection

Week 3 (After 4 optimizations):
- Win rate: 68%
- Profit factor: 2.1x
- Optimized entry strategies per token type
- Better position sizing
```

## Cost Considerations

**Claude API Usage:**
- Optimization triggers every N trades
- Each optimization = 1 Claude API call
- Cost: ~$0.01-0.05 per optimization
- For 100 trades = 10 optimizations = ~$0.10-0.50 total

**ROI:**
- Improved win rate from 50% → 65% = significant P&L improvement
- Cost of optimization << value of better performance
- Well worth it for active trading

## Next Steps

**Immediate:**
1. Start paper trading with AI optimization enabled
2. Let it collect 10-20 trades
3. Run first optimization: `python strategy_optimizer.py --run-once`

**This Week:**
1. Optimize after every 10 trades
2. Review Claude's patterns and recommendations
3. Track performance improvement

**Ongoing:**
1. Consider enabling continuous auto-optimization
2. Monitor optimization log for insights
3. Adjust optimization frequency based on trading volume

**The AI optimizer transforms your trading from static rules to an adaptive learning system. Let Claude do the heavy lifting of analyzing data and finding winning patterns!** 🤖📈
