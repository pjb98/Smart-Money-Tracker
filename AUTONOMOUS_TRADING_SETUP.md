# Autonomous AI Trading Agent - Complete Setup

## YES! Everything is Set Up for Fully Autonomous Trading

Your AI agent is now **100% autonomous** and will:

1. **Monitor** for new token migrations continuously
2. **Analyze** every token with Claude AI
3. **Trade** automatically based on AI recommendations
4. **Set** adaptive stop-loss and take-profit levels
5. **Execute** SL/TP automatically with trailing stops
6. **Monitor** all positions in real-time
7. **Report** everything to the dashboard

---

## How to Start the AI Agent

### Simple Command

```bash
python main.py
```

That's it! The agent will start in **AUTONOMOUS MODE** and handle everything.

---

## What Happens Automatically

### 1. Token Discovery & Analysis

**Every 5 minutes:**
- Agent checks for new tokens migrating to Raydium
- For each new token:
  ```
  → Fetch on-chain data (transactions, holders, liquidity)
  → Get Phanes scan data (social momentum, velocity)
  → Analyze Twitter account (if available)
  → Fetch developer wallet history (rug risk detection)
  → Build 50+ features
  → Run ML prediction model
  → Send everything to Claude AI for analysis
  ```

### 2. Claude AI Decision Making

**Claude analyzes each token and provides:**
- **Recommendation**: BUY / HOLD / AVOID
- **Confidence**: HIGH / MEDIUM / LOW
- **Risk Score**: 0-10 (lower is better)
- **Reasoning**: Detailed analysis of why
- **Red Flags**: Critical warnings (rug pull indicators, etc.)

### 3. Automatic Trade Execution

**If Claude says BUY:**
```
→ PaperTrader receives the signal
→ Calculates position size based on:
   • Confidence level (HIGH = 100%, MEDIUM = 60%, LOW = 30%)
   • Risk score (lower risk = larger position)
   • Maximum 10% of capital per trade

→ Determines entry strategy:
   • IMMEDIATE: Viral memes with HIGH confidence
   • WAIT_FOR_DIP: Tech tokens (wait for 5-10% dip)
   • LADDER: Split entry (50% now, 50% later)

→ Calculates adaptive stop-loss:
   • Factors: Confidence, risk score, token category, dev risk, volatility
   • Example: HIGH confidence tech with good dev = 14.4% SL

→ Sets multi-stage take-profit:
   • Stage 1: +50% profit → Sell 30%
   • Stage 2: +100% profit → Sell 30%
   • Stage 3: +200% profit → Sell 20%
   • Remaining 20%: Trailing stop

→ Enters position at optimal time
```

### 4. Position Monitoring

**Every 60 seconds:**
```
For each active position:

1. Fetch current price from Solana blockchain

2. Update position:
   → Check if stop-loss hit → Exit if yes
   → Check if TP stages hit → Partial exits
   → Check if trailing stop activated → Activate at +30%
   → Apply time decay → Tighten SL after 24h

3. Check entry signals (for WATCHING positions):
   → IMMEDIATE strategy: Enter now
   → WAIT_FOR_DIP: Enter if 5% dip detected
   → LADDER: Enter first portion, wait for confirmation

4. Log portfolio performance:
   → Current capital
   → Total P&L
   → Win rate
   → Active positions
```

### 5. Automated SL/TP Execution

**Stop-Loss:**
- Triggers automatically when price drops to SL level
- Logs: "🛑 STOP LOSS HIT"
- Closes position, realizes loss
- Updates capital and journal

**Take-Profit Stages:**
- Stage 1 (+50%): "🎯 First Target HIT" → Sell 30%
- Stage 2 (+100%): "🎯 Second Target HIT" → Sell 30%
- Stage 3 (+200%): "🎯 Moon Target HIT" → Sell 20%
- Each partial exit is logged and tracked

**Trailing Stop:**
- Activates automatically at +30% profit
- Tracks peak price as token rises
- Trails 15-25% below peak (based on confidence)
- "🛑 TRAILING STOP HIT" when triggered
- Exits remaining 20% with locked-in profits

**Time Decay:**
- After 24 hours holding, SL tightens automatically
- Reduces SL by 10% per day
- Example: 20% SL → 18% after 24h → 16.2% after 48h
- Protects unrealized gains from evaporating

---

## Full Workflow Example

### Token Migration Detected

```
2025-11-11 10:00:00 | Found 1 new migration
2025-11-11 10:00:01 | Processing migration: $MOON (7Xk9...)
```

### Claude Analysis

```
2025-11-11 10:00:15 | Running Claude analysis...
2025-11-11 10:00:25 | Claude Recommendation: BUY
2025-11-11 10:00:25 | Confidence: HIGH
2025-11-11 10:00:25 | Risk Score: 3/10
2025-11-11 10:00:25 | Dev Credibility: 85/100 (LOW RISK)
```

### Automatic Trading

```
2025-11-11 10:00:26 | 🎯 BUY signal detected! Starting position watch...
2025-11-11 10:00:27 | ✅ Now watching $MOON - Entry strategy: immediate
2025-11-11 10:00:27 | 📈 Entering position for $MOON
2025-11-11 10:00:28 | ✅ ENTERED $MOON
2025-11-11 10:00:28 |    Entry Price: $0.001234
2025-11-11 10:00:28 |    Position Size: $850.00 (100% filled)
2025-11-11 10:00:28 |    Stop Loss: $0.001056 (-14.4%)
2025-11-11 10:00:28 |    Take Profit Stages: 3
2025-11-11 10:00:28 |      First Target: $0.001851 (+50%) - Sell 30%
2025-11-11 10:00:28 |      Second Target: $0.002468 (+100%) - Sell 30%
2025-11-11 10:00:28 |      Moon Target: $0.003702 (+200%) - Sell 20%
```

### Position Monitoring

```
2025-11-11 10:01:28 | Monitoring 1 active position
2025-11-11 10:01:29 | Portfolio: $10,000.00 | P&L: $0.00 | Win Rate: 0.0% | Active: 1

2025-11-11 10:15:00 | Price update: $0.001604 (+30%)
2025-11-11 10:15:01 | 🔄 Trailing stop activated for $MOON
2025-11-11 10:15:01 | Portfolio: $10,000.00 | P&L: $255.00 | Win Rate: 0.0% | Active: 1

2025-11-11 10:30:00 | Price update: $0.001851 (+50%)
2025-11-11 10:30:01 | 🎯 First Target HIT: $MOON
2025-11-11 10:30:01 |    Target: $0.001851
2025-11-11 10:30:01 |    Current: $0.001851
2025-11-11 10:30:01 |    Profit: 50.0%
2025-11-11 10:30:01 |    Exiting: 30% of position
2025-11-11 10:30:01 | Portfolio: $10,127.50 | P&L: $127.50 | Win Rate: 0.0% | Active: 1
```

---

## Key Features

### ✅ Fully Autonomous
- No human intervention required
- Runs 24/7 continuously
- Makes all trading decisions automatically

### ✅ AI-Powered Analysis
- Claude AI evaluates every token
- 50+ features analyzed
- Developer rug risk detection
- Social momentum tracking
- Twitter analysis

### ✅ Dynamic Risk Management
- Adaptive stop-loss (5-30%)
- Multi-stage take-profit
- Trailing stops (+30% activation)
- Time decay protection
- Position sizing based on confidence

### ✅ Transparent Logging
- Every decision logged
- Every trade logged
- Real-time performance tracking
- Detailed reasoning provided

### ✅ Dashboard Integration
- Real-time portfolio view
- Trading journal with all trades
- AI analysis patterns
- Cost optimization metrics
- Live predictions

---

## Configuration

### Capital & Risk Settings

**In `main.py` line 89-93:**
```python
self.paper_trader = PaperTrader(
    initial_capital=10000,        # Starting capital ($10k)
    max_position_size_pct=0.10,   # Max 10% per trade
    use_ai_optimization=False     # Use fixed parameters
)
```

**Change these values** to adjust:
- `initial_capital`: Your starting capital
- `max_position_size_pct`: Maximum % of capital per trade (0.10 = 10%)

### Monitoring Intervals

**In `main.py` line 515-517:**
```python
await asyncio.gather(
    agent.monitor_migrations(check_interval_minutes=5),  # Check for new tokens
    agent.monitor_positions(update_interval_seconds=60)  # Update positions
)
```

**Change these values** to adjust:
- `check_interval_minutes`: How often to check for new tokens (default: 5 min)
- `update_interval_seconds`: How often to update positions (default: 60 sec)

### Adaptive Risk Parameters

**In `src/trading/adaptive_risk_manager.py` line 27-86:**

Customize:
- Base stop-loss percentages
- Confidence multipliers
- Category multipliers (meme/tech/viral)
- Dev risk multipliers
- Take-profit stages
- Trailing stop distances
- Time decay settings

---

## Monitoring the Agent

### 1. Terminal Output

Watch the terminal for real-time logs:
- Token migrations detected
- Claude analysis results
- Trade executions
- Position updates
- SL/TP triggers
- Portfolio performance

### 2. Dashboard

Open in browser: **http://127.0.0.1:8050**

View:
- **Overview**: Portfolio summary, capital, P&L
- **Trading Journal**: All trades with details
- **AI Patterns**: Claude's analysis trends
- **Cost Optimization**: API usage and caching
- **Live Predictions**: Latest AI recommendations
- **Strategy**: Performance metrics

### 3. Trading Journal File

Check: `data/trading_journal.json`

Contains:
- Current capital
- Total trades
- Win/loss record
- All closed positions
- Position details

### 4. Logs

Check: `logs/agent.log`

Contains:
- Detailed execution logs
- Error messages
- Debug information

---

## Safety Features

### Paper Trading Only
- **No real money** involved
- Simulated trades
- Safe testing environment
- Learn without risk

### Risk Controls
- Maximum 10% position size per trade
- Adaptive stop-losses (minimum 5%)
- Multi-stage profit taking
- Trailing stops to lock gains
- Time decay to tighten SL

### Rug Pull Protection
- Developer credibility scoring (0-100)
- Wallet history analysis
- Quick dump pattern detection
- Risky devs get tighter SLs
- HIGH dev risk = POOR quality override

### Quality Assessment
- Trades rated: EXCELLENT / GOOD / FAIR / POOR
- High risk scores force POOR rating
- HIGH dev risk forces POOR rating
- Low R:R ratios flag poor setups

---

## What You Don't Need to Do

❌ **Manually analyze tokens** - Claude AI does it automatically
❌ **Set stop-losses** - Calculated and set automatically
❌ **Set take-profits** - Multi-stage TP set automatically
❌ **Monitor positions** - Updated every 60 seconds automatically
❌ **Execute SL/TP** - Triggers automatically when hit
❌ **Adjust trailing stops** - Updates automatically as price rises
❌ **Tighten SL over time** - Time decay handles it automatically
❌ **Check for new tokens** - Monitored every 5 minutes automatically

---

## What You Should Do

✅ **Start the agent**: `python main.py`
✅ **Watch the terminal**: See what it's doing
✅ **Check the dashboard**: http://127.0.0.1:8050
✅ **Review trades**: Learn from AI's decisions
✅ **Adjust parameters**: If needed, customize risk settings
✅ **Monitor performance**: Track win rate and P&L

---

## Stopping the Agent

Press `Ctrl+C` in the terminal:

```
^C
2025-11-11 12:00:00 | 🛑 Shutting down agent...
2025-11-11 12:00:01 | Agent shutdown complete
2025-11-11 12:00:01 | Agent stopped
```

All positions will be saved. Restart anytime with `python main.py`.

---

## File Structure

```
.
├── main.py                          # MAIN ORCHESTRATOR - Start here
├── dashboard.py                     # Dashboard (run separately)
├── strategy_parameters.json         # Risk management docs
├── AUTONOMOUS_TRADING_SETUP.md     # This file
├── ADAPTIVE_RISK_INTEGRATION.md    # Adaptive SL/TP details
├── DEV_CREDIBILITY_INTEGRATION.md  # Dev rug detection details
├── data/
│   ├── trading_journal.json        # Paper trading history
│   ├── results/                    # Analysis results
│   └── reports/                    # Comprehensive reports
├── logs/
│   └── agent.log                   # Detailed logs
└── src/
    ├── agents/
    │   └── claude_agent.py         # Claude AI analysis
    ├── trading/
    │   ├── paper_trader.py         # Paper trading execution
    │   └── adaptive_risk_manager.py # SL/TP calculation
    ├── ingestion/
    │   ├── helius_client.py        # Dev wallet analysis
    │   ├── solana_client.py        # On-chain data
    │   ├── phanes_parser.py        # Social momentum
    │   └── twitter_analyzer.py     # Twitter analysis
    └── features/
        └── feature_engineer.py     # Feature computation
```

---

## Summary

### The AI Agent Does EVERYTHING:

1. **Discovers** new tokens → Every 5 minutes
2. **Analyzes** with Claude AI → 50+ features + dev risk + social
3. **Decides** BUY/HOLD/AVOID → Based on comprehensive analysis
4. **Trades** automatically → Position sizing + entry strategy
5. **Sets** SL/TP → Adaptive based on 5 factors
6. **Monitors** positions → Every 60 seconds
7. **Executes** exits → Automatic SL/TP + trailing stops
8. **Reports** everything → Dashboard + logs + journal

### You Just Need To:

**Run:** `python main.py`

**Watch:** http://127.0.0.1:8050

**That's it!** 🚀

---

## Live Now

Your autonomous AI trading agent is **ready to run**. It will:

- Make intelligent decisions using Claude AI
- Execute trades based on those decisions
- Manage risk dynamically with adaptive SL/TP
- Protect your capital with rug pull detection
- Monitor everything in real-time
- Log every action transparently

**Start it now:** `python main.py`

**Welcome to autonomous AI trading!** 🤖💰
