

# Paper Trading System - Test Strategies Without Risk

## Overview

The Paper Trading System simulates real trading with virtual capital, allowing you to test strategies, optimize entry/exit points, and build a track record before risking real money.

## Key Features

### 1. **Intelligent Entry Strategies**
Automatically determines optimal entry based on token type:

**VIRAL_MEME Tokens:**
- High Phanes scan velocity (>100/hr)
- Large Twitter following (>50K)
- High engagement
- **Strategy:** Enter immediately or miss the pump
- **Approach:** Full position or 50/50 ladder

**TECH Tokens:**
- Slower steady growth
- Lower initial hype
- Strong fundamentals
- **Strategy:** Wait for post-migration dip
- **Approach:** 30% now, 70% on dip

### 2. **Automated Stop Loss & Take Profit**
- **Dynamic SL:** Adjusts based on risk score and token type
  - High risk (7-10): 15% stop loss
  - Medium risk (4-6): 25% stop loss
  - Low risk (0-3): 35% stop loss
- **Laddered TP:** Multiple profit targets
  - TP1: 30-50% exit at first target
  - TP2: 30-40% exit at main target
  - TP3: 20-30% exit at moon target

### 3. **Position Sizing**
Automatically calculates position size based on:
- Confidence level (HIGH/MEDIUM/LOW)
- Risk score (0-10)
- Available capital
- Max position size limit (default 10%)

**Example:**
- HIGH confidence + Low risk (2/10) = 10% of capital
- MEDIUM confidence + Medium risk (5/10) = 4% of capital
- LOW confidence + High risk (8/10) = 1% of capital

### 4. **Trading Journal**
Tracks every trade with:
- Entry/exit prices and times
- P&L and returns
- Token classification
- Entry strategy used
- Exit reason
- Max drawdown
- Partial exits
- Notes and analysis

### 5. **Performance Analytics**
- Win rate tracking
- Average win/loss
- Profit factor
- Return on capital
- Best/worst trades
- Pattern analysis by:
  - Token type
  - Entry strategy
  - Confidence level
  - Risk score

## Quick Start

### Start Paper Trading

```bash
# Start with default $10,000 capital
python paper_trade_monitor.py

# Start with custom capital
python paper_trade_monitor.py --capital 50000
```

The monitor will:
1. Detect new migrations
2. Analyze tokens with AI
3. Make BUY/HOLD/AVOID decisions
4. Automatically enter positions for BUY signals
5. Monitor positions and execute SL/TP
6. Track all trades in journal

### View Trading Journal

```bash
# View performance summary
python view_trading_journal.py --summary

# List all trades
python view_trading_journal.py --list

# View specific trade details
python view_trading_journal.py --view 1

# Show only winning trades
python view_trading_journal.py --wins

# Show only losing trades
python view_trading_journal.py --losses

# Analyze patterns
python view_trading_journal.py --analyze
```

## Entry Strategy Logic

### Token Classification

The system automatically classifies tokens:

```python
# VIRAL_MEME indicators:
- Phanes scan velocity > 100/hr
- Twitter followers > 50K
- High engagement (>500 avg)
- Fast growth on bonding curve (<3 hours)

# TECH indicators:
- Time on curve > 12 hours (steady growth)
- Lower hype (scan velocity < 50)
- Strong community (>100 unique wallets)
```

### Entry Timing

**Immediate Entry:**
- Token type: VIRAL_MEME
- Confidence: HIGH
- Liquidity: >20 SOL
- **Action:** Full position immediately

**Wait for Dip:**
- Token type: TECH
- Liquidity: <10 SOL
- **Action:** Wait up to 6 hours for 5-10% dip

**Laddered Entry:**
- Mixed signals or unknown type
- **Action:** Split entry (e.g., 50% now, 50% on confirmation)

### Example Entry Decisions

**Example 1: Viral Meme**
```
Token: PEPEMOON
Type: VIRAL_MEME
Phanes Velocity: 245/hr
Twitter: 85K followers, verified
Recommendation: BUY (HIGH confidence)

Entry Strategy: IMMEDIATE
Position Size: $1,000 (10% of capital)
Entry: 100% at market price
Reason: High viral potential, enter fast or miss pump
```

**Example 2: Tech Token**
```
Token: SOLIDAI
Type: TECH
Time on Curve: 18 hours
Unique Wallets: 342
Recommendation: BUY (MEDIUM confidence)

Entry Strategy: WAIT_FOR_DIP
Position Size: $600 (6% of capital)
Entry: Wait for 5-10% dip from migration price
Max Wait: 6 hours
Reason: Tech tokens often dump post-migration, better entry coming
```

## Stop Loss & Take Profit

### Stop Loss Calculation

```python
# Base SL by risk score
Risk 7-10: 15% SL (tight - high risk)
Risk 4-6:  25% SL (moderate)
Risk 0-3:  35% SL (loose - low risk, let it breathe)

# Adjustments by token type
TECH tokens: 1.3x wider stops (they dip more)
VIRAL_MEME: 0.8x tighter stops (if no pump, exit fast)
```

**Example:**
```
Token: SOLIDAI (TECH, Risk 4/10)
Entry: $0.0001
Base SL: 25%
Adjusted: 25% * 1.3 = 32.5% (tech adjustment)
Stop Loss: $0.0000675
```

### Take Profit Targets

**High Risk (7-10):** Exit early
```
TP1: 40% of predicted return → Exit 50%
TP2: 70% of predicted return → Exit 30%
TP3: 100% of predicted return → Exit 20%
```

**Medium Risk (4-6):** Standard ladder
```
TP1: 50% of predicted return → Exit 30%
TP2: 100% of predicted return → Exit 40%
TP3: 150% of predicted return → Exit 30%
```

**Low Risk (0-3):** Let it run
```
TP1: 100% of predicted return → Exit 30%
TP2: 150% of predicted return → Exit 40%
TP3: 200% of predicted return → Exit 30%
```

**Example:**
```
Token: PEPEMOON
Entry: $0.0001
Predicted Return: 50%
Risk: 4/10 (Medium)

TP1: $0.000125 (25% gain) → Sell 30%
TP2: $0.00015 (50% gain) → Sell 40%
TP3: $0.000175 (75% gain) → Sell 30%
```

## Trading Journal Output

### Summary View
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

🏆 Best Trade:  PEPEMOON (+$1,245.50)
   💔 Worst Trade: RUGCOIN (-$425.00)
```

### Trade List
```
TRADING HISTORY
================================================================================
#    Symbol     Type         Entry               Exit                Return     P&L
-------------------------------------------------------------------------------------
1    PEPEMOON   viral_meme   2025-01-10 14:32   2025-01-10 18:45   +124.5%    +$1,245.50
2    SOLIDAI    tech         2025-01-10 15:20   2025-01-11 02:15   +35.2%     +$420.60
3    MEMECOIN   viral_meme   2025-01-10 16:05   2025-01-10 17:30   -18.3%     -$183.00
...
```

### Trade Detail
```
TRADE DETAIL
================================================================================

📝 Basic Information
   Symbol:       PEPEMOON
   Token Type:   viral_meme
   Recommendation: BUY (HIGH confidence)
   Risk Score:   3/10

💰 Position Details
   Position Size: $1,000.00
   Entry Strategy: immediate
   Entry Price:  $0.000100
   Exit Price:   $0.000225
   Stop Loss:    $0.000072

📈 Performance
   Return:       🟢 +124.5%
   P&L:          🟢 +$1,245.50
   Peak Gain:    +145.2%
   Max Drawdown: -8.5%

⏱️  Timing
   Entry:        2025-01-10 14:32:15
   Exit:         2025-01-10 18:45:30
   Duration:     4.2 hours

🎯 Exit Information
   Exit Reason:  All Take Profits Hit
   Partial Exits: 3
     Exit 1: 30% at $0.000150 (P&L: $150.00)
     Exit 2: 40% at $0.000200 (P&L: $400.00)
     Exit 3: 30% at $0.000225 (P&L: $375.00)
```

### Pattern Analysis
```
TRADING PATTERN ANALYSIS
================================================================================

📊 Performance by Token Type
   Tech Tokens:  5 trades | 80.0% win rate | Avg P&L: $245.50
   Viral Memes:  10 trades | 60.0% win rate | Avg P&L: $185.30

🎯 Performance by Entry Strategy
   Immediate        8 trades | 62.5% win rate | Avg P&L: $175.20
   Wait_for_dip     4 trades | 75.0% win rate | Avg P&L: $320.40
   Ladder           3 trades | 66.7% win rate | Avg P&L: $210.50

💪 Performance by Confidence Level
   HIGH       6 trades | 83.3% win rate | Avg P&L: $450.30
   MEDIUM     7 trades | 57.1% win rate | Avg P&L: $180.20
   LOW        2 trades | 50.0% win rate | Avg P&L: $75.50

🚪 Exit Reasons
   All Take Profits Hit              6 (40.0%)
   Stop Loss Hit                     4 (26.7%)
   Entry window expired              3 (20.0%)
   Manual close                      2 (13.3%)
```

## Understanding Paper Trading Results

### What Paper Trading Tests

✅ **Tests:**
- Entry strategy logic
- Stop loss placement
- Take profit targets
- Position sizing
- Risk management
- Token classification
- Decision-making process

❌ **Does NOT Test:**
- Real slippage
- Liquidity constraints
- Actual execution speed
- Network congestion
- Real market conditions
- Psychological pressure

### Interpreting Results

**Good Signs:**
- Win rate > 60%
- Profit factor > 2.0
- Consistent returns across token types
- Low max drawdown per trade
- Fast profitable exits

**Warning Signs:**
- Win rate < 50%
- Large losses hitting stop loss frequently
- Inconsistent performance
- High max drawdown
- Long losing streaks

### Transitioning to Real Trading

Before going live:
1. ✅ Run paper trading for at least 2-4 weeks
2. ✅ Achieve 50+ paper trades
3. ✅ Maintain win rate > 55%
4. ✅ Profit factor > 1.5
5. ✅ Understand why trades win/lose
6. ✅ Backtest on historical data
7. ✅ Start with small real capital (1-5% of intended size)

## Price Simulation

Currently uses **mock price simulation** for paper trading:

```python
# Simulated price action
VIRAL_MEME: High volatility (±15% per update)
TECH: Lower volatility (±5% per update)
UNKNOWN: Medium volatility (±10% per update)
```

### For Real Price Tracking

To use real prices instead of simulation:

```python
# In paper_trade_monitor.py, replace _fetch_current_price():

async def _fetch_current_price(self, token_address: str) -> float:
    # Fetch from Jupiter, Raydium API, or price oracle
    response = await fetch_from_dex(token_address)
    return response['price']
```

**Price Sources:**
- Jupiter Aggregator API
- Raydium API
- DexScreener API
- Birdeye API (you already have this!)

## Advanced Usage

### Custom Position Sizing

Edit max position size:
```python
# In paper_trade_monitor.py
paper_trader = PaperTrader(
    initial_capital=10000,
    max_position_size_pct=0.05  # 5% max per trade (more conservative)
)
```

### Custom SL/TP Logic

Modify in `src/trading/paper_trader.py`:
```python
def calculate_stop_loss(self, entry_price, risk_score, token_type):
    # Your custom SL logic
    if risk_score > 7:
        sl_pct = 0.10  # Tighter stop (10%)
    else:
        sl_pct = 0.20  # Looser stop (20%)
    return entry_price * (1 - sl_pct)
```

### Filter Trades

Only trade specific types:
```python
# In paper_trade_monitor.py, handle_migration():

# Only trade HIGH confidence
if confidence != 'HIGH':
    return

# Only trade low/medium risk
if risk_score > 6:
    return

# Only trade certain token types
token_type = self.paper_trader.classify_token_type(...)
if token_type != TokenType.VIRAL_MEME:
    return
```

## Files & Structure

```
src/trading/
├── paper_trader.py          # Core paper trading engine
└── __init__.py

paper_trade_monitor.py       # Real-time paper trading monitor
view_trading_journal.py      # Journal viewer and analytics

data/
├── trading_journal.json     # Complete trade history
└── seen_migrations.json     # Tracked migrations
```

## Troubleshooting

**Problem:** No trades being executed
- Check that tokens are getting BUY recommendations
- Verify position sizing is not 0
- Check that confidence/risk criteria are met

**Problem:** All trades hitting stop loss
- SL might be too tight
- Increase SL percentage for tech tokens
- Review token classification logic

**Problem:** Missing take profit targets
- TP targets might be too high
- Check predicted return accuracy
- Adjust TP calculation multipliers

## Next Steps

1. **Run Paper Trading:** Start monitor and collect data
   ```bash
   python paper_trade_monitor.py
   ```

2. **Review Daily:** Check journal regularly
   ```bash
   python view_trading_journal.py --summary
   ```

3. **Analyze Patterns:** After 20+ trades
   ```bash
   python view_trading_journal.py --analyze
   ```

4. **Refine Strategy:** Adjust based on results
   - Tweak SL/TP levels
   - Modify entry strategies
   - Filter by token types

5. **Backtest:** Test on historical data

6. **Go Live:** Once confident in strategy
   - Start with small capital
   - Use real price feeds
   - Implement actual DEX integration

## Integration with Live Trading (Future)

When ready for real trading:

1. Replace price simulation with real DEX prices
2. Add Jupiter/Raydium SDK for actual swaps
3. Implement wallet management
4. Add slippage and fee calculations
5. Include transaction confirmation logic
6. Add emergency manual override

**The paper trading system gives you a complete testing ground to perfect your strategy before risking real capital!** 📈

---

**Built for:** Risk-free strategy testing and optimization
**Module:** `src/trading/paper_trader.py`
**Monitor:** `paper_trade_monitor.py`
**Viewer:** `view_trading_journal.py`
