"""
Trading Journal Viewer - Review Paper Trading Performance
Analyze trades, track performance, and learn from results
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import argparse


class TradingJournalViewer:
    """View and analyze trading journal"""

    def __init__(self, journal_file: str = "data/trading_journal.json"):
        """Initialize journal viewer"""
        self.journal_file = Path(journal_file)
        self.journal_data = self._load_journal()

    def _load_journal(self) -> Dict[str, Any]:
        """Load journal from disk"""
        if not self.journal_file.exists():
            print(f"❌ Trading journal not found: {self.journal_file}")
            print("   Start paper trading first to generate journal")
            return {}

        try:
            with open(self.journal_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading journal: {e}")
            return {}

    def display_summary(self):
        """Display performance summary"""
        if not self.journal_data:
            return

        print("\n" + "="*100)
        print("TRADING PERFORMANCE SUMMARY")
        print("="*100)

        initial = self.journal_data.get('initial_capital', 0)
        current = self.journal_data.get('current_capital', 0)
        total_pnl = self.journal_data.get('total_pnl', 0)
        total_trades = self.journal_data.get('total_trades', 0)
        winning = self.journal_data.get('winning_trades', 0)
        losing = self.journal_data.get('losing_trades', 0)
        win_rate = self.journal_data.get('win_rate', 0)

        return_pct = ((current / initial) - 1) * 100 if initial > 0 else 0

        print(f"\n💰 Capital")
        print(f"   Initial:  ${initial:,.2f}")
        print(f"   Current:  ${current:,.2f}")
        print(f"   P&L:      ${total_pnl:,.2f} ({return_pct:+.2f}%)")

        print(f"\n📊 Trading Statistics")
        print(f"   Total Trades:   {total_trades}")
        print(f"   Winning Trades: {winning} ({winning/total_trades*100 if total_trades > 0 else 0:.1f}%)")
        print(f"   Losing Trades:  {losing} ({losing/total_trades*100 if total_trades > 0 else 0:.1f}%)")
        print(f"   Win Rate:       {win_rate*100:.1f}%")

        # Calculate more metrics
        if total_trades > 0:
            closed_positions = self.journal_data.get('closed_positions', [])
            if closed_positions:
                wins = [p['realized_pnl'] for p in closed_positions if p['realized_pnl'] > 0]
                losses = [p['realized_pnl'] for p in closed_positions if p['realized_pnl'] < 0]

                avg_win = sum(wins) / len(wins) if wins else 0
                avg_loss = sum(losses) / len(losses) if losses else 0
                profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0

                print(f"\n💵 P&L Metrics")
                print(f"   Average Win:    ${avg_win:,.2f}")
                print(f"   Average Loss:   ${avg_loss:,.2f}")
                print(f"   Profit Factor:  {profit_factor:.2f}x")

                # Best and worst trades
                best_trade = max(closed_positions, key=lambda x: x['realized_pnl'])
                worst_trade = min(closed_positions, key=lambda x: x['realized_pnl'])

                print(f"\n🏆 Best Trade:  {best_trade['symbol']} (${best_trade['realized_pnl']:,.2f})")
                print(f"   💔 Worst Trade: {worst_trade['symbol']} (${worst_trade['realized_pnl']:,.2f})")

        print("="*100)

    def list_trades(self, limit: int = 20, filter_status: str = None):
        """List all trades"""
        if not self.journal_data:
            return

        closed_positions = self.journal_data.get('closed_positions', [])

        if not closed_positions:
            print("\n📭 No closed trades yet")
            return

        # Filter if needed
        if filter_status:
            if filter_status == 'wins':
                closed_positions = [p for p in closed_positions if p['realized_pnl'] > 0]
            elif filter_status == 'losses':
                closed_positions = [p for p in closed_positions if p['realized_pnl'] < 0]

        # Sort by entry time (most recent first)
        closed_positions.sort(key=lambda x: x.get('entry_time', ''), reverse=True)

        print("\n" + "="*100)
        print("TRADING HISTORY")
        print("="*100)
        print(f"{'#':<4} {'Symbol':<10} {'Type':<12} {'Entry':<20} {'Exit':<20} {'Return':<10} {'P&L':<12}")
        print("-"*100)

        for i, trade in enumerate(closed_positions[:limit], 1):
            symbol = trade['symbol'][:10]
            token_type = trade.get('token_type', 'unknown')[:12]
            entry_time = trade.get('entry_time', '')[:19] if trade.get('entry_time') else 'N/A'
            exit_time = trade.get('exit_time', '')[:19] if trade.get('exit_time') else 'N/A'

            entry_price = trade.get('entry_price', 0)
            exit_price = trade.get('current_price', 0)
            pnl = trade.get('realized_pnl', 0)

            return_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else 0

            # Color coding
            if pnl > 0:
                return_str = f"+{return_pct:.1f}%"
                pnl_str = f"+${pnl:.2f}"
            else:
                return_str = f"{return_pct:.1f}%"
                pnl_str = f"-${abs(pnl):.2f}"

            print(f"{i:<4} {symbol:<10} {token_type:<12} {entry_time:<20} {exit_time:<20} {return_str:<10} {pnl_str:<12}")

        print("="*100)
        print(f"Showing {min(limit, len(closed_positions))} of {len(closed_positions)} trades")

    def view_trade_detail(self, index: int):
        """View detailed trade information"""
        if not self.journal_data:
            return

        closed_positions = self.journal_data.get('closed_positions', [])

        if index < 1 or index > len(closed_positions):
            print(f"❌ Invalid trade index: {index}")
            return

        # Sort by entry time to match list display
        closed_positions.sort(key=lambda x: x.get('entry_time', ''), reverse=True)
        trade = closed_positions[index - 1]

        print("\n" + "="*100)
        print("TRADE DETAIL")
        print("="*100)

        print(f"\n📝 Basic Information")
        print(f"   Symbol:       {trade['symbol']}")
        print(f"   Token Type:   {trade.get('token_type', 'unknown')}")
        print(f"   Address:      {trade['token_address']}")
        print(f"   Recommendation: {trade.get('recommendation', 'N/A')} ({trade.get('confidence', 'N/A')} confidence)")
        print(f"   Risk Score:   {trade.get('risk_score', 'N/A')}/10")

        print(f"\n💰 Position Details")
        print(f"   Position Size: ${trade.get('position_size_usd', 0):.2f}")
        print(f"   Entry Strategy: {trade.get('entry_strategy', 'N/A')}")
        print(f"   Entry Price:  ${trade.get('entry_price', 0):.6f}")
        print(f"   Exit Price:   ${trade.get('current_price', 0):.6f}")
        print(f"   Stop Loss:    ${trade.get('stop_loss', 0):.6f}")

        print(f"\n📈 Performance")
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('current_price', 0)
        pnl = trade.get('realized_pnl', 0)
        return_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else 0

        if pnl > 0:
            print(f"   Return:       🟢 +{return_pct:.2f}%")
            print(f"   P&L:          🟢 +${pnl:.2f}")
        else:
            print(f"   Return:       🔴 {return_pct:.2f}%")
            print(f"   P&L:          🔴 -${abs(pnl):.2f}")

        highest = trade.get('highest_price', 0)
        lowest = trade.get('lowest_price', 0)
        max_drawdown = trade.get('max_drawdown', 0)

        if highest and entry_price:
            max_gain_pct = ((highest / entry_price) - 1) * 100
            print(f"   Peak Gain:    +{max_gain_pct:.2f}%")
        if lowest and entry_price:
            max_loss_pct = ((lowest / entry_price) - 1) * 100
            print(f"   Max Drawdown: {max_loss_pct:.2f}%")

        print(f"\n⏱️  Timing")
        entry_time = trade.get('entry_time', 'N/A')
        exit_time = trade.get('exit_time', 'N/A')
        print(f"   Migration:    {trade.get('migration_time', 'N/A')}")
        print(f"   Entry:        {entry_time}")
        print(f"   Exit:         {exit_time}")

        if entry_time != 'N/A' and exit_time != 'N/A':
            try:
                entry_dt = datetime.fromisoformat(entry_time)
                exit_dt = datetime.fromisoformat(exit_time)
                duration = exit_dt - entry_dt
                hours = duration.total_seconds() / 3600
                print(f"   Duration:     {hours:.1f} hours")
            except:
                pass

        print(f"\n🎯 Exit Information")
        print(f"   Exit Reason:  {trade.get('exit_reason', 'N/A')}")

        # Partial exits
        partial_exits = trade.get('partial_exits', [])
        if partial_exits:
            print(f"   Partial Exits: {len(partial_exits)}")
            for i, exit_info in enumerate(partial_exits, 1):
                exit_pnl = exit_info.get('pnl', 0)
                exit_price_partial = exit_info.get('price', 0)
                exit_pct = exit_info.get('size_pct', 0) * 100
                print(f"     Exit {i}: {exit_pct:.0f}% at ${exit_price_partial:.6f} (P&L: ${exit_pnl:.2f})")

        # Notes
        notes = trade.get('notes', [])
        if notes:
            print(f"\n📋 Notes")
            for note in notes:
                # Truncate long notes
                if len(note) > 100:
                    print(f"   {note[:100]}...")
                else:
                    print(f"   {note}")

        print("="*100)

    def analyze_patterns(self):
        """Analyze trading patterns"""
        if not self.journal_data:
            return

        closed_positions = self.journal_data.get('closed_positions', [])

        if not closed_positions:
            print("\n📭 No trades to analyze yet")
            return

        print("\n" + "="*100)
        print("TRADING PATTERN ANALYSIS")
        print("="*100)

        # Analyze by token type
        tech_tokens = [p for p in closed_positions if p.get('token_type') == 'tech']
        viral_memes = [p for p in closed_positions if p.get('token_type') == 'viral_meme']

        print(f"\n📊 Performance by Token Type")

        if tech_tokens:
            tech_wins = len([p for p in tech_tokens if p['realized_pnl'] > 0])
            tech_win_rate = tech_wins / len(tech_tokens) * 100
            tech_avg_pnl = sum(p['realized_pnl'] for p in tech_tokens) / len(tech_tokens)
            print(f"   Tech Tokens:  {len(tech_tokens)} trades | {tech_win_rate:.1f}% win rate | Avg P&L: ${tech_avg_pnl:.2f}")

        if viral_memes:
            meme_wins = len([p for p in viral_memes if p['realized_pnl'] > 0])
            meme_win_rate = meme_wins / len(viral_memes) * 100
            meme_avg_pnl = sum(p['realized_pnl'] for p in viral_memes) / len(viral_memes)
            print(f"   Viral Memes:  {len(viral_memes)} trades | {meme_win_rate:.1f}% win rate | Avg P&L: ${meme_avg_pnl:.2f}")

        # Analyze by entry strategy
        print(f"\n🎯 Performance by Entry Strategy")
        strategies = {}
        for p in closed_positions:
            strategy = p.get('entry_strategy', 'unknown')
            if strategy not in strategies:
                strategies[strategy] = []
            strategies[strategy].append(p)

        for strategy, trades in strategies.items():
            wins = len([p for p in trades if p['realized_pnl'] > 0])
            win_rate = wins / len(trades) * 100 if trades else 0
            avg_pnl = sum(p['realized_pnl'] for p in trades) / len(trades) if trades else 0
            print(f"   {strategy.title():15} {len(trades)} trades | {win_rate:.1f}% win rate | Avg P&L: ${avg_pnl:.2f}")

        # Analyze by confidence level
        print(f"\n💪 Performance by Confidence Level")
        confidences = {}
        for p in closed_positions:
            conf = p.get('confidence', 'UNKNOWN')
            if conf not in confidences:
                confidences[conf] = []
            confidences[conf].append(p)

        for conf, trades in sorted(confidences.items()):
            wins = len([p for p in trades if p['realized_pnl'] > 0])
            win_rate = wins / len(trades) * 100 if trades else 0
            avg_pnl = sum(p['realized_pnl'] for p in trades) / len(trades) if trades else 0
            print(f"   {conf:10} {len(trades)} trades | {win_rate:.1f}% win rate | Avg P&L: ${avg_pnl:.2f}")

        # Exit reasons
        print(f"\n🚪 Exit Reasons")
        exit_reasons = {}
        for p in closed_positions:
            reason = p.get('exit_reason', 'Unknown')
            if reason not in exit_reasons:
                exit_reasons[reason] = 0
            exit_reasons[reason] += 1

        for reason, count in sorted(exit_reasons.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(closed_positions) * 100
            print(f"   {reason:30} {count} ({pct:.1f}%)")

        print("="*100)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='View trading journal and performance')
    parser.add_argument('--summary', action='store_true', help='Show performance summary')
    parser.add_argument('--list', action='store_true', help='List all trades')
    parser.add_argument('--view', type=int, help='View trade detail by index')
    parser.add_argument('--wins', action='store_true', help='Show only winning trades')
    parser.add_argument('--losses', action='store_true', help='Show only losing trades')
    parser.add_argument('--analyze', action='store_true', help='Analyze trading patterns')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of trades shown')

    args = parser.parse_args()

    viewer = TradingJournalViewer()

    if args.summary or (not any([args.list, args.view, args.wins, args.losses, args.analyze])):
        viewer.display_summary()

    if args.list:
        viewer.list_trades(limit=args.limit)

    if args.wins:
        viewer.list_trades(limit=args.limit, filter_status='wins')

    if args.losses:
        viewer.list_trades(limit=args.limit, filter_status='losses')

    if args.view:
        viewer.view_trade_detail(args.view)

    if args.analyze:
        viewer.analyze_patterns()

    if not viewer.journal_data:
        print("\n💡 Start paper trading to generate journal:")
        print("   python paper_trade_monitor.py")


if __name__ == "__main__":
    main()
