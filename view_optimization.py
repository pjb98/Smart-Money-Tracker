"""
View AI Optimization History and Performance
"""
import json
from pathlib import Path
from datetime import datetime
import argparse


def view_current_parameters():
    """Display current strategy parameters"""
    params_file = Path("data/strategy_parameters.json")

    if not params_file.exists():
        print("❌ No parameters file found")
        print("   Parameters will be created on first paper trade")
        return

    with open(params_file, 'r') as f:
        params = json.load(f)

    print("\n" + "="*70)
    print("CURRENT STRATEGY PARAMETERS")
    print("="*70)

    # Stop Loss
    print("\n🛑 Stop Loss Settings:")
    sl = params.get('stop_loss', {})
    print(f"   High Risk (7-10):  {sl.get('high_risk_pct', 0)*100:.1f}%")
    print(f"   Medium Risk (4-6): {sl.get('medium_risk_pct', 0)*100:.1f}%")
    print(f"   Low Risk (0-3):    {sl.get('low_risk_pct', 0)*100:.1f}%")
    print(f"   Tech Multiplier:   {sl.get('tech_multiplier', 1):.2f}x")
    print(f"   Viral Multiplier:  {sl.get('viral_multiplier', 1):.2f}x")

    # Position Sizing
    print("\n💰 Position Sizing:")
    ps = params.get('position_sizing', {})
    print(f"   Max Position:       {ps.get('max_position_pct', 0)*100:.1f}%")
    print(f"   HIGH Confidence:    {ps.get('high_confidence_mult', 1):.2f}x")
    print(f"   MEDIUM Confidence:  {ps.get('medium_confidence_mult', 1):.2f}x")
    print(f"   LOW Confidence:     {ps.get('low_confidence_mult', 1):.2f}x")

    # Filters
    print("\n🔍 Filtering Rules:")
    filt = params.get('filters', {})
    min_conf = filt.get('min_confidence')
    print(f"   Min Confidence:     {min_conf if min_conf else 'None (all accepted)'}")
    print(f"   Max Risk Score:     {filt.get('max_risk_score', 10)}/10")
    print(f"   Min Liquidity:      {filt.get('min_liquidity_sol', 0)} SOL")

    # Metadata
    print(f"\n📝 Last Updated: {params.get('last_updated', 'N/A')}")
    print(f"📌 Version: {params.get('version', 1)}")
    print("="*70)


def view_optimization_history(limit: int = 10):
    """Display optimization history"""
    log_file = Path("data/optimization_log.json")

    if not log_file.exists():
        print("❌ No optimization history found")
        print("   Run: python strategy_optimizer.py --run-once")
        return

    with open(log_file, 'r') as f:
        history = json.load(f)

    if not history:
        print("📭 Optimization history is empty")
        return

    # Show last N optimizations
    recent = history[-limit:]

    print("\n" + "="*70)
    print(f"OPTIMIZATION HISTORY (Last {len(recent)} of {len(history)})")
    print("="*70)

    for i, entry in enumerate(reversed(recent), 1):
        timestamp = entry.get('timestamp', 'N/A')
        total_trades = entry.get('total_trades', 0)
        analysis = entry.get('analysis', {})
        application = entry.get('application', {})

        applied = application.get('applied', 0)
        skipped = application.get('skipped', 0)

        print(f"\n{i}. {timestamp}")
        print(f"   Total Trades: {total_trades}")
        print(f"   Patterns Found: {len(analysis.get('patterns', []))}")
        print(f"   Recommendations: {len(analysis.get('recommendations', []))}")
        print(f"   Applied: {applied} | Skipped: {skipped}")

        # Show priority actions
        if analysis.get('priority_actions'):
            print(f"   Priority Actions:")
            for action in analysis['priority_actions'][:2]:
                print(f"      - {action}")

    print("="*70)


def view_parameter_history(limit: int = 10):
    """Display parameter change history"""
    history_file = Path("data/parameter_history.json")

    if not history_file.exists():
        print("❌ No parameter history found")
        return

    with open(history_file, 'r') as f:
        history = json.load(f)

    if not history:
        print("📭 Parameter history is empty")
        return

    recent = history[-limit:]

    print("\n" + "="*70)
    print(f"PARAMETER CHANGE HISTORY (Last {len(recent)} of {len(history)})")
    print("="*70)

    for i, entry in enumerate(reversed(recent), 1):
        timestamp = entry.get('timestamp', 'N/A')
        reason = entry.get('reason', 'N/A')

        print(f"\n{i}. {timestamp}")
        print(f"   Reason: {reason}")

    print("="*70)


def view_performance_comparison():
    """Compare performance before/after optimizations"""
    journal_file = Path("data/trading_journal.json")
    log_file = Path("data/optimization_log.json")

    if not journal_file.exists() or not log_file.exists():
        print("❌ Need both trading journal and optimization log")
        return

    with open(journal_file, 'r') as f:
        journal = json.load(f)

    with open(log_file, 'r') as f:
        opt_history = json.load(f)

    if not opt_history:
        print("📭 No optimizations yet")
        return

    # Get current performance
    current_win_rate = journal.get('win_rate', 0)
    total_trades = journal.get('total_trades', 0)
    total_pnl = journal.get('total_pnl', 0)

    # Get trade count at first optimization
    first_opt = opt_history[0]
    trades_at_first_opt = first_opt.get('total_trades', 0)

    # Get trade count at last optimization
    last_opt = opt_history[-1]
    trades_at_last_opt = last_opt.get('total_trades', 0)

    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON")
    print("="*70)

    print(f"\n📊 Overall:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Total Optimizations: {len(opt_history)}")
    print(f"   Current Win Rate: {current_win_rate*100:.1f}%")
    print(f"   Total P&L: ${total_pnl:.2f}")

    print(f"\n📈 Timeline:")
    print(f"   First Optimization: After {trades_at_first_opt} trades")
    print(f"   Last Optimization: After {trades_at_last_opt} trades")
    print(f"   Trades Since Last: {total_trades - trades_at_last_opt}")

    # Calculate before/after if possible
    if len(opt_history) >= 2:
        print(f"\n💡 Insights:")
        print(f"   Optimizations have been applied {len(opt_history)} times")
        print(f"   Parameters are continuously adapting to performance")
        print(f"   Check individual optimization logs for specific improvements")

    print("="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='View AI optimization status and history')
    parser.add_argument('--parameters', action='store_true', help='Show current parameters')
    parser.add_argument('--history', action='store_true', help='Show optimization history')
    parser.add_argument('--param-history', action='store_true', help='Show parameter change history')
    parser.add_argument('--performance', action='store_true', help='Show performance comparison')
    parser.add_argument('--limit', type=int, default=10, help='Limit history entries (default: 10)')
    parser.add_argument('--all', action='store_true', help='Show everything')

    args = parser.parse_args()

    # If no args, show everything
    if not any([args.parameters, args.history, args.param_history, args.performance, args.all]):
        args.all = True

    if args.all or args.parameters:
        view_current_parameters()

    if args.all or args.history:
        view_optimization_history(args.limit)

    if args.all or args.param_history:
        view_parameter_history(args.limit)

    if args.all or args.performance:
        view_performance_comparison()


if __name__ == "__main__":
    main()
