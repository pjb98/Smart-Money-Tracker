"""
AI-Powered Strategy Optimizer
Continuously analyzes trading performance and optimizes strategy using Claude AI
"""
import asyncio
from datetime import datetime
from pathlib import Path
import json
from loguru import logger
from typing import Dict, List, Any, Optional

from config import settings, setup_directories
from src.utils.logger import setup_logger
from src.optimization.pattern_detector import PatternDetector
from src.optimization.parameter_tuner import ParameterTuner


class StrategyOptimizer:
    """
    Monitors trading performance and automatically optimizes strategy using AI
    """

    def __init__(
        self,
        optimize_every_n_trades: int = 10,
        auto_apply: bool = False,
        min_priority: str = 'medium'
    ):
        """
        Initialize strategy optimizer

        Args:
            optimize_every_n_trades: Run optimization every N trades
            auto_apply: Auto-apply AI recommendations (or ask for approval)
            min_priority: Minimum priority to apply (high/medium/low)
        """
        self.logger = setup_logger(settings.log_file, settings.log_level)
        self.pattern_detector = PatternDetector()
        self.parameter_tuner = ParameterTuner()

        self.optimize_every_n_trades = optimize_every_n_trades
        self.auto_apply = auto_apply
        self.min_priority = min_priority

        self.journal_file = Path("data/trading_journal.json")
        self.optimization_log_file = Path("data/optimization_log.json")
        self.optimization_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Track state
        self.last_optimization_trade_count = 0
        self.optimization_history = []

    async def run_optimization(self, force: bool = False) -> Dict[str, Any]:
        """
        Run optimization cycle

        Args:
            force: Force optimization even if not enough trades

        Returns:
            Optimization result
        """
        self.logger.info("=" * 70)
        self.logger.info("🤖 AI STRATEGY OPTIMIZATION")
        self.logger.info("=" * 70)

        # Load trading journal
        trades = self._load_completed_trades()

        if not trades:
            self.logger.warning("No completed trades found in journal")
            return {'error': 'No trades available'}

        total_trades = len(trades)
        new_trades = total_trades - self.last_optimization_trade_count

        self.logger.info(f"Total trades: {total_trades}")
        self.logger.info(f"New trades since last optimization: {new_trades}")

        # Check if we should optimize
        if not force and new_trades < self.optimize_every_n_trades:
            self.logger.info(f"Waiting for {self.optimize_every_n_trades - new_trades} more trades before optimizing")
            return {'status': 'waiting', 'trades_until_optimization': self.optimize_every_n_trades - new_trades}

        # Get current parameters
        current_params = self.parameter_tuner.get_parameters()

        self.logger.info("\n🔍 Analyzing trading performance with Claude AI...")

        # Analyze with Claude
        analysis = await self.pattern_detector.analyze_trading_performance(
            trades=trades,
            current_parameters=current_params
        )

        if 'error' in analysis:
            self.logger.error(f"Analysis failed: {analysis['error']}")
            return analysis

        # Display analysis
        self._display_analysis(analysis)

        # Apply recommendations
        if analysis.get('recommendations'):
            self.logger.info("\n" + "=" * 70)
            self.logger.info("📝 APPLYING RECOMMENDATIONS")
            self.logger.info("=" * 70)

            if not self.auto_apply:
                # Ask for confirmation
                response = input(f"\nApply {len(analysis['recommendations'])} AI recommendations? (yes/no): ")
                if response.lower() != 'yes':
                    self.logger.info("Recommendations not applied")
                    return {
                        'status': 'skipped',
                        'analysis': analysis,
                        'applied': False
                    }

            # Apply recommendations
            application_result = self.parameter_tuner.apply_recommendations(
                recommendations=analysis['recommendations'],
                auto_apply=self.auto_apply,
                min_priority=self.min_priority
            )

            self.logger.info(f"\n✅ Applied {application_result['applied']} changes")

            # Save optimization log
            self._save_optimization_log(analysis, application_result, total_trades)

            # Update last optimization count
            self.last_optimization_trade_count = total_trades

            return {
                'status': 'completed',
                'analysis': analysis,
                'application': application_result,
                'total_trades': total_trades
            }

        else:
            self.logger.info("\nNo recommendations from AI")
            return {
                'status': 'completed',
                'analysis': analysis,
                'recommendations': 0
            }

    def _load_completed_trades(self) -> List[Dict[str, Any]]:
        """Load completed trades from journal"""
        if not self.journal_file.exists():
            return []

        try:
            with open(self.journal_file, 'r') as f:
                journal = json.load(f)

            # Get closed trades only
            closed_trades = [
                t for t in journal.get('trades', [])
                if t.get('status') == 'closed'
            ]

            return closed_trades

        except Exception as e:
            self.logger.error(f"Error loading journal: {e}")
            return []

    def _display_analysis(self, analysis: Dict[str, Any]):
        """Display Claude's analysis"""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("📊 CLAUDE'S ANALYSIS")
        self.logger.info("=" * 70)

        # Overall assessment
        if analysis.get('overall_assessment'):
            self.logger.info(f"\n{analysis['overall_assessment']}")

        # Patterns
        if analysis.get('patterns'):
            self.logger.info(f"\n🔍 PATTERNS IDENTIFIED ({len(analysis['patterns'])})")
            for pattern in analysis['patterns']:
                significance = pattern.get('significance', 'medium').upper()
                emoji = '🔴' if significance == 'HIGH' else '🟡' if significance == 'MEDIUM' else '⚪'

                self.logger.info(f"\n{emoji} {pattern.get('description', 'N/A')}")
                self.logger.info(f"   Category: {pattern.get('category', 'N/A')}")
                self.logger.info(f"   Metric: {pattern.get('metric', 'N/A')} = {pattern.get('current_value', 'N/A')}")
                self.logger.info(f"   Significance: {significance}")

        # Recommendations
        if analysis.get('recommendations'):
            self.logger.info(f"\n💡 RECOMMENDATIONS ({len(analysis['recommendations'])})")
            for i, rec in enumerate(analysis['recommendations'], 1):
                priority = rec.get('priority', 'medium').upper()
                emoji = '🔴' if priority == 'HIGH' else '🟡' if priority == 'MEDIUM' else '⚪'

                self.logger.info(f"\n{emoji} Recommendation {i} [{priority}]")
                self.logger.info(f"   Category: {rec.get('category', 'N/A')}")
                self.logger.info(f"   Parameter: {rec.get('parameter', 'N/A')}")
                self.logger.info(f"   Change: {rec.get('current_value', 'N/A')} → {rec.get('recommended_value', 'N/A')}")
                self.logger.info(f"   Reason: {rec.get('reasoning', 'N/A')}")
                self.logger.info(f"   Expected: {rec.get('expected_impact', 'N/A')}")
                if rec.get('risk'):
                    self.logger.info(f"   ⚠️  Risk: {rec['risk']}")

        # Priority actions
        if analysis.get('priority_actions'):
            self.logger.info(f"\n⚡ PRIORITY ACTIONS")
            for i, action in enumerate(analysis['priority_actions'], 1):
                self.logger.info(f"   {i}. {action}")

        # Cautions
        if analysis.get('cautions'):
            self.logger.info(f"\n⚠️  CAUTIONS")
            for caution in analysis['cautions']:
                self.logger.info(f"   - {caution}")

    def _save_optimization_log(
        self,
        analysis: Dict[str, Any],
        application_result: Dict[str, Any],
        total_trades: int
    ):
        """Save optimization log entry"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'total_trades': total_trades,
            'analysis': analysis,
            'application': application_result
        }

        # Load existing log
        optimization_log = []
        if self.optimization_log_file.exists():
            try:
                with open(self.optimization_log_file, 'r') as f:
                    optimization_log = json.load(f)
            except:
                pass

        # Append new entry
        optimization_log.append(log_entry)

        # Keep only last 50 optimizations
        if len(optimization_log) > 50:
            optimization_log = optimization_log[-50:]

        # Save
        try:
            with open(self.optimization_log_file, 'w') as f:
                json.dump(optimization_log, f, indent=2, default=str)
            self.logger.info(f"\n📝 Optimization log saved to {self.optimization_log_file}")
        except Exception as e:
            self.logger.error(f"Error saving optimization log: {e}")

    async def monitor_and_optimize(self, check_interval_seconds: int = 300):
        """
        Continuously monitor and optimize

        Args:
            check_interval_seconds: How often to check for new trades (default: 5 minutes)
        """
        self.logger.info("=" * 70)
        self.logger.info("🤖 CONTINUOUS AI OPTIMIZATION MONITOR")
        self.logger.info("=" * 70)
        self.logger.info(f"Optimize every: {self.optimize_every_n_trades} trades")
        self.logger.info(f"Auto-apply: {self.auto_apply}")
        self.logger.info(f"Min priority: {self.min_priority}")
        self.logger.info(f"Check interval: {check_interval_seconds}s")
        self.logger.info("=" * 70)

        try:
            while True:
                # Wait
                await asyncio.sleep(check_interval_seconds)

                # Check if optimization needed
                trades = self._load_completed_trades()
                total_trades = len(trades)
                new_trades = total_trades - self.last_optimization_trade_count

                if new_trades >= self.optimize_every_n_trades:
                    self.logger.info(f"\n🔔 {new_trades} new trades - triggering optimization...")
                    await self.run_optimization()
                else:
                    self.logger.debug(f"Checked: {new_trades}/{self.optimize_every_n_trades} trades")

        except KeyboardInterrupt:
            self.logger.info("\nStopping optimizer...")
        except Exception as e:
            self.logger.error(f"Optimizer error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        await self.pattern_detector.close()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='AI-Powered Strategy Optimizer')
    parser.add_argument('--run-once', action='store_true', help='Run optimization once and exit')
    parser.add_argument('--force', action='store_true', help='Force optimization even with few trades')
    parser.add_argument('--monitor', action='store_true', help='Continuously monitor and optimize')
    parser.add_argument('--every', type=int, default=10, help='Optimize every N trades (default: 10)')
    parser.add_argument('--auto-apply', action='store_true', help='Auto-apply recommendations without asking')
    parser.add_argument('--min-priority', type=str, default='medium', choices=['high', 'medium', 'low'],
                        help='Minimum priority to apply (default: medium)')
    parser.add_argument('--check-interval', type=int, default=300, help='Check interval in seconds (default: 300)')
    parser.add_argument('--view-history', action='store_true', help='View optimization history')
    parser.add_argument('--rollback', action='store_true', help='Rollback to previous parameters')

    args = parser.parse_args()

    setup_directories()

    optimizer = StrategyOptimizer(
        optimize_every_n_trades=args.every,
        auto_apply=args.auto_apply,
        min_priority=args.min_priority
    )

    if args.view_history:
        # View optimization history
        history = optimizer.parameter_tuner.get_history(limit=10)
        print("\n" + "=" * 70)
        print("OPTIMIZATION HISTORY")
        print("=" * 70)
        for entry in history:
            print(f"\n{entry['timestamp']}")
            print(f"Reason: {entry['reason']}")
        print("=" * 70)
        return

    if args.rollback:
        # Rollback parameters
        print("\n" + "=" * 70)
        print("⏮️  ROLLBACK TO PREVIOUS PARAMETERS")
        print("=" * 70)
        response = input("\nAre you sure? (yes/no): ")
        if response.lower() == 'yes':
            success = optimizer.parameter_tuner.rollback_to_previous()
            if success:
                print("\n✅ Parameters rolled back successfully")
            else:
                print("\n❌ Rollback failed")
        return

    if args.monitor:
        # Continuous monitoring
        await optimizer.monitor_and_optimize(check_interval_seconds=args.check_interval)
    else:
        # Run once
        result = await optimizer.run_optimization(force=args.force)

        if result.get('status') == 'completed':
            print("\n" + "=" * 70)
            print("✅ OPTIMIZATION COMPLETE")
            print("=" * 70)
            print(f"Applied: {result.get('application', {}).get('applied', 0)} changes")
            print("\nView updated parameters:")
            print("  cat data/strategy_parameters.json")
            print("\nView optimization log:")
            print("  cat data/optimization_log.json")
        elif result.get('status') == 'waiting':
            print(f"\nWaiting for {result['trades_until_optimization']} more trades")


if __name__ == "__main__":
    asyncio.run(main())
