"""
Test Paper Trader Integration with Adaptive Risk Manager
"""
import asyncio
from src.trading.paper_trader import PaperTrader
from datetime import datetime


async def test_integration():
    """Test the adaptive risk manager integration"""
    print("\n" + "=" * 70)
    print("Testing Paper Trader + Adaptive Risk Manager Integration")
    print("=" * 70 + "\n")

    # Initialize paper trader
    trader = PaperTrader(
        initial_capital=10000,
        use_ai_optimization=False
    )

    # Simulate watching a token
    print("1. Starting to watch a token...")

    features = {
        'phanes_scan_velocity': 150,
        'social_momentum': 75,
        'time_on_bonding_curve_hours': 2,
        'unique_wallets_pre_migration': 120,
        'initial_liquidity_sol': 25
    }

    position = await trader.watch_token(
        token_address="TestToken123",
        symbol="TEST",
        recommendation="BUY",
        confidence="HIGH",
        risk_score=3,
        predicted_return=0.45,
        features=features,
        current_price=0.001234,
        dev_risk_category=0,  # LOW risk dev
        token_category="tech"
    )

    print(f"[OK] Position created: {position.symbol}")
    print(f"  - Entry Strategy: {position.entry_strategy}")
    print(f"  - Confidence: {position.confidence}")
    print(f"  - Dev Risk: {position.dev_risk_category}")
    print(f"  - Token Category: {position.token_category}")

    # Simulate entering the position
    print("\n2. Entering position...")
    await trader.enter_position(
        token_address="TestToken123",
        entry_price=0.001234
    )

    print(f"[OK] Position entered")
    print(f"  - Entry Price: ${position.entry_price:.6f}")
    print(f"  - Stop Loss: ${position.stop_loss:.6f} ({((position.stop_loss/position.entry_price)-1)*100:.1f}%)")
    print(f"  - TP Stages: {len(position.tp_stages)}")
    for stage in position.tp_stages:
        print(f"    - {stage['name']}: ${stage['price']:.6f} (+{stage['threshold_pct']:.0f}%)")

    # Simulate price updates
    print("\n3. Simulating price updates...")

    # Update 1: Small gain
    print("\n  > Price moves to +20%...")
    await trader.update_position("TestToken123", 0.001234 * 1.20)
    print(f"    Unrealized P&L: ${position.unrealized_pnl:.2f}")
    print(f"    Trailing Stop Active: {position.trailing_stop_active}")

    # Update 2: Hit +50% (first TP stage)
    print("\n  > Price moves to +50% (First TP Target)...")
    await trader.update_position("TestToken123", 0.001234 * 1.50)
    print(f"    TP Stage 1 Executed: {position.tp_stages[0]['executed']}")
    print(f"    Partial Exits: {len(position.partial_exits)}")
    print(f"    Realized P&L: ${position.realized_pnl:.2f}")
    print(f"    Trailing Stop Active: {position.trailing_stop_active}")

    # Update 3: Price increases more
    print("\n  > Price moves to +75%...")
    await trader.update_position("TestToken123", 0.001234 * 1.75)
    if position.trailing_stop_active:
        print(f"    Trailing Stop Price: ${position.trailing_stop_price:.6f}")
        print(f"    Peak Price: ${position.peak_price_for_trailing:.6f}")

    # Get performance summary
    print("\n4. Performance Summary:")
    summary = trader.get_performance_summary()
    print(f"  - Total Trades: {summary['total_trades']}")
    print(f"  - Active Positions: {summary['active_positions']}")
    print(f"  - Total P&L: ${summary['total_pnl']:.2f}")
    print(f"  - Current Capital: ${summary['current_capital']:.2f}")

    print("\n" + "=" * 70)
    print("Integration Test Complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_integration())
