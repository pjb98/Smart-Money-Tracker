# Pumpfun → Raydium Prediction Agent

An AI-powered agent that predicts token performance after migration from Pumpfun to Raydium on Solana. Uses on-chain data, social signals (Phanes bot), and Claude AI for autonomous analysis and decision-making.

## Features

- **Multi-Source Data Ingestion**: Solana RPC, Pumpfun API, Phanes Telegram bot, Twitter/social signals
- **Comprehensive Feature Engineering**: Liquidity metrics, holder distribution, transaction patterns, social sentiment
- **ML Prediction Models**: LightGBM-based regression and classification models
- **Claude AI Integration**: Autonomous reasoning layer that interprets predictions and provides actionable insights
- **Real-time Monitoring**: Continuous migration monitoring with instant alerts
- **Interactive Dashboard**: Dash-based web dashboard for visualizing predictions and performance
- **Backtesting Framework**: Full P&L simulation with multiple trading strategies
- **Free Hobby Mode**: Works with free API tiers and mock data for testing

## Project Structure

```
pumpfun agent/
├── config.py                          # Configuration management
├── main.py                            # Main orchestration script
├── dashboard.py                       # Interactive web dashboard
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
│
├── src/
│   ├── ingestion/                     # Data ingestion modules
│   │   ├── solana_client.py          # Solana RPC client
│   │   ├── pumpfun_client.py         # Pumpfun API client
│   │   └── phanes_parser.py          # Phanes Telegram bot parser
│   │
│   ├── features/                      # Feature engineering
│   │   ├── feature_engineer.py       # Feature computation
│   │   └── label_generator.py        # Label generation for training
│   │
│   ├── models/                        # ML models
│   │   └── predictor.py              # LightGBM prediction model
│   │
│   ├── agents/                        # AI agents
│   │   └── claude_agent.py           # Claude AI integration
│   │
│   └── utils/                         # Utilities
│       ├── logger.py                 # Logging setup
│       └── backtester.py             # Backtesting framework
│
├── data/                              # Data storage
│   ├── cache/                        # Cached data
│   ├── features/                     # Feature store
│   ├── raw/                          # Raw data
│   └── results/                      # Analysis results
│
├── models/                            # Trained models
├── logs/                              # Log files
└── notebooks/                         # Jupyter notebooks for analysis
```

## Installation

### 1. Clone and Setup

```bash
cd "pumpfun agent"
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Solana RPC (use free endpoint or your own)
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com

# Telegram (for Phanes bot parsing)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=your_phone_number
PHANES_CHANNEL_ID=-1001234567890

# Claude AI (required for agent features)
ANTHROPIC_API_KEY=your_claude_api_key

# Optional: Twitter API for social signals
TWITTER_BEARER_TOKEN=your_bearer_token
```

### 4. Initialize Directories

```python
python config.py
```

## Usage

### Quick Start with Mock Data

Test the system with mock data (no API keys required):

```bash
python main.py
```

This will:
1. Generate mock migration events
2. Compute features
3. Make predictions
4. Run Claude analysis (if API key provided)

### Real-time Monitoring

Monitor for new migrations continuously:

```python
import asyncio
from main import PumpfunAgent

async def run_monitor():
    agent = PumpfunAgent(use_mock_data=False)
    await agent.monitor_migrations(check_interval_minutes=5)

asyncio.run(run_monitor())
```

### Training a Model

Train a model on historical data:

```python
from src.models.predictor import train_model_pipeline

predictor = train_model_pipeline(
    features_csv='data/features/features.csv',
    labels_csv='data/features/labels.csv',
    target_variable='return_24h',
    task_type='regression',
    model_save_path='./models/token_predictor.pkl'
)
```

### Running the Dashboard

Start the interactive dashboard:

```bash
python dashboard.py
```

Then open http://localhost:8050 in your browser.

### Backtesting

Run a backtest with different strategies:

```python
from src.utils.backtester import Backtester
import pandas as pd

backtester = Backtester(initial_capital=10000, position_size=0.1)

# Load your predictions and actuals
predictions = pd.read_csv('data/predictions.csv')
actuals = pd.read_csv('data/actuals.csv')

# Run backtest
results = backtester.simulate_trades(predictions, actuals, strategy='threshold')

print(f"Final Capital: ${results['final_capital']:.2f}")
print(f"Total Return: {results['total_return_pct']:.2f}%")
print(f"Win Rate: {results['win_rate']*100:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")

# Compare strategies
comparison = backtester.compare_strategies(predictions, actuals)
print(comparison)
```

## Key Components

### 1. Data Ingestion

**Solana RPC Client** (`src/ingestion/solana_client.py`)
- Fetches on-chain transactions, holder data, token supply
- Handles rate limiting and timeframe queries

**Pumpfun Client** (`src/ingestion/pumpfun_client.py`)
- Fetches migration events and token metadata
- Includes mock client for testing

**Phanes Parser** (`src/ingestion/phanes_parser.py`)
- Parses Telegram bot scan messages
- Tracks scan counts, velocity, sentiment

### 2. Feature Engineering

**FeatureEngineer** (`src/features/feature_engineer.py`)

Computes 40+ features including:
- Temporal: time of day, token age, time since liquidity
- Liquidity: initial SOL, reserve ratios, LP count
- Transactions: counts across multiple windows (1m, 5m, 1h, 6h, 24h)
- Holders: top holder %, Gini coefficient, holder count
- Social: Phanes scans, sentiment, Twitter mentions
- Derived: liquidity per holder, social momentum, concentration risk

**LabelGenerator** (`src/features/label_generator.py`)

Generates training labels:
- Returns over multiple windows (1h, 6h, 24h, 7d)
- Binary pump events (>10%, >20% gains)
- Rug detection (sustained >50% drops)
- Volatility metrics

### 3. ML Models

**TokenPredictor** (`src/models/predictor.py`)

LightGBM-based model with:
- Multi-task support (regression + classification)
- Feature importance analysis
- Prediction explanations
- Model persistence

### 4. Claude AI Agent

**ClaudeAgent** (`src/agents/claude_agent.py`)

Autonomous reasoning layer that:
- Analyzes token features + ML predictions
- Provides risk assessment (1-10 scale)
- Generates BUY/HOLD/AVOID recommendations
- Explains key insights and drivers
- Suggests next actions (rescan, monitor, alert)
- Detects anomalies and suspicious patterns

### 5. Dashboard

Interactive Dash dashboard with:
- Real-time prediction monitoring
- Summary statistics
- Model performance charts
- Feature importance visualization
- Risk analysis

### 6. Backtesting

Full P&L simulation with:
- Multiple strategies (threshold, top-K, risk-adjusted)
- Transaction fees and slippage modeling
- Performance metrics (Sharpe, drawdown, win rate)
- Trade-by-trade analysis

## Free Hobby Mode

The agent works completely free without paid APIs:

- **Solana RPC**: Use free public endpoints (rate-limited but functional)
- **Pumpfun API**: Mock client generates synthetic data for testing
- **Phanes Bot**: Mock parser simulates scan data
- **Storage**: Local SQLite and CSV files
- **Compute**: Train models locally on CPU (LightGBM is fast)
- **Claude AI**: Only component requiring paid API (Claude API)

To run in free mode, set `use_mock_data=True` in main.py.

## MVP Roadmap

### Phase 1: Data Collection (Week 1-2)
- ✅ Solana RPC integration
- ✅ Pumpfun API client
- ✅ Phanes Telegram parser
- Collect 30-90 days historical data for 50+ tokens

### Phase 2: Feature Engineering & Modeling (Week 3-4)
- ✅ Feature engineering pipeline
- ✅ Label generation
- ✅ LightGBM model training
- Baseline model beating random (precision@10)

### Phase 3: AI Agent & Dashboard (Week 5-6)
- ✅ Claude AI integration
- ✅ Interactive dashboard
- ✅ Real-time monitoring
- Alert system (Telegram/Discord)

### Phase 4: Backtesting & Optimization (Week 7-8)
- ✅ Backtesting framework
- ✅ Strategy comparison
- Hyperparameter tuning
- Production deployment

## Key Features from Project Plan

✅ **Data Sources**:
- Solana on-chain data (transactions, holders, liquidity)
- Phanes Telegram bot (scan counts, sentiment, popularity)
- Pumpfun API (migration events, token metadata)
- Social signals (Twitter mentions - optional)

✅ **Feature Engineering**:
- 40+ engineered features across 6 categories
- Rolling window aggregations (1m to 24h)
- Holder concentration metrics (Gini coefficient)
- Social momentum and sentiment scores

✅ **ML Models**:
- LightGBM gradient boosting
- Multi-task learning (returns + pump events)
- Feature importance and SHAP explanations

✅ **Claude AI Agent**:
- Autonomous reasoning and analysis
- Risk assessment and recommendations
- Alert generation and anomaly detection
- Tool-use integration with backend

✅ **Monitoring & Evaluation**:
- Real-time dashboard
- Backtesting with P&L simulation
- Multiple evaluation metrics (MAE, RMSE, AUC, Sharpe)

## Example Output

```json
{
  "token_address": "MOCK...",
  "migration_time": "2025-01-06T...",
  "prediction": {
    "prediction": 0.25,
    "top_features": [
      {"feature": "initial_liquidity_sol", "value": 10.5, "importance": 0.25},
      {"feature": "phanes_scan_velocity", "value": 45, "importance": 0.20},
      {"feature": "holder_count", "value": 234, "importance": 0.18}
    ]
  },
  "claude_analysis": {
    "risk_score": 4,
    "opportunity_score": 7,
    "recommendation": "BUY",
    "confidence": "MEDIUM",
    "key_insights": [
      "Strong initial liquidity (10.5 SOL)",
      "High Phanes scan velocity (45/hr) indicates strong interest",
      "Low top holder concentration (15%) reduces rug risk"
    ]
  }
}
```

## Contributing

This is a research/personal project. Feel free to fork and modify for your own use.

## Disclaimer

**This tool is for educational and research purposes only.**

- Cryptocurrency trading carries significant risk
- Past performance does not indicate future results
- Always do your own research (DYOR)
- Never invest more than you can afford to lose
- This is not financial advice

## License

MIT License

## Contact

For questions or issues, please open a GitHub issue.

---

**Built with**: Python, Solana, LightGBM, Claude AI, Dash, Plotly
