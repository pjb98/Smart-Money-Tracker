# Pumpfun → Raydium Prediction Agent

> **Goal:** build an AI agent that ingests a wide variety of on-chain, off-chain, and social signals to discover trends and predict short- to medium-term token performance after a Pumpfun token migrates onto Raydium.

---

## 1. High-level overview

**Problem statement**
When a token migrates to Raydium (or any AMM on Solana), price & liquidity dynamics often show measurable patterns (immediate pumps, dumps, whalebooking, slow growth, or flat performance). We want an agent that uses as much relevant data as possible to discover features and produce probabilistic predictions (e.g., expected % return and risk over 1h / 24h / 7d), plus explainability for why it predicted that outcome.

**Main outputs**
- Predictions per migration event: expected return distribution for windows (1h, 6h, 24h, 7d)
- Probability that token will achieve a X% gain within Y time
- Risk scores (likelihood of rug/pullback >Z%)
- Feature importance / explanations and suggested actionable signals

---

## 2. Data sources

### **Phanes Telegram Bot (Popularity & Sentiment Signal)**
- Parse Phanes bot scan responses using a Telegram client (e.g., Telethon)
- Extract scan count, scan velocity, and popularity metrics
- Useful as a direct measure of trader attention
- Works in a **free hobby setup** through message scraping in a private channel
 (examples & notes)

**On-chain (Solana):**
- Solana RPC nodes (getConfirmedSignaturesForAddress2, getTransaction, getAccountInfo)
- Indexing services: TheGraph (if available for Solana/serum), QuickNode, Helium, custom Solana indexer
- Pumpfun API (token metadata, migration events, timelines)
- Raydium liquidity pool data (pool creation time, initial LP Provider, pool depth, swap events)
- Serum orderbook snapshots (if relevant) and cross-exchange arbitrage
- Token mint metadata, distribution, owners list
- Wallet analytics (smart wallets, suspected bots, multisig, exchanges)

**Off-chain / social / market data:**
- Dune analytics (queries for historical token / pool behaviors) — extract rolling aggregates
- Twitter/X sentiment (tweet volume, sentiment about token, influencer posts)
- Telegram / Discord signals (mentions, pinned announcements — may require scraping/consent)
- CoinGecko / CoinMarketCap for price & marketcap history (if listed)
- Google Trends or other web search trends
- NFT / token launch pages, GitHub activity (if token is associated with an open repo)

**Third-party / heuristics:**
- Whale trackers (large SOL or token transfers to/from exchanges)
- Known scam/rug databases (to filter obvious bad actors) — community blacklist
- Liquidity locker verifications (if LP tokens locked) and audit status

---

## 3. Data ingestion & ETL

**Pipeline outline**
1. **Ingest layer**
   - Poll Pumpfun API for migration events and token ids
   - Subscribe to Solana transaction stream (via RPC websockets or streaming indexer) for related token mint addresses, Raydium pool addresses
   - Pull Dune query results (or maintain parallel analytics) for enriched aggregates
   - Stream social signals (Twitter API v2 filtered stream, webhook listeners for Discord/Telegram)

2. **Staging**
   - Raw JSON events stored in object storage (S3) partitioned by date and token
   - Minimal normalization (timestamp standardization, source tags)

3. **Normalization / Feature store**
   - Convert to tabular feature sets and event timelines (e.g., 1-min bars of volume, tx counts, new holders)
   - Maintain a feature store (e.g., Feast or custom DB) keyed by `(token_id, timestamp)`

4. **Label generation**
   - After migration, compute label windows: returns at 1h, 6h, 24h, 7d and binary events (pump >X%, rug >Y%, sustained gain)

5. **Training datasets**
   - Rolling-window snapshots paired with labels; store train/validation/test splits by time (avoid leakage)

**Tools & infra**
- Orchestration: Airflow / Prefect / Dagster
- Storage: S3 or equivalent + Delta Lake / Iceberg for time travel
- DB: Postgres or TimescaleDB for metadata; ClickHouse for fast analytics; Snowflake/BigQuery optional
- Feature store: Feast or internal tables
- Message queue: Kafka or managed alternative for high-volume streaming

---

## 4. Feature engineering (rich list)

### **Phanes Telegram Bot Features**
- `phanes_scan_count`: total # of scans for the token
- `phanes_scan_velocity`: scans/hour (derived by rescanning periodically)
- `phanes_popularity_rank`: if provided in bot responses
- `phanes_rug_warning`: Phanes safety/risk flags
- `phanes_sentiment_score`: derived from bot's qualitative feedback

These provide a social-trader sentiment signal without paid APIs.

 (rich list)

**Temporal & basic price features**
- Time-of-day, day-of-week, UNIX timestamp
- Time since token mint, time since first liquidity add, time since migration announcement
- Pre-migration price trend slope, pre-migration volatility

**Liquidity & pool metrics**
- Initial liquidity added (USD, SOL), initial LP providers (count & identities)
- Pool depth vs circulating supply ratio
- Token price slippage for test swaps (simulate impact)
- Ratio of traded pairs (TOKEN/SOL vs TOKEN/USDC)
- Presence & amount of liquidity locked

**On-chain activity**
- Transaction count per minute/hour pre- and post-migration
- New holders per time window; Gini / Herfindahl index of holder distribution
- Transfers to exchange-associated addresses
- Smart contract calls (if token uses program logic)
- Number of unique interacting wallets and reuse rate

**Whale / address-level features**
- Top N holders’ share and change in share pre/post migration
- Transfers between top holders
- Known exchange wallet receipts or deposits
- Ratio of smart wallets vs EOAs (heuristic for bots)

**Behavioral & social features**
- Tweet/mention volume in last 1h/6h/24h; sentiment score (positive/negative/neutral)
- Influencer mentions (binary per notable handle)
- Discord / Telegram mention burst metrics
- Pumpfun-specific metrics: time spent pre migration on Pumpfun, promotion rank, listing sequence

**Derived & advanced features**
- Cross-exchange arbitrage pressure (difference in quote prices if token appears elsewhere)
- Orderbook imbalance on Serum / Raydium (buy vs sell depth)
- Graph features: PageRank of holder transaction graph, community detection of cluster buys
- Rate of new token contract interactions from flagged bot addresses

---

## 5. Labels & problem framing

**Primary label choices**
- Regression: realized log-return over T = {1h, 6h, 24h, 7d}
- Classification: whether return > 10% within 1h, 50% within 24h, etc.
- Multi-task: produce both (regression + binary event probabilities)

**Other labels**
- Volatility label: realized volatility over window
- Rug / exit-scam flag: big holder drains LP within X hours

**Avoid leakage**
- Use only features available up to prediction moment (just after migration). Keep any post-migration features out of training inputs for that prediction moment.

---

## 6. Modeling approaches

**Baseline models**
- Logistic Regression / Ridge / Lasso for classification/regression on engineered features
- Gradient-boosted trees (XGBoost / LightGBM / CatBoost) — strong baseline for tabular features

**Time-series models**
- Temporal convolutional networks or LSTM for sequential time features
- Transformer-based time-series (e.g., Informer, Temporal Fusion Transformer)

**Graph & relational models**
- GNNs on holder-transfer graphs to capture structure (GraphSAGE, GAT)
- Node embeddings (node2vec) used as features in tree models

**Ensembles & stacking**
- Combine tree models with time-series deep models and graph-derived embeddings

**Probabilistic forecasting**
- Predict full return distribution (quantile regression, or Gaussian mixture models) rather than point estimate

**Anomaly detection**
- Autoencoders or one-class SVM to detect unusual/risky migrations (likely scams)

---

## 7. Evaluation & backtesting

**Metrics**
- Regression: MAE, RMSE, MAPE, R², calibration of predicted quantiles
- Classification: AUC-ROC, PR-AUC (if positive class is rare), precision@k, recall@k
- Economic metrics: simulated P&L from a strategy using predictions (Sharpe, max drawdown, win rate)

**Backtesting methodology**
- Use time-based splits. Train on older migrations, validate on more recent ones.
- Simulate realistic latency and slippage when evaluating trading gains.
- Include transaction costs, swap fees, and slippage in simulations

**Stress tests**
- Evaluate during extreme network conditions or SOL price shocks
- Test sensitivity to missing data and delayed signals

---

## 8. Explainability & interpretability

- SHAP or TreeSHAP for tree models to show feature attribution at token-event level
- Counterfactual explanations: which small changes would flip the prediction
- GNN explanation tools (e.g., GNNExplainer) to show subgraphs driving predictions
- Human-readable summary: top 3 drivers (e.g., "high initial liquidity + low top-holder concentration + influencer mentions")

---

## 9. Monitoring & operations

- Data quality checks: missing rates, outlier detection, time drift
- Model monitoring: concept drift detection (feature distributions and label drift)
- Prediction health: track calibration, realized vs predicted returns
- Alerting on model deterioration and infra failures

---

## 10. Ethics, legal, and policy

- Avoid explicit facilitation of fraud or malicious activity. Include a risk filter for tokens flagged by community/regulators.
- Check Terms of Service for each API (Twitter/TG Discord scraping). Avoid scraping private communities.
- Privacy: avoid storing PII. Treat wallets as public on-chain data but be mindful about linking to off-chain personal identities.
- Compliance: follow exchange rules and local laws when acting on predictions or automating trades.

---

## 11. Security & cost considerations

- Rate-limit handling & caching for Solana RPC and Pumpfun APIs
- Use rate-limited API keys, circuit breakers to avoid DoS
- Cost: streaming Solana topics and Twitter ingest can be expensive — budget for node providers and data storage
- Secrets: store API keys and RPC endpoints in vault (HashiCorp / AWS Secrets Manager)

---

## 12. Minimal viable product (MVP)

### **Free Hobby Version Requirements**
- Use only free Solana RPC endpoints (rate-limited but workable)
- Manual / semi-automated Phanes scan parsing via Telegram
- No paid Dune API — instead run slow free queries or export CSVs
- Local storage (CSV/SQLite) instead of cloud warehouses
- Train models locally (LightGBM on CPU)
- No paid social APIs — rely on Phanes scan count + simple sentiment sources

This version is completely viable for personal research and experimentation.

---
 (MVP)

**MVP scope (fast path)**
- Collect Pumpfun migration events
- Ingest Solana RPC for 24 hours pre/post migration and compute: initial liquidity, tx counts, new holders, top holder shares
- Pull Twitter mention volume & simple sentiment
- Train a LightGBM classifier to predict 24h positive return (>20%)
- Dashboard showing predictions, top features, and backtest P&L

**MVP success criteria**
- Model beats a simple baseline (e.g., always predict no pump) by X% in precision@10
- Dashboard refreshes predictions within N minutes of migration event

---

## 12.5. Claude AI Agent Integration

### **Role of Claude as the AI Agent**
Claude Premium acts as the autonomous reasoning layer that interprets model outputs, monitors incoming data, triggers automated actions, and produces human‑readable insights.

### **What Claude Does in the System**
- Interprets raw features + ML model predictions
- Detects anomalies or early hype signals (e.g., rising Phanes scan count)
- Suggests next actions (rescan token, check holders, re‑query LP depth)
- Generates explanations, risk scores, and summary reports
- Pushes alerts to Telegram/Discord
- Performs tool‑use via your backend (trigger Python scripts, request RPC fetches, etc.)

### **Claude Integration Workflow**
1. Your pipeline ingests data from Pumpfun, Solana RPC, Raydium, Dune, and Phanes.
2. Data is converted into features and sent to your ML prediction model.
3. The **ML model outputs predictions**.
4. Claude receives:
   - The model’s output
   - The most recent token features
   - Recent Phanes scan data
   - Any alerts or metric changes
5. Claude produces:
   - Reasoned analysis and explanations
   - Updated risk/hype assessments
   - Suggested actions
   - Telegram/Discord alerts
6. Claude may trigger automated tasks through your backend (tool‑use / function calls).

### **Claude Agent Loop (Pseudocode)**
```
loop:
    new_event = check_for_new_migration()
    if new_event:
        features = build_features(new_event)
        model_output = run_ml_model(features)

        claude_analysis = claude_agent(
            features=features,
            model_output=model_output,
            recent_phases_scans=get_phanes_data(),
            historical_patterns=get_recent_history()
        )

        send_alert(claude_analysis)

    if hype_increasing():
        claude_recommendation = claude_agent(reason="Hype spike detected")
        if claude_recommendation["action"] == "rescan":
            run_phanes_scan(token)
            update_features()

    sleep(interval)
```

### **Why Claude Works Well**
- Large context window lets it reason over full token history + features.
- Strong tool‑use for calling scripts and APIs.
- Works perfectly in a **free hobby setup** where Claude handles the reasoning while your local scripts handle data.
- Eliminates the need for expensive MLops infrastructure.

### **Integration Requirements**
- Claude API key (included with Claude Premium)
- A small backend with defined function endpoints for:
  - Fetching new data
  - Triggering Phanes scans
  - Querying your feature store
  - Sending Telegram messages

---

## 13. Roadmap & milestones

**Phase 0 — Research (2–4 weeks)**
- Inventory of data availability and rate limits
- Prototype ingestion for 10 historical migrations
- Exploratory data analysis and feature importance sketch

**Phase 1 — MVP (4–8 weeks)**
- Build ETL pipeline, feature store, and a LightGBM model
- Basic dashboard & backtest

**Phase 2 — Expand data & models (8–12 weeks)**
- Add GNN embeddings, social data improvements, quantile predictions
- Improve productionization and monitoring

**Phase 3 — Production (ongoing)**
- Robust monitoring, auto-retraining, model ensembles, latency optimization

---

## 14. Example queries & snippets

### 1) Solana RPC (get confirmed signatures recent for a mint address)

```bash
curl https://api.mainnet-beta.solana.com -X POST -H "Content-Type: application/json" -d '
{ "jsonrpc":"2.0", "id":1, "method":"getSignaturesForAddress", "params":["<MINT_OR_POOL_ADDR>", {"limit": 1000}] }
'
```

### 2) SQL-style example: compute new holders in last 24h (pseudocode)

```sql
SELECT token_mint,
       count(distinct to_address) as new_holders_24h
FROM transfers
WHERE transfer_time BETWEEN migration_time - interval '24 hours' AND migration_time
GROUP BY token_mint;
```

### 3) Pumpfun API example (pseudocode)

```
GET /api/v1/migrations?since=2025-01-01
Response: [{ token: "ABC", migration_time: "2025-10-01T12:00:00Z", pre_migration_rank: 5, ... }]
```

---

## 15. Data schema (suggested feature table)

`features_token_snapshot` (key: token_id, snapshot_ts)
- token_id (string)
- snapshot_ts (timestamp)
- time_since_mint (s)
- time_since_first_liq_add (s)
- initial_liquidity_usd (float)
- pre_migration_tx_count_1h (int)
- pre_migration_tx_count_24h (int)
- pre_migration_new_holders_24h (int)
- top1_holder_pct (float)
- top5_holder_pct (float)
- gini_holder_distribution (float)
- tweets_1h (int)
- tweets_sentiment_1h (float)
- influencer_mention_flag (bool)
- pool_locked_flag (bool)
- rug_risk_score (float)
- label_return_24h (float)
- label_positive_24h (bool)

---

## 16. Implementation & dev notes

- Version control for Dune queries & SQL: store them in the repo
- Use tests for data pipelines (contract tests for feature shapes, unit tests for transforms)
- Small reproducible notebooks for EDA
- Keep a reproducible environment (Docker) and a `requirements.txt` or `poetry.lock`

---

## 17. Team & roles (if applicable)

- Data Engineer: ingestion, indexers, feature store
- ML Engineer: model training, validation, explainability
- Backend Engineer: API, dashboard, infra
- Quant / Researcher: EDA, labeling choices, strategy backtests
- Security/Compliance: vetting tokens and data sources

---

## 18. Potential improvements & experiments

- Use contrastive learning to learn token embeddings from transaction sequences
- Fine-grained causal analysis: try to isolate causal patterns (do influencer mentions precede pumps?)
- Active learning: focus labeling effort on edge cases where model uncertain
- Reinforcement learning for automated execution strategies (careful with compliance)

---

## 19. Risks & mitigations

- **Data scarcity**: few historical migrations -> use transfer learning & data augmentation
- **Label noise**: returns affected by liquidity & slippage -> incorporate slippage into label calc
- **Adversarial behavior**: actors might intentionally game signals (bot amplification). Build adversarial detection and downweight suspicious signals.

---

## 20. Next steps (suggested immediate actions)
1. Confirm data source access (API keys, RPC endpoints, Dune/SQL access)
2. Prototype ingestion and create a 30–90 day historical dataset for 20–50 tokens
3. Run EDA to validate predictive signal existence
4. Implement MVP pipeline + LightGBM model

---

## Appendix: reading & resources (internal)
- Keep a tracked list of useful Dune queries, Pumpfun endpoints, Solana RPC call recipes, and recommended external data providers.


---

*End of document.*

