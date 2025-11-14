-- Trading Database Schema
-- Optimized for analytics and pattern detection

-- Main trades table
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    symbol TEXT NOT NULL,

    -- Classification
    token_type TEXT, -- tech, viral_meme, unknown
    entry_strategy TEXT, -- immediate, wait_for_dip, ladder
    recommendation TEXT, -- BUY, HOLD, AVOID
    confidence TEXT, -- HIGH, MEDIUM, LOW
    risk_score INTEGER, -- 0-10

    -- Pricing
    entry_price REAL,
    exit_price REAL,
    current_price REAL,
    stop_loss REAL,

    -- Position
    position_size_usd REAL,
    entry_filled_pct REAL, -- For laddered entries

    -- Performance
    pnl REAL,
    return_pct REAL,
    max_drawdown REAL,
    highest_price REAL,
    lowest_price REAL,

    -- Timing
    migration_time TIMESTAMP,
    watch_start_time TIMESTAMP,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    duration_hours REAL,

    -- Exit info
    exit_reason TEXT, -- stop_loss, take_profit, manual, expired
    status TEXT, -- watching, open, closed_tp, closed_sl, etc.
    partial_exits_count INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_token_type ON trades(token_type);
CREATE INDEX IF NOT EXISTS idx_trades_entry_strategy ON trades(entry_strategy);
CREATE INDEX IF NOT EXISTS idx_trades_confidence ON trades(confidence);
CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);

-- Precomputed aggregated statistics (feature store)
CREATE TABLE IF NOT EXISTS aggregated_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Grouping dimensions
    token_type TEXT,
    entry_strategy TEXT,
    confidence TEXT,
    risk_bucket TEXT, -- low (0-3), medium (4-6), high (7-10)

    -- Time window
    window_start TIMESTAMP,
    window_end TIMESTAMP,

    -- Aggregate metrics
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate REAL,

    avg_pnl REAL,
    total_pnl REAL,
    avg_return_pct REAL,

    avg_win REAL,
    avg_loss REAL,
    profit_factor REAL,

    avg_duration_hours REAL,

    -- Exit reasons breakdown
    exit_sl_count INTEGER,
    exit_tp_count INTEGER,
    exit_manual_count INTEGER,

    -- Computed at
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stats_dimensions ON aggregated_stats(token_type, entry_strategy, confidence);
CREATE INDEX IF NOT EXISTS idx_stats_computed ON aggregated_stats(computed_at DESC);

-- Optimization history
CREATE TABLE IF NOT EXISTS optimizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Context
    total_trades_at_time INTEGER,
    trades_since_last INTEGER,

    -- Analysis results
    patterns_identified INTEGER,
    recommendations_count INTEGER,
    high_priority_count INTEGER,

    -- Application
    applied_count INTEGER,
    skipped_count INTEGER,

    -- Performance before
    win_rate_before REAL,
    profit_factor_before REAL,

    -- Claude response (compressed)
    overall_assessment TEXT,
    priority_actions TEXT -- JSON array
);

CREATE INDEX IF NOT EXISTS idx_optimizations_timestamp ON optimizations(timestamp DESC);

-- Parameter changes history
CREATE TABLE IF NOT EXISTS parameter_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    optimization_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Change details
    category TEXT, -- stop_loss, take_profit, entry_strategy, etc.
    parameter_name TEXT,
    old_value TEXT,
    new_value TEXT,

    -- Reasoning
    reason TEXT,
    expected_impact TEXT,
    priority TEXT, -- high, medium, low

    FOREIGN KEY (optimization_id) REFERENCES optimizations(id)
);

CREATE INDEX IF NOT EXISTS idx_param_changes_optimization ON parameter_changes(optimization_id);
CREATE INDEX IF NOT EXISTS idx_param_changes_category ON parameter_changes(category);

-- Partial exits tracking
CREATE TABLE IF NOT EXISTS partial_exits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,

    exit_price REAL,
    size_pct REAL,
    pnl REAL,
    exit_time TIMESTAMP,
    target_label TEXT, -- TP1, TP2, TP3

    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

CREATE INDEX IF NOT EXISTS idx_partial_exits_trade ON partial_exits(trade_id);

-- Pattern cache (for similarity matching)
CREATE TABLE IF NOT EXISTS pattern_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Pattern signature (hash of features)
    pattern_hash TEXT UNIQUE,

    -- Feature vector (normalized, comma-separated)
    features TEXT, -- e.g., "0.75,0.32,0.88,..."

    -- Pattern metadata
    token_type TEXT,
    entry_strategy TEXT,
    confidence TEXT,

    -- Historical performance
    seen_count INTEGER DEFAULT 1,
    avg_return REAL,
    win_rate REAL,

    -- Last seen
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Claude's assessment (cached)
    claude_recommendation TEXT,
    claude_reasoning TEXT,
    cached_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pattern_hash ON pattern_cache(pattern_hash);
CREATE INDEX IF NOT EXISTS idx_pattern_type ON pattern_cache(token_type, entry_strategy);

-- Views for common queries

-- Recent closed trades
CREATE VIEW IF NOT EXISTS v_recent_closed_trades AS
SELECT
    id, token_address, symbol, token_type, entry_strategy,
    confidence, risk_score, entry_price, exit_price,
    pnl, return_pct, entry_time, exit_time,
    CAST((JULIANDAY(exit_time) - JULIANDAY(entry_time)) * 24 AS REAL) as duration_hours,
    exit_reason, status
FROM trades
WHERE status LIKE 'closed%'
ORDER BY exit_time DESC;

-- Performance by token type
CREATE VIEW IF NOT EXISTS v_performance_by_token_type AS
SELECT
    token_type,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
    CAST(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl) as avg_pnl,
    SUM(pnl) as total_pnl,
    AVG(return_pct) as avg_return_pct
FROM trades
WHERE status LIKE 'closed%'
GROUP BY token_type;

-- Performance by entry strategy
CREATE VIEW IF NOT EXISTS v_performance_by_entry_strategy AS
SELECT
    entry_strategy,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    CAST(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl) as avg_pnl,
    SUM(pnl) as total_pnl
FROM trades
WHERE status LIKE 'closed%'
GROUP BY entry_strategy;

-- Performance by confidence
CREATE VIEW IF NOT EXISTS v_performance_by_confidence AS
SELECT
    confidence,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    CAST(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) as win_rate,
    AVG(pnl) as avg_pnl,
    SUM(pnl) as total_pnl
FROM trades
WHERE status LIKE 'closed%'
GROUP BY confidence;
