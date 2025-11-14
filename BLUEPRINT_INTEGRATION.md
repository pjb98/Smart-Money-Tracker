# PumpFun AI Agent - Blueprint Integration Plan

## ✅ What You Already Have (Implemented)

### Core Infrastructure
- ✅ **SQLite Database** - `data/analytics.db` with features, patterns, trades
- ✅ **Feature Engineering** - 50+ features computed from on-chain data
- ✅ **ML Predictions** - XGBoost model for return predictions
- ✅ **Claude AI Agent** - Autonomous decision-making layer
- ✅ **Cost Optimization** - Caching, pattern matching, compact summaries
- ✅ **Paper Trading** - Full simulation with P&L tracking
- ✅ **Dashboard** - 6 tabs showing journal, AI patterns, predictions, etc.
- ✅ **Interactive Terminal** - Just created `claude_interactive.py`
- ✅ **Strategy Optimizer** - AI learns from outcomes and adjusts parameters

### Existing Features (Partial Match to Blueprint)
- ✅ Token migration tracking (via monitor_migrations.py)
- ✅ Holders & distribution (gini coefficient, top holder %)
- ✅ Volume tracking (tx counts across timeframes)
- ✅ Time-based features (hour_of_day, day_of_week)
- ✅ Liquidity analysis (initial SOL, reserves)
- ✅ Phanes bot data integration
- ✅ Risk scoring (via Claude analysis)
- ✅ Confidence levels (HIGH/MEDIUM/LOW)
- ✅ Basic stop-loss strategy
- ✅ Historical pattern matching
- ✅ Learning loop (pattern detector + optimizer)

---

## 🔨 What Needs to Be Built (New)

### Priority 1: Critical Enhancements (Next 1-2 weeks)

#### 1. **Helius Integration** ⭐ HIGH PRIORITY
```
Status: NOT IMPLEMENTED
Importance: Critical for real-time dev tracking

Tasks:
- [ ] Set up Helius RPC/API access
- [ ] Create webhook listener for migration events
- [ ] Implement dev wallet history tracker
- [ ] Add rug pattern detection from dev history
- [ ] Track liquidity burns post-migration
- [ ] Monitor smart wallet & whale activity

Files to create:
- src/ingestion/helius_client.py
- src/webhooks/helius_listener.py
- src/analysis/dev_tracker.py
```

#### 2. **Developer Credibility Index** ⭐ HIGH PRIORITY
```
Status: NOT IMPLEMENTED
Importance: Key risk factor

Metrics to track:
- [ ] Dev wallet history (prior tokens, outcomes)
- [ ] Dexscreener paid status
- [ ] Time between dex_paid and migration
- [ ] Social accounts linked (Twitter, Telegram, Website)
- [ ] Dev holding % and sell behavior
- [ ] Connected wallets (bundle detection)

Files to create:
- src/analysis/dev_credibility.py
- Add to feature_engineer.py
```

#### 3. **Adaptive Entry Logic** ⭐ MEDIUM PRIORITY
```
Status: NOT IMPLEMENTED (uses paper trading simulation only)
Importance: Critical for live trading

Logic:
- [ ] Market order if: High confidence + Expected immediate spike
- [ ] Limit order if: Medium confidence + Expected dip first
- [ ] Skip if: Low confidence or high risk

Decision factors:
- AI confidence score
- Recent price action (pre-migration chart)
- Order book analysis
- Whale activity

Files to modify:
- src/trading/paper_trader.py → Add order_type logic
- src/agents/claude_agent.py → Add entry_type recommendation
```

#### 4. **Enhanced Stop-Loss & Take-Profit** ⭐ HIGH PRIORITY
```
Status: BASIC IMPLEMENTED (fixed % SL)
Needs: Dynamic, adaptive SL/TP

Enhancements:
- [ ] Adaptive SL based on:
  - Confidence level
  - Token category (meme/tech/viral)
  - Market volatility (ATR)
  - Historical pattern similarity
  - Dev risk score

- [ ] Multi-stage Take-Profit:
  - Stage 1: Lock 30% profit at +50%
  - Stage 2: Lock 30% profit at +100%
  - Stage 3: Trailing stop for remaining 40%

- [ ] Trailing stop based on:
  - Confidence (HIGH = tighter trailing)
  - Volatility
  - Time since entry

Files to modify:
- src/trading/paper_trader.py
- data/strategy_parameters.json
```

---

### Priority 2: Important Features (2-4 weeks)

#### 5. **Bundle Detection** ⭐ MEDIUM PRIORITY
```
Status: NOT IMPLEMENTED
Importance: Major risk factor

Detection methods:
- [ ] Transaction timing patterns
- [ ] Wallet creation time clustering
- [ ] Shared funding sources
- [ ] Coordinated buy/sell patterns

Helius API helps with this (wallet history)

Files to create:
- src/analysis/bundle_detector.py
```

#### 6. **Smart Wallet Tracking** ⭐ MEDIUM PRIORITY
```
Status: NOT IMPLEMENTED
Importance: Follow successful traders

Features:
- [ ] Track wallets with high win rates
- [ ] Monitor their positions in real-time
- [ ] Weight confidence higher if smart wallet is buying
- [ ] Alert when smart wallet enters/exits

Files to create:
- src/tracking/smart_wallet_tracker.py
- Add smart_wallet_activity to features
```

#### 7. **Technical Indicators** ⭐ LOW PRIORITY
```
Status: NOT IMPLEMENTED
Importance: Nice-to-have for price analysis

Indicators to add:
- [ ] RSI (Relative Strength Index)
- [ ] MACD (Moving Average Convergence Divergence)
- [ ] ATR (Average True Range) for volatility
- [ ] Bollinger Bands
- [ ] Volume-weighted indicators

Files to create:
- src/features/technical_indicators.py
```

#### 8. **Pre-Migration Chart Analysis** ⭐ MEDIUM PRIORITY
```
Status: NOT IMPLEMENTED
Importance: Pattern recognition on PumpFun curve

Features:
- [ ] Time spent on PumpFun before migration
- [ ] Buy/sell ratio patterns pre-migration
- [ ] Velocity of approach to bonding curve
- [ ] Holder accumulation rate
- [ ] Dev wallet activity during pump phase

Data source: PumpFun API or scraper

Files to create:
- src/ingestion/pumpfun_chart_analyzer.py
```

---

### Priority 3: Nice-to-Have Features (1-2 months)

#### 9. **Real-Time Alerts System** ⭐ LOW PRIORITY
```
Status: NOT IMPLEMENTED
Importance: Quality of life

Alert triggers:
- [ ] High confidence trade opportunity (>80%)
- [ ] Dev wallet sell detected
- [ ] Whale accumulation/distribution
- [ ] Sudden Phanes scan velocity spike
- [ ] Social media viral moment

Delivery methods:
- [ ] Terminal notifications
- [ ] Discord webhook
- [ ] Telegram bot
- [ ] Email (optional)

Files to create:
- src/alerts/alert_manager.py
- src/alerts/discord_webhook.py
```

#### 10. **Category-Specific Strategies** ⭐ MEDIUM PRIORITY
```
Status: BASIC (tech vs viral_meme)
Needs: More granular categories

Categories to add:
- [ ] Tech (utility tokens)
- [ ] Meme (pure memes)
- [ ] Viral (Twitter/social momentum)
- [ ] Gaming
- [ ] DeFi
- [ ] NFT-related

Different strategies per category:
- Tech: Longer hold, higher confidence threshold
- Meme: Quick flip, trailing stops
- Viral: Momentum-based, social signals weighted higher

Files to modify:
- src/features/feature_engineer.py (add category classifier)
- data/strategy_parameters.json (per-category params)
```

#### 11. **Market Sentiment Integration** ⭐ MEDIUM PRIORITY
```
Status: PARTIAL (basic Twitter sentiment)
Needs: Multi-source sentiment

Sources:
- [ ] Twitter trending topics
- [ ] Telegram group activity
- [ ] Discord server engagement
- [ ] Reddit mentions
- [ ] Overall Solana market trend
- [ ] BTC/ETH correlation

Files to create:
- src/sentiment/market_sentiment.py
```

#### 12. **Visual Analytics Dashboard** ⭐ LOW PRIORITY
```
Status: BASIC (current dashboard has tables/charts)
Needs: More visualizations

Charts to add:
- [ ] Confidence vs Outcome scatter plot
- [ ] Holder distribution evolution
- [ ] Dev wallet activity timeline
- [ ] Social signal correlation
- [ ] Win rate by token category
- [ ] Real-time price chart overlay with entry/exit points

Files to modify:
- dashboard.py (add new visualization tabs)
```

---

## 📋 Integration Roadmap

### Phase 1: Foundation (Week 1-2)
1. ✅ Set up Helius account and API access
2. ✅ Implement Helius webhook listener
3. ✅ Create dev wallet tracker
4. ✅ Build Developer Credibility Index
5. ✅ Add bundle detection basics

**Deliverable:** Real-time dev tracking and risk scoring

### Phase 2: Strategy Enhancement (Week 3-4)
1. ✅ Implement adaptive SL/TP logic
2. ✅ Add multi-stage take-profit
3. ✅ Build adaptive entry logic (market vs limit)
4. ✅ Integrate dev risk into confidence scoring
5. ✅ Add smart wallet tracking

**Deliverable:** Dynamic, confidence-based trading strategy

### Phase 3: Intelligence Layer (Week 5-6)
1. ✅ Pre-migration chart analysis
2. ✅ Technical indicators (RSI, MACD, ATR)
3. ✅ Enhanced sentiment analysis
4. ✅ Category-specific strategies
5. ✅ Historical analog matching improvements

**Deliverable:** Comprehensive token evaluation

### Phase 4: UX & Monitoring (Week 7-8)
1. ✅ Real-time alert system
2. ✅ Enhanced dashboard visualizations
3. ✅ Terminal interface improvements
4. ✅ Performance analytics
5. ✅ Backtesting framework

**Deliverable:** Production-ready monitoring system

---

## 🎯 Quick Start: What to Build First

### Recommended First Steps (This Week)

1. **Helius Integration** (Day 1-2)
   - Sign up at https://helius.dev
   - Get API key
   - Create `src/ingestion/helius_client.py`
   - Test dev wallet history queries

2. **Developer Credibility Score** (Day 3-4)
   - Add to `feature_engineer.py`:
     ```python
     def compute_dev_credibility(dev_wallet):
         score = 100
         # Prior rug pulls: -50 each
         # Dex paid: +20
         # Social links: +10
         # Holding %: dynamic
         return score
     ```
   - Integrate into Claude analysis prompt

3. **Adaptive Stop-Loss** (Day 5-7)
   - Modify `paper_trader.py`:
     ```python
     def calculate_adaptive_sl(confidence, category, risk_score):
         base_sl = 0.15  # 15%
         if confidence == "HIGH":
             base_sl *= 0.8  # Tighter SL
         if category == "meme":
             base_sl *= 1.2  # Wider SL
         if risk_score >= 7:
             base_sl *= 0.7  # Much tighter
         return base_sl
     ```

---

## 💡 Architecture Notes

### Data Flow (Enhanced)
```
Helius Webhook (Migration Event)
    ↓
Migration Detector
    ↓
Data Collection:
  - On-chain metrics (Helius RPC)
  - Dexscreener API
  - Phanes scan data
  - Pre-migration chart (PumpFun)
  - Dev wallet history (Helius)
  - Smart wallet positions
    ↓
Feature Engineering:
  - 50+ existing features
  - Dev credibility score
  - Bundle risk score
  - Smart wallet signals
  - Technical indicators
    ↓
ML Model Prediction
    ↓
Claude AI Analysis:
  - Risk assessment
  - Confidence scoring
  - Entry type (market/limit)
  - SL/TP recommendations
    ↓
Human Review (semi-autonomous)
    ↓
Execute Trade (paper or live)
    ↓
Log to Database
    ↓
Learning Loop:
  - Update indicator weights
  - Adjust SL/TP parameters
  - Refine confidence thresholds
```

### Database Schema Additions
```sql
-- New tables needed:
CREATE TABLE dev_wallets (
    address TEXT PRIMARY KEY,
    credibility_score REAL,
    prior_tokens_count INTEGER,
    rug_pull_count INTEGER,
    successful_tokens_count INTEGER,
    last_updated TIMESTAMP
);

CREATE TABLE smart_wallets (
    address TEXT PRIMARY KEY,
    win_rate REAL,
    total_trades INTEGER,
    avg_return REAL,
    tracked_since TIMESTAMP
);

CREATE TABLE bundles (
    bundle_id TEXT PRIMARY KEY,
    token_address TEXT,
    wallet_addresses TEXT,  -- JSON array
    risk_score REAL,
    detected_at TIMESTAMP
);

CREATE TABLE trade_execution (
    id INTEGER PRIMARY KEY,
    token_address TEXT,
    order_type TEXT,  -- 'market' or 'limit'
    entry_price REAL,
    stop_loss REAL,
    take_profit_stages TEXT,  -- JSON
    confidence TEXT,
    executed_at TIMESTAMP
);
```

---

## 🔧 Configuration Updates Needed

### New Settings (add to config/settings.py)
```python
# Helius
helius_api_key: str
helius_rpc_url: str
helius_webhook_secret: str

# Trading
enable_live_trading: bool = False  # Paper trading by default
max_position_size_sol: float = 1.0
min_confidence_for_trade: float = 0.7
adaptive_sl_enabled: bool = True
multi_stage_tp_enabled: bool = True

# Developer Tracking
track_dev_wallets: bool = True
min_dev_credibility_score: float = 50.0

# Smart Wallets
track_smart_wallets: bool = True
smart_wallet_influence_weight: float = 1.5

# Alerts
discord_webhook_url: Optional[str] = None
telegram_bot_token: Optional[str] = None
alert_on_high_confidence: bool = True
alert_on_dev_sell: bool = True
```

---

## 📊 Success Metrics

Track these to measure improvement:
- Win rate (target: >60%)
- Average return per trade (target: >25%)
- Risk-adjusted return (Sharpe ratio)
- Max drawdown (target: <20%)
- Confidence calibration (HIGH confidence should win >80%)
- Dev credibility score accuracy
- Bundle detection rate
- Smart wallet following performance

---

## 🚀 Next Steps

1. Review this integration plan
2. Prioritize which features to build first
3. Set up Helius account (critical for dev tracking)
4. Start with Phase 1 implementation
5. Test each feature with paper trading
6. Gradually enable features as they prove successful

**Want me to start implementing any of these features?** Let me know which priority items you want to tackle first!
