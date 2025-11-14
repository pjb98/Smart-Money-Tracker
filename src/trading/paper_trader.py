"""
Paper Trading System - Simulate trades without real capital
Tracks positions, executes SL/TP, and maintains trading journal
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
from loguru import logger
from dataclasses import dataclass, asdict
from enum import Enum

# Import adaptive risk manager
from src.trading.adaptive_risk_manager import AdaptiveRiskManager

# Import parameter tuner for AI-optimized parameters
try:
    from src.optimization.parameter_tuner import ParameterTuner
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False
    logger.warning("Optimizer not available, using hardcoded parameters")


class PositionStatus(Enum):
    """Position status"""
    WATCHING = "watching"  # Waiting for entry signal
    PENDING_ENTRY = "pending_entry"  # Waiting for optimal entry
    OPEN = "open"  # Position is active
    CLOSED_TP = "closed_tp"  # Closed at take profit
    CLOSED_SL = "closed_sl"  # Closed at stop loss
    CLOSED_MANUAL = "closed_manual"  # Manually closed
    EXPIRED = "expired"  # Entry window expired


class TokenType(Enum):
    """Token classification for entry strategy"""
    TECH = "tech"  # Tech tokens (often dump then recover)
    VIRAL_MEME = "viral_meme"  # Viral memes (often pump immediately)
    UNKNOWN = "unknown"


@dataclass
class Position:
    """Represents a trading position"""
    token_address: str
    symbol: str
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    position_size_usd: float = 0
    stop_loss: Optional[float] = None
    take_profit_targets: List[float] = None  # Multiple TP levels
    status: PositionStatus = PositionStatus.WATCHING
    token_type: TokenType = TokenType.UNKNOWN

    # Timing
    migration_time: Optional[datetime] = None
    watch_start_time: Optional[datetime] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None

    # Strategy
    recommendation: str = "HOLD"
    confidence: str = "MEDIUM"
    risk_score: int = 5

    # Entry strategy
    entry_strategy: str = "immediate"  # immediate, wait_for_dip, ladder
    entry_filled_pct: float = 0  # % of position filled (for laddering)
    entry_attempts: int = 0
    max_entry_wait_hours: float = 6.0

    # Performance tracking
    unrealized_pnl: float = 0
    realized_pnl: float = 0
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    max_drawdown: float = 0

    # Exit tracking
    exit_reason: Optional[str] = None
    partial_exits: List[Dict] = None  # Track partial exits for laddered TPs

    # Adaptive SL/TP tracking
    tp_stages: List[Dict] = None  # Detailed TP stage info from AdaptiveRiskManager
    trailing_stop_active: bool = False
    trailing_stop_price: Optional[float] = None
    peak_price_for_trailing: Optional[float] = None
    dev_risk_category: Optional[int] = None  # 0=LOW, 1=MEDIUM, 2=HIGH
    token_category: str = "unknown"  # meme, tech, viral, gaming, defi
    volatility_multiplier: float = 1.0

    # Metadata
    notes: List[str] = None

    def __post_init__(self):
        if self.take_profit_targets is None:
            self.take_profit_targets = []
        if self.partial_exits is None:
            self.partial_exits = []
        if self.notes is None:
            self.notes = []
        if self.tp_stages is None:
            self.tp_stages = []


class PaperTrader:
    """
    Paper trading system with position management and journal
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        max_position_size_pct: float = 0.10,
        journal_file: str = "data/trading_journal.json",
        use_ai_optimization: bool = True,
        optimize_every_n_trades: int = 10
    ):
        """
        Initialize paper trader

        Args:
            initial_capital: Starting capital in USD
            max_position_size_pct: Maximum position size as % of capital
            journal_file: Path to trading journal
            use_ai_optimization: Use AI-optimized parameters
            optimize_every_n_trades: Trigger optimization every N trades
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_position_size_pct = max_position_size_pct
        self.journal_file = Path(journal_file)

        # Active positions
        self.positions: Dict[str, Position] = {}  # token_address -> Position

        # Closed positions (for journal)
        self.closed_positions: List[Position] = []

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0

        # AI optimization
        self.use_ai_optimization = use_ai_optimization and OPTIMIZER_AVAILABLE
        self.optimize_every_n_trades = optimize_every_n_trades
        self.last_optimization_trade_count = 0
        self.parameter_tuner = None
        self.parameters = None

        if self.use_ai_optimization:
            self.parameter_tuner = ParameterTuner()
            self.parameters = self.parameter_tuner.get_parameters()
            logger.info("✅ AI optimization enabled - using dynamic parameters")
        else:
            logger.info("📋 Using hardcoded parameters (AI optimization disabled)")

        # Initialize Adaptive Risk Manager
        self.risk_manager = AdaptiveRiskManager()
        logger.info("✅ Adaptive Risk Manager initialized")

        self._load_journal()
        logger.info(f"Paper trader initialized: ${initial_capital} capital")

    def _load_journal(self):
        """Load trading journal from disk"""
        if self.journal_file.exists():
            try:
                with open(self.journal_file, 'r') as f:
                    data = json.load(f)
                    self.current_capital = data.get('current_capital', self.initial_capital)
                    self.total_trades = data.get('total_trades', 0)
                    self.winning_trades = data.get('winning_trades', 0)
                    self.losing_trades = data.get('losing_trades', 0)
                    self.total_pnl = data.get('total_pnl', 0)

                    # Load closed positions
                    closed = data.get('closed_positions', [])
                    self.closed_positions = [self._dict_to_position(p) for p in closed]

                    logger.info(f"Loaded journal: {self.total_trades} trades, ${self.total_pnl:.2f} PnL")
            except Exception as e:
                logger.error(f"Error loading journal: {e}")

    def _save_journal(self):
        """Save trading journal to disk"""
        self.journal_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_pnl': self.total_pnl,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'closed_positions': [self._position_to_dict(p) for p in self.closed_positions],
            'last_updated': datetime.now().isoformat()
        }

        with open(self.journal_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _position_to_dict(self, position: Position) -> Dict:
        """Convert position to dict"""
        d = asdict(position)
        d['status'] = position.status.value
        d['token_type'] = position.token_type.value
        return d

    def _dict_to_position(self, d: Dict) -> Position:
        """Convert dict to position"""
        d['status'] = PositionStatus(d['status'])
        d['token_type'] = TokenType(d['token_type'])
        # Convert datetime strings back to datetime objects
        for field in ['migration_time', 'watch_start_time', 'entry_time', 'exit_time']:
            if d.get(field):
                d[field] = datetime.fromisoformat(d[field])
        return Position(**d)

    def classify_token_type(
        self,
        recommendation: str,
        features: Dict[str, Any],
        twitter_analysis: Optional[Dict[str, Any]] = None
    ) -> TokenType:
        """
        Classify token as TECH or VIRAL_MEME for entry strategy

        Args:
            recommendation: BUY/HOLD/AVOID
            features: Token features
            twitter_analysis: Twitter analysis data

        Returns:
            TokenType classification
        """
        # VIRAL_MEME indicators:
        # - High Phanes scan velocity
        # - Large Twitter following or viral engagement
        # - High social momentum
        # - Fast time on bonding curve

        phanes_velocity = features.get('phanes_scan_velocity', 0)
        social_momentum = features.get('social_momentum', 0)
        time_on_curve = features.get('time_on_bonding_curve_hours', 0)

        twitter_followers = 0
        twitter_engagement = 0
        if twitter_analysis and not twitter_analysis.get('limited_data'):
            twitter_followers = twitter_analysis.get('follower_analysis', {}).get('followers_count', 0)
            twitter_engagement = twitter_analysis.get('engagement_analysis', {}).get('avg_engagement_rate', 0)

        # VIRAL_MEME criteria
        is_viral = (
            phanes_velocity > 100 or  # Very high scan velocity
            twitter_followers > 50000 or  # Large following
            twitter_engagement > 500 or  # High engagement
            (phanes_velocity > 50 and time_on_curve < 3)  # Fast viral growth
        )

        if is_viral:
            return TokenType.VIRAL_MEME

        # TECH tokens typically have:
        # - Lower initial hype
        # - Slower steady growth
        # - Better fundamentals
        has_tech_characteristics = (
            time_on_curve > 12 and  # Slow steady growth
            phanes_velocity < 50 and  # Lower hype
            features.get('unique_wallets_pre_migration', 0) > 100  # Solid community
        )

        if has_tech_characteristics:
            return TokenType.TECH

        return TokenType.UNKNOWN

    def determine_entry_strategy(
        self,
        token_type: TokenType,
        recommendation: str,
        confidence: str,
        features: Dict[str, Any]
    ) -> str:
        """
        Determine optimal entry strategy based on token type

        Args:
            token_type: Token classification
            recommendation: BUY/HOLD/AVOID
            confidence: HIGH/MEDIUM/LOW
            features: Token features

        Returns:
            Entry strategy: 'immediate', 'wait_for_dip', 'ladder'
        """
        if recommendation != 'BUY':
            return 'none'

        liquidity = features.get('initial_liquidity_sol', 0)

        # VIRAL_MEME: Usually best to enter immediately or miss the pump
        if token_type == TokenType.VIRAL_MEME:
            if confidence == 'HIGH' and liquidity > 20:
                return 'immediate'  # Full position now
            else:
                return 'ladder'  # 50% now, 50% on confirmation

        # TECH: Often dumps post-migration, wait for better entry
        elif token_type == TokenType.TECH:
            if liquidity < 10:
                return 'wait_for_dip'  # Wait for initial dump
            else:
                return 'ladder'  # 30% now, 70% on dip

        # UNKNOWN: Conservative laddered entry
        else:
            return 'ladder'  # 50% now, 50% after observing

    def calculate_position_size(
        self,
        recommendation: str,
        confidence: str,
        risk_score: int
    ) -> float:
        """
        Calculate position size based on recommendation and risk

        Args:
            recommendation: BUY/HOLD/AVOID
            confidence: HIGH/MEDIUM/LOW
            risk_score: Risk score 0-10

        Returns:
            Position size in USD
        """
        if recommendation != 'BUY':
            return 0

        # Base position size
        base_size_pct = self.max_position_size_pct

        # Adjust for confidence
        if confidence == 'HIGH':
            size_multiplier = 1.0
        elif confidence == 'MEDIUM':
            size_multiplier = 0.6
        else:  # LOW
            size_multiplier = 0.3

        # Adjust for risk (lower risk = larger size)
        risk_adjustment = 1.0 - (risk_score / 20)  # Risk 0 = 1.0x, Risk 10 = 0.5x

        final_size_pct = base_size_pct * size_multiplier * risk_adjustment
        position_size = self.current_capital * final_size_pct

        return position_size

    def calculate_stop_loss(
        self,
        entry_price: float,
        confidence: str,
        risk_score: int,
        token_category: str = 'unknown',
        dev_risk_category: Optional[int] = None,
        volatility_multiplier: float = 1.0
    ) -> float:
        """
        Calculate adaptive stop loss using AdaptiveRiskManager

        Args:
            entry_price: Entry price
            confidence: HIGH/MEDIUM/LOW
            risk_score: Risk score 0-10
            token_category: Token category (meme/tech/viral/gaming/defi)
            dev_risk_category: Dev risk (0=LOW, 1=MEDIUM, 2=HIGH)
            volatility_multiplier: Volatility adjustment (ATR-based)

        Returns:
            Stop loss price
        """
        return self.risk_manager.calculate_stop_loss(
            entry_price=entry_price,
            confidence=confidence,
            risk_score=risk_score,
            token_category=token_category,
            dev_risk_category=dev_risk_category,
            volatility_multiplier=volatility_multiplier
        )

    def calculate_take_profit_targets(
        self,
        entry_price: float,
        position_size: float
    ) -> List[Dict[str, Any]]:
        """
        Calculate multi-stage take profit targets using AdaptiveRiskManager

        Args:
            entry_price: Entry price
            position_size: Total position size

        Returns:
            List of TP stage dicts with price, size, percentage
        """
        return self.risk_manager.calculate_take_profit_stages(
            entry_price=entry_price,
            position_size=position_size
        )

    async def watch_token(
        self,
        token_address: str,
        symbol: str,
        recommendation: str,
        confidence: str,
        risk_score: int,
        predicted_return: float,
        features: Dict[str, Any],
        twitter_analysis: Optional[Dict[str, Any]] = None,
        current_price: Optional[float] = None,
        dev_risk_category: Optional[int] = None,
        token_category: str = "unknown"
    ) -> Optional[Position]:
        """
        Start watching a token for entry

        Args:
            token_address: Token address
            symbol: Token symbol
            recommendation: BUY/HOLD/AVOID
            confidence: Confidence level
            risk_score: Risk score
            predicted_return: Predicted return
            features: Token features
            twitter_analysis: Twitter analysis
            current_price: Current price if known

        Returns:
            Position object or None if not watching
        """
        if recommendation != 'BUY':
            logger.info(f"Not watching {symbol}: recommendation is {recommendation}")
            return None

        # Classify token type
        token_type = self.classify_token_type(recommendation, features, twitter_analysis)

        # Determine entry strategy
        entry_strategy = self.determine_entry_strategy(
            token_type, recommendation, confidence, features
        )

        if entry_strategy == 'none':
            logger.info(f"Not watching {symbol}: entry strategy is none")
            return None

        # Calculate position size
        position_size = self.calculate_position_size(recommendation, confidence, risk_score)

        if position_size == 0:
            logger.info(f"Not watching {symbol}: position size is 0")
            return None

        # Create position
        position = Position(
            token_address=token_address,
            symbol=symbol,
            current_price=current_price,
            position_size_usd=position_size,
            status=PositionStatus.WATCHING,
            token_type=token_type,
            migration_time=datetime.now(),
            watch_start_time=datetime.now(),
            recommendation=recommendation,
            confidence=confidence,
            risk_score=risk_score,
            entry_strategy=entry_strategy,
            dev_risk_category=dev_risk_category,
            token_category=token_category
        )

        # Set entry timing based on strategy
        if entry_strategy == 'immediate':
            position.max_entry_wait_hours = 0.5  # 30 minutes
        elif entry_strategy == 'wait_for_dip':
            position.max_entry_wait_hours = 6.0  # 6 hours
        else:  # ladder
            position.max_entry_wait_hours = 2.0  # 2 hours for first entry

        self.positions[token_address] = position

        logger.info(f"📊 Watching {symbol} ({token_type.value})")
        logger.info(f"   Entry Strategy: {entry_strategy}")
        logger.info(f"   Position Size: ${position_size:.2f}")
        logger.info(f"   Max Wait: {position.max_entry_wait_hours:.1f}h")

        return position

    async def check_entry_signal(
        self,
        token_address: str,
        current_price: float,
        volume_increase: Optional[float] = None
    ) -> bool:
        """
        Check if entry signal is triggered

        Args:
            token_address: Token address
            current_price: Current price
            volume_increase: Optional volume increase indicator

        Returns:
            True if should enter position
        """
        if token_address not in self.positions:
            return False

        position = self.positions[token_address]

        if position.status != PositionStatus.WATCHING:
            return False

        # Check if entry window expired
        time_elapsed = (datetime.now() - position.watch_start_time).total_seconds() / 3600
        if time_elapsed > position.max_entry_wait_hours:
            logger.info(f"⏰ Entry window expired for {position.symbol}")
            position.status = PositionStatus.EXPIRED
            self._close_position(position, current_price, "Entry window expired")
            return False

        # Entry logic based on strategy
        if position.entry_strategy == 'immediate':
            # Enter immediately
            return True

        elif position.entry_strategy == 'wait_for_dip':
            # Wait for a dip (price drops from initial)
            if position.highest_price is None:
                position.highest_price = current_price
                return False

            # Update highest
            if current_price > position.highest_price:
                position.highest_price = current_price

            # Enter if price dipped 5-10% from high
            dip_pct = (position.highest_price - current_price) / position.highest_price
            if dip_pct >= 0.05:  # 5% dip
                logger.info(f"💧 Dip detected for {position.symbol}: {dip_pct*100:.1f}%")
                return True

        elif position.entry_strategy == 'ladder':
            # Enter first portion immediately, rest on signals
            if position.entry_filled_pct == 0:
                return True  # First entry
            elif position.entry_filled_pct < 1.0:
                # Check for continuation signals (volume, price action)
                if volume_increase and volume_increase > 1.5:  # 50% volume increase
                    logger.info(f"📈 Volume confirmation for {position.symbol}")
                    return True

        return False

    async def enter_position(
        self,
        token_address: str,
        entry_price: float,
        fill_pct: float = 1.0
    ):
        """
        Enter a position with adaptive SL/TP

        Args:
            token_address: Token address
            entry_price: Entry price
            fill_pct: Percentage of position to fill (for laddering)
        """
        if token_address not in self.positions:
            logger.error(f"Cannot enter position: {token_address} not found")
            return

        position = self.positions[token_address]

        # First entry
        if position.entry_price is None:
            position.entry_price = entry_price
            position.entry_time = datetime.now()
            position.current_price = entry_price
            position.highest_price = entry_price
            position.lowest_price = entry_price
            position.status = PositionStatus.OPEN

            # Calculate adaptive SL
            position.stop_loss = self.calculate_stop_loss(
                entry_price=entry_price,
                confidence=position.confidence,
                risk_score=position.risk_score,
                token_category=position.token_category,
                dev_risk_category=position.dev_risk_category,
                volatility_multiplier=position.volatility_multiplier
            )

            # Calculate multi-stage TP targets
            position.tp_stages = self.calculate_take_profit_targets(
                entry_price=entry_price,
                position_size=position.position_size_usd
            )
            position.take_profit_targets = [stage['price'] for stage in position.tp_stages]

            # Store TP details in notes
            position.notes.append(f"Adaptive TP Stages: {json.dumps(position.tp_stages, indent=2, default=str)}")

        # Update filled percentage
        position.entry_filled_pct += fill_pct
        position.entry_filled_pct = min(1.0, position.entry_filled_pct)
        position.entry_attempts += 1

        logger.info(f"✅ ENTERED {position.symbol}")
        logger.info(f"   Entry Price: ${entry_price:.6f}")
        logger.info(f"   Position Size: ${position.position_size_usd * position.entry_filled_pct:.2f} ({position.entry_filled_pct*100:.0f}% filled)")
        logger.info(f"   Stop Loss: ${position.stop_loss:.6f} ({((position.stop_loss/entry_price)-1)*100:.1f}%)")
        logger.info(f"   Take Profit Stages: {len(position.tp_stages)}")
        for stage in position.tp_stages:
            logger.info(f"     {stage['name']}: ${stage['price']:.6f} (+{stage['threshold_pct']:.0f}%) - Sell {stage['sell_percentage']:.0f}%")

        self._save_journal()

    async def update_position(
        self,
        token_address: str,
        current_price: float
    ):
        """
        Update position with current price and check SL/TP (with adaptive features)

        Args:
            token_address: Token address
            current_price: Current price
        """
        if token_address not in self.positions:
            return

        position = self.positions[token_address]

        if position.status != PositionStatus.OPEN:
            return

        # Update price tracking
        position.current_price = current_price

        if position.highest_price is None or current_price > position.highest_price:
            position.highest_price = current_price
            # Update peak for trailing stop
            if position.trailing_stop_active:
                position.peak_price_for_trailing = current_price

        if position.lowest_price is None or current_price < position.lowest_price:
            position.lowest_price = current_price

        # Calculate unrealized PnL
        if position.entry_price:
            remaining_size = position.position_size_usd * (1 - sum(e['size_pct'] for e in position.partial_exits))
            position.unrealized_pnl = (current_price - position.entry_price) / position.entry_price * remaining_size

            # Calculate max drawdown from highest
            if position.highest_price:
                drawdown = (position.highest_price - current_price) / position.highest_price
                position.max_drawdown = max(position.max_drawdown, drawdown)

        # Apply time decay to stop loss (tightens SL over time)
        if position.entry_time and position.stop_loss:
            position.stop_loss = self.risk_manager.update_stop_loss_time_decay(
                current_sl=position.stop_loss,
                entry_price=position.entry_price,
                entry_time=position.entry_time,
                current_time=datetime.now()
            )

        # Check if trailing stop should be activated
        if not position.trailing_stop_active and position.entry_price:
            should_activate = self.risk_manager.should_activate_trailing_stop(
                entry_price=position.entry_price,
                current_price=current_price
            )
            if should_activate:
                position.trailing_stop_active = True
                position.peak_price_for_trailing = current_price
                logger.info(f"🔄 Trailing stop activated for {position.symbol}")

        # Update trailing stop if active
        if position.trailing_stop_active and position.peak_price_for_trailing:
            position.trailing_stop_price = self.risk_manager.calculate_trailing_stop(
                peak_price=position.peak_price_for_trailing,
                confidence=position.confidence,
                current_price=current_price
            )

            # Check if trailing stop hit
            if current_price <= position.trailing_stop_price:
                logger.warning(f"🛑 TRAILING STOP HIT: {position.symbol}")
                logger.warning(f"   Peak: ${position.peak_price_for_trailing:.6f}")
                logger.warning(f"   Exit: ${current_price:.6f}")
                logger.warning(f"   Profit: {((current_price/position.entry_price)-1)*100:.1f}%")
                await self.close_position(token_address, current_price, "Trailing Stop Hit")
                return

        # Check regular Stop Loss
        if position.stop_loss and current_price <= position.stop_loss:
            logger.warning(f"🛑 STOP LOSS HIT: {position.symbol}")
            logger.warning(f"   Entry: ${position.entry_price:.6f}")
            logger.warning(f"   Exit: ${current_price:.6f}")
            logger.warning(f"   Loss: {((current_price/position.entry_price)-1)*100:.1f}%")
            await self.close_position(token_address, current_price, "Stop Loss Hit")
            return

        # Check Take Profit stages
        for stage in position.tp_stages:
            # Check if should execute this stage
            if self.risk_manager.should_execute_stage(stage, current_price):
                # Mark stage as executed
                stage['executed'] = True

                # Get exit size from stage
                exit_size_pct = stage['sell_percentage'] / 100

                logger.success(f"🎯 {stage['name']} HIT: {position.symbol}")
                logger.success(f"   Target: ${stage['price']:.6f}")
                logger.success(f"   Current: ${current_price:.6f}")
                logger.success(f"   Profit: {((current_price/position.entry_price)-1)*100:.1f}%")
                logger.success(f"   Exiting: {exit_size_pct*100:.0f}% of position")

                # Record partial exit
                partial_exit = {
                    'tp_stage': stage['name'],
                    'price': current_price,
                    'size_pct': exit_size_pct,
                    'time': datetime.now().isoformat(),
                    'pnl': (current_price - position.entry_price) / position.entry_price * position.position_size_usd * exit_size_pct
                }
                position.partial_exits.append(partial_exit)
                position.realized_pnl += partial_exit['pnl']

                # Check if all TP stages executed
                all_executed = all(s['executed'] for s in position.tp_stages)
                if all_executed:
                    await self.close_position(token_address, current_price, "All TP Stages Complete")
                    return

                self._save_journal()

    async def close_position(
        self,
        token_address: str,
        exit_price: float,
        reason: str
    ):
        """
        Close a position

        Args:
            token_address: Token address
            exit_price: Exit price
            reason: Reason for closing
        """
        if token_address not in self.positions:
            return

        position = self.positions[token_address]
        self._close_position(position, exit_price, reason)

    def _close_position(self, position: Position, exit_price: float, reason: str):
        """Internal close position logic"""
        position.exit_time = datetime.now()
        position.exit_reason = reason
        position.current_price = exit_price

        # Calculate final PnL
        if position.entry_price:
            remaining_size_pct = 1 - sum(e['size_pct'] for e in position.partial_exits)
            final_pnl = (exit_price - position.entry_price) / position.entry_price * position.position_size_usd * remaining_size_pct
            position.realized_pnl += final_pnl

            # Update capital
            self.current_capital += position.realized_pnl
            self.total_pnl += position.realized_pnl

            # Update stats
            self.total_trades += 1
            if position.realized_pnl > 0:
                self.winning_trades += 1
                position.status = PositionStatus.CLOSED_TP
            else:
                self.losing_trades += 1
                position.status = PositionStatus.CLOSED_SL

            logger.info(f"📕 CLOSED {position.symbol}")
            logger.info(f"   Entry: ${position.entry_price:.6f}")
            logger.info(f"   Exit: ${exit_price:.6f}")
            logger.info(f"   Return: {((exit_price/position.entry_price)-1)*100:.1f}%")
            logger.info(f"   PnL: ${position.realized_pnl:.2f}")
            logger.info(f"   Reason: {reason}")
            logger.info(f"   Capital: ${self.current_capital:.2f} (Total PnL: ${self.total_pnl:.2f})")

        # Move to closed positions
        self.closed_positions.append(position)
        del self.positions[position.token_address]

        self._save_journal()

        # Trigger AI optimization if enabled
        if self.use_ai_optimization:
            self._check_optimization_trigger()

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get trading performance summary"""
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        avg_win = self.total_pnl / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = abs(self.total_pnl) / self.losing_trades if self.losing_trades > 0 else 0

        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_pnl': self.total_pnl,
            'total_return_pct': (self.current_capital / self.initial_capital - 1) * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'active_positions': len(self.positions)
        }

    # ===== AI OPTIMIZATION METHODS =====

    def _get_param(self, *keys, default=None):
        """
        Get parameter from AI-optimized params or fallback to default

        Args:
            *keys: Nested dict keys (e.g., 'stop_loss', 'high_risk_pct')
            default: Fallback value if param not found

        Returns:
            Parameter value or default
        """
        if not self.use_ai_optimization or not self.parameters:
            return default

        value = self.parameters
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def reload_parameters(self):
        """Reload parameters from parameter tuner (after AI optimization)"""
        if self.use_ai_optimization and self.parameter_tuner:
            self.parameters = self.parameter_tuner.get_parameters()
            logger.info("🔄 Reloaded AI-optimized parameters")

    def _check_optimization_trigger(self):
        """Check if we should trigger AI optimization"""
        new_trades = self.total_trades - self.last_optimization_trade_count

        if new_trades >= self.optimize_every_n_trades:
            logger.info(f"\n{'='*70}")
            logger.info(f"🤖 {new_trades} trades completed - AI optimization recommended!")
            logger.info(f"   Run: python strategy_optimizer.py --run-once")
            logger.info(f"   Or wait for continuous optimizer to trigger")
            logger.info(f"{'='*70}\n")

            # Update last count
            self.last_optimization_trade_count = self.total_trades
