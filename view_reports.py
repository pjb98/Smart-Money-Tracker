"""
Report Viewer - Review Historical Investment Decisions
Browse and analyze all past token analysis reports
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import argparse


class ReportViewer:
    """View and analyze historical investment reports"""

    def __init__(self, reports_dir: str = "data/reports"):
        """Initialize report viewer"""
        self.reports_dir = Path(reports_dir)

    def list_reports(self, limit: int = 20, sort_by: str = 'date') -> List[Dict[str, Any]]:
        """
        List available reports

        Args:
            limit: Maximum number of reports to show
            sort_by: Sort by 'date', 'symbol', or 'recommendation'

        Returns:
            List of report summaries
        """
        if not self.reports_dir.exists():
            print(f"❌ Reports directory not found: {self.reports_dir}")
            return []

        # Find all JSON report files
        report_files = list(self.reports_dir.glob("*.json"))

        if not report_files:
            print(f"📭 No reports found in {self.reports_dir}")
            return []

        reports = []
        for filepath in report_files:
            try:
                with open(filepath, 'r') as f:
                    report = json.load(f)
                    reports.append({
                        'filepath': filepath,
                        'report_id': report.get('report_id', 'Unknown'),
                        'symbol': report.get('symbol', 'UNKNOWN'),
                        'name': report.get('name', 'Unknown Token'),
                        'generated_at': report.get('generated_at', ''),
                        'recommendation': report.get('executive_summary', {}).get('recommendation', 'UNKNOWN'),
                        'confidence': report.get('executive_summary', {}).get('confidence', 'UNKNOWN'),
                        'risk_score': report.get('executive_summary', {}).get('risk_score', 0)
                    })
            except Exception as e:
                print(f"⚠️ Error loading {filepath.name}: {e}")

        # Sort reports
        if sort_by == 'date':
            reports.sort(key=lambda x: x['generated_at'], reverse=True)
        elif sort_by == 'symbol':
            reports.sort(key=lambda x: x['symbol'])
        elif sort_by == 'recommendation':
            reports.sort(key=lambda x: x['recommendation'])

        return reports[:limit]

    def display_report_list(self, reports: List[Dict[str, Any]]):
        """Display list of reports"""
        print("\n" + "="*100)
        print("INVESTMENT DECISION REPORTS")
        print("="*100)
        print(f"{'#':<4} {'Symbol':<10} {'Recommendation':<15} {'Confidence':<12} {'Risk':<6} {'Generated':<20}")
        print("-"*100)

        for i, report in enumerate(reports, 1):
            symbol = report['symbol'][:10]
            rec = report['recommendation']
            conf = report['confidence']
            risk = f"{report['risk_score']}/10"
            generated = report['generated_at'][:19] if report['generated_at'] else 'Unknown'

            # Color coding
            if rec == 'BUY':
                rec_display = f"🟢 {rec}"
            elif rec == 'AVOID':
                rec_display = f"🔴 {rec}"
            else:
                rec_display = f"🟡 {rec}"

            print(f"{i:<4} {symbol:<10} {rec_display:<15} {conf:<12} {risk:<6} {generated:<20}")

        print("="*100)
        print(f"\nTotal: {len(reports)} reports")

    def view_report(self, report_id: str = None, index: int = None):
        """
        View detailed report

        Args:
            report_id: Specific report ID to view
            index: Index from list (1-based)
        """
        if index is not None:
            reports = self.list_reports(limit=1000)
            if index < 1 or index > len(reports):
                print(f"❌ Invalid index: {index}")
                return
            filepath = reports[index - 1]['filepath']
        elif report_id:
            filepath = self.reports_dir / f"{report_id}.json"
            if not filepath.exists():
                print(f"❌ Report not found: {report_id}")
                return
        else:
            print("❌ Must provide either report_id or index")
            return

        # Load and display report
        try:
            with open(filepath, 'r') as f:
                report = json.load(f)
            self._display_full_report(report)
        except Exception as e:
            print(f"❌ Error loading report: {e}")

    def _display_full_report(self, report: Dict[str, Any]):
        """Display full report details"""

        print("\n" + "="*100)
        print("COMPREHENSIVE INVESTMENT ANALYSIS REPORT")
        print("="*100)
        print(f"")
        print(f"Token: {report['name']} ({report['symbol']})")
        print(f"Address: {report['token_address']}")
        print(f"Migration Time: {report['migration_time']}")
        print(f"Report ID: {report['report_id']}")
        print(f"Generated: {report['generated_at']}")
        print(f"")

        # EXECUTIVE SUMMARY
        summary = report.get('executive_summary', {})
        print("="*100)
        print("📊 EXECUTIVE SUMMARY")
        print("="*100)
        print(summary.get('one_line_summary', 'No summary available'))
        print(f"")
        print(f"Recommendation: {summary.get('recommendation', 'UNKNOWN')} ({summary.get('confidence', 'UNKNOWN')} confidence)")
        print(f"Risk Score: {summary.get('risk_score', 'N/A')}/10")
        print(f"Opportunity Score: {summary.get('opportunity_score', 'N/A')}/10")
        print(f"Predicted 24h Return: {summary.get('predicted_return_24h', 0)*100:.1f}%")
        print(f"Initial Liquidity: {summary.get('initial_liquidity_sol', 0):.2f} SOL")
        print(f"Holder Count: {summary.get('holder_count', 0)}")
        print(f"")

        # DECISION & RATIONALE
        decision = report.get('decision', {})
        print("="*100)
        print("💡 DECISION & RATIONALE")
        print("="*100)
        print(f"Action: {decision.get('action', 'UNKNOWN')}")
        print(f"Confidence: {decision.get('confidence', 'UNKNOWN')}")
        print(f"Position Size: {decision.get('position_size_recommendation', 'N/A')}")
        print(f"Entry Strategy: {decision.get('entry_strategy', 'N/A')}")
        print(f"Exit Strategy: {decision.get('exit_strategy', 'N/A')}")
        print(f"")

        # Show Claude's detailed reasoning if available
        if decision.get('reasoning'):
            print("Detailed Reasoning:")
            print("-"*100)
            # Show first 500 chars of reasoning
            reasoning = decision['reasoning']
            if len(reasoning) > 500:
                print(reasoning[:500] + "...")
                print("(See full report file for complete reasoning)")
            else:
                print(reasoning)
            print(f"")

        # KEY METRICS
        metrics = report.get('key_metrics', {})
        print("="*100)
        print("📈 KEY METRICS ANALYSIS")
        print("="*100)

        # Liquidity
        liq = metrics.get('liquidity', {})
        print(f"Liquidity: {liq.get('rating', 'N/A')} ({liq.get('initial_sol', 0):.2f} SOL)")
        print(f"  {liq.get('analysis', 'No analysis')}")
        print(f"")

        # Holder Distribution
        holders = metrics.get('holder_distribution', {})
        print(f"Holder Distribution: {holders.get('rating', 'N/A')}")
        print(f"  {holders.get('analysis', 'No analysis')}")
        print(f"")

        # Pre-migration
        pre_mig = metrics.get('pre_migration_performance', {})
        if pre_mig.get('available'):
            print(f"Pre-Migration Performance: {pre_mig.get('rating', 'N/A')}")
            print(f"  {pre_mig.get('analysis', 'No analysis')}")
            print(f"")

        # Wallet Quality
        wallet_qual = metrics.get('wallet_quality', {})
        if wallet_qual.get('available'):
            print(f"Wallet Quality: {wallet_qual.get('rating', 'N/A')}")
            print(f"  {wallet_qual.get('analysis', 'No analysis')}")
            print(f"")

        # Social Presence
        social = metrics.get('social_presence', {})
        if social.get('available'):
            print(f"Social Presence: {social.get('rating', 'N/A')}")
            print(f"  {social.get('analysis', 'No analysis')}")
            print(f"")

        # RISK ASSESSMENT
        risk_assessment = report.get('risk_assessment', {})
        print("="*100)
        print("⚠️  RISK ASSESSMENT")
        print("="*100)
        print(f"Overall Risk: {risk_assessment.get('risk_level', 'UNKNOWN')} ({risk_assessment.get('overall_risk_score', 'N/A')}/10)")
        print(f"Identified Risks: {risk_assessment.get('risk_count', 0)} total, {risk_assessment.get('critical_risks', 0)} critical")
        print(f"")

        identified_risks = risk_assessment.get('identified_risks', [])
        if identified_risks:
            print("Major Risks:")
            for risk in identified_risks:
                print(f"  [{risk['severity']}] {risk['type']}: {risk['description']}")
            print(f"")

        # RED FLAGS
        red_flags = report.get('red_flags', [])
        if red_flags:
            print("="*100)
            print("🚨 RED FLAGS")
            print("="*100)
            for flag in red_flags:
                print(f"[{flag['severity']}] {flag['flag']}")
                print(f"    {flag['detail']}")
            print(f"")

        # OPPORTUNITY ANALYSIS
        opp = report.get('opportunity_analysis', {})
        print("="*100)
        print("🎯 OPPORTUNITY ANALYSIS")
        print("="*100)
        print(f"Overall Opportunity: {opp.get('opportunity_level', 'UNKNOWN')} ({opp.get('overall_opportunity_score', 'N/A')}/10)")
        print(f"Predicted Return: {opp.get('predicted_return_24h', 0):.1f}%")
        print(f"")

        opportunities = opp.get('identified_opportunities', [])
        if opportunities:
            print("Key Opportunities:")
            for opportunity in opportunities:
                print(f"  [{opportunity['strength']}] {opportunity['type']}: {opportunity['description']}")
            print(f"")

        # ACTION PLAN
        action_plan = report.get('action_plan', {})
        print("="*100)
        print("🎬 ACTION PLAN")
        print("="*100)
        print("Immediate Actions:")
        for action in action_plan.get('immediate_actions', []):
            print(f"  • {action}")
        print(f"")
        print(f"Monitoring Plan: {action_plan.get('monitoring_plan', 'N/A')}")
        print(f"Re-evaluation: {action_plan.get('revaluation_time', 'N/A')}")
        print(f"")

        print("="*100)
        print("END OF REPORT")
        print("="*100)
        print(f"\nFull report saved at: {report['report_id']}.json and .txt")

    def filter_reports(
        self,
        recommendation: str = None,
        min_risk: int = None,
        max_risk: int = None,
        confidence: str = None
    ) -> List[Dict[str, Any]]:
        """Filter reports by criteria"""
        reports = self.list_reports(limit=1000)

        filtered = reports
        if recommendation:
            filtered = [r for r in filtered if r['recommendation'] == recommendation.upper()]
        if min_risk is not None:
            filtered = [r for r in filtered if r['risk_score'] >= min_risk]
        if max_risk is not None:
            filtered = [r for r in filtered if r['risk_score'] <= max_risk]
        if confidence:
            filtered = [r for r in filtered if r['confidence'] == confidence.upper()]

        return filtered

    def statistics(self):
        """Show statistics across all reports"""
        reports = self.list_reports(limit=1000)

        if not reports:
            print("No reports to analyze")
            return

        total = len(reports)
        buy_count = len([r for r in reports if r['recommendation'] == 'BUY'])
        avoid_count = len([r for r in reports if r['recommendation'] == 'AVOID'])
        hold_count = len([r for r in reports if r['recommendation'] == 'HOLD'])

        high_conf = len([r for r in reports if r['confidence'] == 'HIGH'])
        med_conf = len([r for r in reports if r['confidence'] == 'MEDIUM'])
        low_conf = len([r for r in reports if r['confidence'] == 'LOW'])

        avg_risk = sum(r['risk_score'] for r in reports) / total

        print("\n" + "="*100)
        print("📊 REPORT STATISTICS")
        print("="*100)
        print(f"Total Reports: {total}")
        print(f"")
        print(f"Recommendations:")
        print(f"  🟢 BUY:   {buy_count} ({buy_count/total*100:.1f}%)")
        print(f"  🔴 AVOID: {avoid_count} ({avoid_count/total*100:.1f}%)")
        print(f"  🟡 HOLD:  {hold_count} ({hold_count/total*100:.1f}%)")
        print(f"")
        print(f"Confidence Levels:")
        print(f"  HIGH:   {high_conf} ({high_conf/total*100:.1f}%)")
        print(f"  MEDIUM: {med_conf} ({med_conf/total*100:.1f}%)")
        print(f"  LOW:    {low_conf} ({low_conf/total*100:.1f}%)")
        print(f"")
        print(f"Average Risk Score: {avg_risk:.1f}/10")
        print("="*100)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='View investment decision reports')
    parser.add_argument('--list', action='store_true', help='List all reports')
    parser.add_argument('--view', type=int, help='View report by index')
    parser.add_argument('--filter', choices=['BUY', 'AVOID', 'HOLD'], help='Filter by recommendation')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of reports shown')

    args = parser.parse_args()

    viewer = ReportViewer()

    if args.stats:
        viewer.statistics()
    elif args.view:
        viewer.view_report(index=args.view)
    elif args.filter:
        reports = viewer.filter_reports(recommendation=args.filter)
        viewer.display_report_list(reports[:args.limit])
    elif args.list or True:  # Default to list
        reports = viewer.list_reports(limit=args.limit)
        viewer.display_report_list(reports)
        print(f"\nUsage:")
        print(f"  python view_reports.py --list           # List reports")
        print(f"  python view_reports.py --view 1         # View report #1")
        print(f"  python view_reports.py --filter BUY     # Show only BUY recommendations")
        print(f"  python view_reports.py --stats          # Show statistics")


if __name__ == "__main__":
    main()
