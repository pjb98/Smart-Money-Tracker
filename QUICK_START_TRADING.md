# Quick Start Guide - Paper Trading

Get started with paper trading in 5 minutes!

## Step 1: Run Paper Trading Monitor

```bash
python paper_trade_monitor.py
```

This will:
- Monitor for new Pumpfun → Raydium migrations
- Analyze each token with AI
- Automatically make trading decisions
- Execute paper trades with SL/TP
- Track everything in a journal

**Output you'll see:**
```
🤖 PAPER TRADING MONITOR
================================================================================
Simulating trades with virtual capital
Stop Loss and Take Profit automation enabled

💰 Starting Capital: $10,000.00
📊 Max Position Size: 10% per trade

NEW MIGRATION DETECTED
================================================================================
✨ Token: PEPEMOON (MEME)
   Address: ABC...XYZ

📊 ANALYSIS RESULT: PEPEMOON
   Recommendation: BUY (HIGH confidence)
   Risk Score: 3/10

🤖 PAPER TRADING DECISION
================================================================================
📊 Watching PEPEMOON (viral_meme)
   Entry Strategy: immediate
   Position Size: $1,000.00
   Max Wait: 0.5h

✅ ENTERED PEPEMOON
   Entry Price: $0.0001
   Position Size: $1,000.00 (100% filled)
   Stop Loss: $0.000072 (-28.0%)
   Take Profits: 3 levels
     TP1: $0.000125 (+25.0%)
     TP2: $0.000150 (+50.0%)
     TP3: $0.000175 (+75.0%)

💰 Portfolio: $10,000.00 | P&L: $0.00 | Win Rate: 0.0%
================================================================================
```

## Step 2: Let It Run

The monitor will:
- ✅ Watch for new migrations
- ✅ Make BUY/HOLD/AVOID decisions
- ✅ Enter positions automatically
- ✅ Update prices every 60 seconds
- ✅ Execute SL/TP automatically
- ✅ Log all activity

**When TP hits:**
```
🎯 TAKE PROFIT 1 HIT: PEPEMOON
   Target: $0.000125
   Current: $0.000127
   Profit: +27.0%
   Exiting: 30% of position
```

**When SL hits:**
```
🛑 STOP LOSS HIT: RUGCOIN
   Entry: $0.0001
   Exit: $0.000075
   Loss: -25.0%
```

**When fully closed:**
```
📕 CLOSED PEPEMOON
   Entry: $0.0001
   Exit: $0.000175
   Return: +75.0%
   PnL: $+750.00
   Reason: All Take Profits Hit
   Capital: $10,750.00 (Total PnL: $+750.00)
```

## Step 3: Review Performance

```bash
# View summary
python view_trading_journal.py --summary
```

**Output:**
```
TRADING PERFORMANCE SUMMARY
================================================================================

💰 Capital
   Initial:  $10,000.00
   Current:  $12,450.00
   P&L:      $2,450.00 (+24.50%)

📊 Trading Statistics
   Total Trades:   15
   Winning Trades: 10 (66.7%)
   Losing Trades:  5 (33.3%)
   Win Rate:       66.7%

💵 P&L Metrics
   Average Win:    $380.50
   Average Loss:   -$125.20
   Profit Factor:  3.04x
```

## Step 4: Analyze Trades

```bash
# List all trades
python view_trading_journal.py --list

# View specific trade
python view_trading_journal.py --view 1

# Show only wins
python view_trading_journal.py --wins

# Show only losses
python view_trading_journal.py --losses

# Analyze patterns
python view_trading_journal.py --analyze
```

**Pattern Analysis Output:**
```
TRADING PATTERN ANALYSIS
================================================================================

📊 Performance by Token Type
   Tech Tokens:  5 trades | 80.0% win rate | Avg P&L: $245.50
   Viral Memes:  10 trades | 60.0% win rate | Avg P&L: $185.30

🎯 Performance by Entry Strategy
   Immediate        8 trades | 62.5% win rate | Avg P&L: $175.20
   Wait_for_dip     4 trades | 75.0% win rate | Avg P&L: $320.40
```

## Understanding What's Happening

### Entry Strategies

**IMMEDIATE (Viral Memes):**
- Token classified as high-hype meme
- Enters full position immediately
- Reason: Memes pump fast, can't wait

**WAIT_FOR_DIP (Tech Tokens):**
- Token classified as tech/fundamental
- Waits up to 6 hours for 5-10% dip
- Reason: Tech tokens often dump post-migration

**LADDER (Mixed Signals):**
- Unknown type or mixed confidence
- Enters 50% now, 50% later
- Reason: Conservative approach

### Stop Loss Logic

```
High Risk (7-10): 15% stop loss (tight)
Medium Risk (4-6): 25% stop loss (moderate)
Low Risk (0-3): 35% stop loss (loose)

Tech Tokens: 1.3x wider (they dip more)
Viral Memes: 0.8x tighter (if no pump, exit)
```

### Take Profit Laddering

```
TP1: Exit 30-50% at first target
TP2: Exit 30-40% at main target
TP3: Exit 20-30% at moon target

Targets adjust based on:
- Predicted return
- Risk score
- Token type
```

## Tips for Success

### 1. Let It Run for 2-4 Weeks
- Need 30-50 trades for meaningful data
- Patterns emerge over time
- Don't judge on 2-3 trades

### 2. Review Daily
```bash
python view_trading_journal.py --summary
```

### 3. Analyze Patterns Weekly
```bash
python view_trading_journal.py --analyze
```

### 4. Refine Based on Results

**If win rate < 50%:**
- Increase confidence filter (only HIGH)
- Lower max risk (only risk ≤ 5)
- Filter out certain token types

**If hitting SL too much:**
- Widen stop losses
- Wait for better entries
- Improve token classification

**If missing profit targets:**
- Lower TP targets
- Exit faster on memes
- Trail stops on winners

### 5. Review Individual Trades

```bash
python view_trading_journal.py --view 1
```

Learn from both wins and losses:
- Why did this trade work/fail?
- Was entry timing good?
- Did SL/TP levels make sense?
- Should token classification change?

## Common Questions

**Q: How do I change starting capital?**
```bash
python paper_trade_monitor.py --capital 50000
```

**Q: How do I filter trades?**
Edit `paper_trade_monitor.py`:
```python
# Only trade HIGH confidence
if confidence != 'HIGH':
    return

# Only trade low risk
if risk_score > 5:
    return
```

**Q: How do I adjust position sizing?**
Edit max position size in `paper_trade_monitor.py`:
```python
paper_trader = PaperTrader(
    initial_capital=10000,
    max_position_size_pct=0.05  # 5% instead of 10%
)
```

**Q: When should I go live?**
After paper trading shows:
- 50+ trades completed
- Win rate > 55%
- Profit factor > 1.5
- Understand why trades win/lose
- Confident in strategy

## Next Steps

1. **Start paper trading now:**
   ```bash
   python paper_trade_monitor.py
   ```

2. **Let it run overnight** to collect data

3. **Review tomorrow:**
   ```bash
   python view_trading_journal.py --summary
   ```

4. **After 1 week, analyze patterns:**
   ```bash
   python view_trading_journal.py --analyze
   ```

5. **Refine strategy** based on results

6. **After 2-4 weeks**, decide if ready for live trading

## Files Generated

- `data/trading_journal.json` - Complete trade history
- `data/reports/` - Analysis reports for each token
- `logs/agent.log` - Detailed logs of all activity

## Getting Help

**View comprehensive docs:**
- `PAPER_TRADING.md` - Full paper trading documentation
- `REPORTING_SYSTEM.md` - Understanding analysis reports
- `TWITTER_ANALYSIS.md` - Twitter account analysis
- `README.md` - Main project documentation

**Paper trading is the safest way to test your strategy. Run it for weeks, learn from the data, and only go live when you're confident!** 🚀
