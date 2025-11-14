"""
Local DataStore using SQLite for cost-efficient storage
Stores precomputed features, patterns, outcomes, and Claude decisions
"""
import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
from loguru import logger
import pandas as pd


class DataStore:
    """SQLite-based storage for features, patterns, and trading results"""

    def __init__(self, db_path: str = "data/analytics.db"):
        """
        Initialize DataStore with SQLite database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts

        self._create_tables()
        logger.info(f"Initialized DataStore at {db_path}")

    def _create_tables(self):
        """Create all necessary tables"""
        cursor = self.conn.cursor()

        # Table 1: Precomputed Features
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS features (
            token_address TEXT NOT NULL,
            migration_time TEXT NOT NULL,
            features_json TEXT NOT NULL,
            compact_summary_json TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (token_address, migration_time)
        )
        """)

        # Table 2: Trading Patterns (historical situations + outcomes)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            migration_time TEXT NOT NULL,
            pattern_vector TEXT NOT NULL,
            outcome_24h REAL,
            outcome_7d REAL,
            max_gain REAL,
            max_loss REAL,
            category TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # Create index for fast similarity search
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_patterns_category
        ON patterns(category)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_patterns_outcome
        ON patterns(outcome_24h)
        """)

        # Table 3: Claude Decisions & Cache
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS claude_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            migration_time TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            confidence TEXT,
            risk_score INTEGER,
            opportunity_score INTEGER,
            reasoning_json TEXT,
            model_used TEXT,
            tokens_used INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(input_hash)
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_claude_input_hash
        ON claude_decisions(input_hash)
        """)

        # Table 4: Backtest Results Summary
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            total_trades INTEGER,
            win_rate REAL,
            total_return_pct REAL,
            sharpe_ratio REAL,
            max_drawdown_pct REAL,
            avg_win REAL,
            avg_loss REAL,
            profit_factor REAL,
            created_at TEXT NOT NULL
        )
        """)

        # Table 5: Trade Outcomes (for pattern matching)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_address TEXT NOT NULL,
            migration_time TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_time TEXT,
            exit_price REAL,
            return_pct REAL,
            pnl REAL,
            exit_reason TEXT,
            claude_recommendation TEXT,
            features_snapshot_json TEXT,
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_outcomes_token
        ON trade_outcomes(token_address)
        """)

        self.conn.commit()
        logger.info("Database tables created successfully")

    # ===== Feature Storage =====

    def store_features(
        self,
        token_address: str,
        migration_time: datetime,
        features: Dict[str, Any],
        compact_summary: Optional[Dict[str, Any]] = None
    ):
        """
        Store precomputed features for a token

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            features: Complete feature dictionary
            compact_summary: Optional compact summary for Claude
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT OR REPLACE INTO features
        (token_address, migration_time, features_json, compact_summary_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            token_address,
            migration_time.isoformat(),
            json.dumps(features),
            json.dumps(compact_summary) if compact_summary else None,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        logger.debug(f"Stored features for {token_address}")

    def get_features(
        self,
        token_address: str,
        migration_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve precomputed features

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp

        Returns:
            Features dict or None if not found
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT features_json FROM features
        WHERE token_address = ? AND migration_time = ?
        """, (token_address, migration_time.isoformat()))

        row = cursor.fetchone()
        if row:
            return json.loads(row['features_json'])
        return None

    def get_compact_summary(
        self,
        token_address: str,
        migration_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve compact summary for Claude

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp

        Returns:
            Compact summary dict or None
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT compact_summary_json FROM features
        WHERE token_address = ? AND migration_time = ?
        """, (token_address, migration_time.isoformat()))

        row = cursor.fetchone()
        if row and row['compact_summary_json']:
            return json.loads(row['compact_summary_json'])
        return None

    # ===== Pattern Storage & Retrieval =====

    def store_pattern(
        self,
        token_address: str,
        migration_time: datetime,
        pattern_vector: List[float],
        outcome_24h: Optional[float] = None,
        outcome_7d: Optional[float] = None,
        max_gain: Optional[float] = None,
        max_loss: Optional[float] = None,
        category: Optional[str] = None
    ):
        """
        Store a trading pattern with its outcome

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            pattern_vector: Compact feature vector (normalized)
            outcome_24h: 24h return percentage
            outcome_7d: 7d return percentage
            max_gain: Maximum gain observed
            max_loss: Maximum loss observed
            category: Pattern category (e.g., "high_liquidity", "viral_meme")
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO patterns
        (token_address, migration_time, pattern_vector, outcome_24h, outcome_7d,
         max_gain, max_loss, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            token_address,
            migration_time.isoformat(),
            json.dumps(pattern_vector),
            outcome_24h,
            outcome_7d,
            max_gain,
            max_loss,
            category,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        logger.debug(f"Stored pattern for {token_address}")

    def get_similar_patterns(
        self,
        pattern_vector: List[float],
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find most similar historical patterns using simple Euclidean distance

        Args:
            pattern_vector: Current pattern vector
            top_k: Number of similar patterns to return
            category: Optional category filter

        Returns:
            List of similar patterns with outcomes
        """
        cursor = self.conn.cursor()

        # Build query
        query = "SELECT * FROM patterns"
        params = []

        if category:
            query += " WHERE category = ?"
            params.append(category)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            return []

        # Calculate distances
        results = []
        for row in rows:
            stored_vector = json.loads(row['pattern_vector'])

            # Simple Euclidean distance (for hobby use)
            # For production, use FAISS or proper vector DB
            distance = sum(
                (a - b) ** 2
                for a, b in zip(pattern_vector, stored_vector)
            ) ** 0.5

            results.append({
                'token_address': row['token_address'],
                'migration_time': row['migration_time'],
                'outcome_24h': row['outcome_24h'],
                'outcome_7d': row['outcome_7d'],
                'max_gain': row['max_gain'],
                'max_loss': row['max_loss'],
                'category': row['category'],
                'distance': distance,
                'created_at': row['created_at']
            })

        # Sort by distance and return top-k
        results.sort(key=lambda x: x['distance'])
        return results[:top_k]

    def get_patterns_by_outcome(
        self,
        min_outcome: Optional[float] = None,
        max_outcome: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve patterns filtered by outcome range

        Args:
            min_outcome: Minimum 24h return
            max_outcome: Maximum 24h return
            limit: Max number of results

        Returns:
            List of patterns
        """
        cursor = self.conn.cursor()

        query = "SELECT * FROM patterns WHERE 1=1"
        params = []

        if min_outcome is not None:
            query += " AND outcome_24h >= ?"
            params.append(min_outcome)

        if max_outcome is not None:
            query += " AND outcome_24h <= ?"
            params.append(max_outcome)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    # ===== Claude Decision Cache =====

    def cache_claude_decision(
        self,
        token_address: str,
        migration_time: datetime,
        input_hash: str,
        recommendation: str,
        confidence: str,
        risk_score: int,
        opportunity_score: int,
        reasoning: Dict[str, Any],
        model_used: str = "claude-3-haiku-20240307",
        tokens_used: int = 0
    ):
        """
        Cache Claude's decision for future reference

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            input_hash: Hash of input for cache lookup
            recommendation: BUY/HOLD/AVOID
            confidence: HIGH/MEDIUM/LOW
            risk_score: 1-10
            opportunity_score: 1-10
            reasoning: Full reasoning dict
            model_used: Claude model name
            tokens_used: API tokens consumed
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO claude_decisions
            (token_address, migration_time, input_hash, recommendation, confidence,
             risk_score, opportunity_score, reasoning_json, model_used, tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token_address,
                migration_time.isoformat(),
                input_hash,
                recommendation,
                confidence,
                risk_score,
                opportunity_score,
                json.dumps(reasoning),
                model_used,
                tokens_used,
                datetime.now().isoformat()
            ))

            self.conn.commit()
            logger.debug(f"Cached Claude decision for {token_address}")

        except sqlite3.IntegrityError:
            # Already cached (duplicate input_hash)
            logger.debug(f"Decision already cached for hash {input_hash[:8]}...")

    def get_cached_decision(
        self,
        input_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached Claude decision by input hash

        Args:
            input_hash: Hash of input features

        Returns:
            Cached decision or None
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT * FROM claude_decisions
        WHERE input_hash = ?
        ORDER BY created_at DESC
        LIMIT 1
        """, (input_hash,))

        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['reasoning'] = json.loads(result['reasoning_json'])
            return result

        return None

    # ===== Backtest Results =====

    def store_backtest_result(
        self,
        strategy_name: str,
        parameters: Dict[str, Any],
        total_trades: int,
        win_rate: float,
        total_return_pct: float,
        sharpe_ratio: float,
        max_drawdown_pct: float,
        avg_win: float,
        avg_loss: float,
        profit_factor: float
    ):
        """
        Store backtest summary results

        Args:
            strategy_name: Name of strategy
            parameters: Strategy parameters dict
            total_trades: Number of trades
            win_rate: Win rate (0-1)
            total_return_pct: Total return percentage
            sharpe_ratio: Sharpe ratio
            max_drawdown_pct: Max drawdown percentage
            avg_win: Average winning trade
            avg_loss: Average losing trade
            profit_factor: Profit factor
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO backtest_results
        (strategy_name, parameters_json, total_trades, win_rate, total_return_pct,
         sharpe_ratio, max_drawdown_pct, avg_win, avg_loss, profit_factor, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy_name,
            json.dumps(parameters),
            total_trades,
            win_rate,
            total_return_pct,
            sharpe_ratio,
            max_drawdown_pct,
            avg_win,
            avg_loss,
            profit_factor,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        logger.info(f"Stored backtest result for {strategy_name}")

    def get_best_backtest_results(
        self,
        top_k: int = 5,
        min_trades: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top backtest results by Sharpe ratio

        Args:
            top_k: Number of results to return
            min_trades: Minimum number of trades required

        Returns:
            List of top backtest results
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT * FROM backtest_results
        WHERE total_trades >= ?
        ORDER BY sharpe_ratio DESC
        LIMIT ?
        """, (min_trades, top_k))

        rows = cursor.fetchall()
        results = []

        for row in rows:
            result = dict(row)
            result['parameters'] = json.loads(result['parameters_json'])
            results.append(result)

        return results

    # ===== Trade Outcomes =====

    def store_trade_outcome(
        self,
        token_address: str,
        migration_time: datetime,
        entry_time: datetime,
        entry_price: float,
        exit_time: Optional[datetime] = None,
        exit_price: Optional[float] = None,
        return_pct: Optional[float] = None,
        pnl: Optional[float] = None,
        exit_reason: Optional[str] = None,
        claude_recommendation: Optional[str] = None,
        features_snapshot: Optional[Dict[str, Any]] = None
    ):
        """
        Store trade outcome for analysis

        Args:
            token_address: Token mint address
            migration_time: Migration timestamp
            entry_time: Entry timestamp
            entry_price: Entry price
            exit_time: Exit timestamp
            exit_price: Exit price
            return_pct: Return percentage
            pnl: P&L in USD
            exit_reason: Reason for exit
            claude_recommendation: Claude's recommendation
            features_snapshot: Features at entry time
        """
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO trade_outcomes
        (token_address, migration_time, entry_time, entry_price, exit_time, exit_price,
         return_pct, pnl, exit_reason, claude_recommendation, features_snapshot_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            token_address,
            migration_time.isoformat(),
            entry_time.isoformat(),
            entry_price,
            exit_time.isoformat() if exit_time else None,
            exit_price,
            return_pct,
            pnl,
            exit_reason,
            claude_recommendation,
            json.dumps(features_snapshot) if features_snapshot else None,
            datetime.now().isoformat()
        ))

        self.conn.commit()
        logger.debug(f"Stored trade outcome for {token_address}")

    def get_trade_outcomes(
        self,
        limit: int = 100,
        min_return: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Retrieve trade outcomes as DataFrame

        Args:
            limit: Max number of results
            min_return: Optional minimum return filter

        Returns:
            DataFrame of trade outcomes
        """
        query = "SELECT * FROM trade_outcomes WHERE 1=1"
        params = []

        if min_return is not None:
            query += " AND return_pct >= ?"
            params.append(min_return)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        return pd.read_sql_query(query, self.conn, params=params)

    # ===== Utilities =====

    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics

        Returns:
            Dict with table row counts
        """
        cursor = self.conn.cursor()

        stats = {}
        tables = ['features', 'patterns', 'claude_decisions', 'backtest_results', 'trade_outcomes']

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']

        return stats

    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("DataStore closed")


# Example usage
if __name__ == "__main__":
    # Initialize
    store = DataStore("data/analytics.db")

    # Store features
    features = {
        'initial_liquidity_sol': 10.5,
        'holder_count': 234,
        'tx_count_1h': 87,
        'phanes_scan_count': 345
    }

    compact = {
        'liquidity': 10.5,
        'holders': 234,
        'tx_1h': 87,
        'social_score': 345
    }

    store.store_features(
        "SOL_TOKEN_ADDR",
        datetime.now(),
        features,
        compact
    )

    # Store pattern
    pattern_vector = [0.5, 0.3, 0.8, 0.2, 0.6]
    store.store_pattern(
        "SOL_TOKEN_ADDR",
        datetime.now(),
        pattern_vector,
        outcome_24h=0.25,
        category="high_liquidity"
    )

    # Get similar patterns
    similar = store.get_similar_patterns(
        [0.52, 0.31, 0.79, 0.21, 0.61],
        top_k=3
    )

    print("Similar patterns:", similar)

    # Get stats
    print("\nDatabase stats:", store.get_stats())

    store.close()
