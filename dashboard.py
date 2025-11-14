"""
Comprehensive Trading Dashboard v2.0
Modern, user-friendly interface combining all features:
- Trading Journal
- AI Trends & Patterns
- Cost Optimization
- Live Predictions
- Strategy Parameters
"""
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime, timedelta
from loguru import logger
from monitor_manager import MonitorManager


class ComprehensiveDashboard:
    """All-in-one trading dashboard"""

    def __init__(self, port: int = 8050):
        """Initialize comprehensive dashboard"""
        self.port = port
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = "PumpFun Trading Dashboard"

        # Data paths
        self.results_dir = Path("data/results")
        self.journal_file = Path("data/trading_journal.json")
        self.params_file = Path("data/strategy_parameters.json")
        self.opt_log_file = Path("data/optimization_log.json")
        self.analytics_db = Path("data/analytics.db")
        self.smart_wallets_file = Path("data/smart_money_wallets.json")
        self.cabal_groups_file = Path("data/cabal_groups.json")
        self.indicator_weights_file = Path("data/indicator_weights.json")

        # Monitor manager
        self.monitor_manager = MonitorManager()

        self._setup_layout()
        self._setup_callbacks()

        logger.info("Comprehensive dashboard initialized")

    def _load_predictions(self) -> pd.DataFrame:
        """Load prediction results"""
        results = []

        if not self.results_dir.exists():
            return pd.DataFrame()

        for json_file in self.results_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    results.append(data)
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")

        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # Extract nested data
        if 'prediction' in df.columns:
            df['predicted_return'] = df['prediction'].apply(
                lambda x: x.get('prediction', 0) if isinstance(x, dict) else 0
            )

        if 'claude_analysis' in df.columns:
            df['recommendation'] = df['claude_analysis'].apply(
                lambda x: x.get('recommendation', 'UNKNOWN') if isinstance(x, dict) else 'UNKNOWN'
            )
            df['risk_score'] = df['claude_analysis'].apply(
                lambda x: x.get('risk_score', 5) if isinstance(x, dict) else 5
            )
            df['confidence'] = df['claude_analysis'].apply(
                lambda x: x.get('confidence', 'MEDIUM') if isinstance(x, dict) else 'MEDIUM'
            )

        return df

    def _load_trading_journal(self) -> dict:
        """Load trading journal"""
        if not self.journal_file.exists():
            return {}

        try:
            with open(self.journal_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading journal: {e}")
            return {}

    def _load_strategy_params(self) -> dict:
        """Load strategy parameters"""
        if not self.params_file.exists():
            return {}

        try:
            with open(self.params_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _load_optimization_log(self) -> list:
        """Load optimization history"""
        if not self.opt_log_file.exists():
            return []

        try:
            with open(self.opt_log_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def _load_cost_stats(self) -> dict:
        """Load cost optimization stats from database"""
        try:
            from src.storage.datastore import DataStore
            store = DataStore(str(self.analytics_db))
            stats = store.get_stats()
            store.close()
            return stats
        except Exception as e:
            logger.error(f"Error loading cost stats: {e}")
            return {}

    def _setup_layout(self):
        """Setup modern dashboard layout"""

        # Modern color scheme
        colors = {
            'background': '#0e1117',
            'card': '#1e2130',
            'text': '#ffffff',
            'accent': '#00d4ff',
            'success': '#00ff9f',
            'warning': '#ffd700',
            'danger': '#ff4444'
        }

        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("🚀 PumpFun Trading Dashboard",
                       style={'color': colors['accent'], 'margin': '0', 'padding': '20px'}),
                html.P("Real-time Trading Analytics & AI Intelligence",
                      style={'color': colors['text'], 'margin': '0', 'padding': '0 20px 20px'}),
            ], style={'backgroundColor': colors['background']}),

            # Auto-refresh
            dcc.Interval(
                id='interval-component',
                interval=10*1000,  # 10 seconds
                n_intervals=0
            ),

            # Main content
            html.Div([
                dcc.Tabs(id='tabs', value='overview', children=[
                    dcc.Tab(label='📊 Overview', value='overview',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='🔥 Smart Wallets', value='smart_wallets',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='📡 Token Monitor', value='token_monitor',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='💼 Trading Journal', value='journal',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='🤖 AI Patterns', value='ai',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='💰 Cost Optimization', value='cost',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='🎯 Live Predictions', value='predictions',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='⚙️ Strategy', value='strategy',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                    dcc.Tab(label='🎮 Command Center', value='command_center',
                           style={'backgroundColor': colors['card'], 'color': colors['text']},
                           selected_style={'backgroundColor': colors['accent'], 'color': colors['background']}),
                ], style={'backgroundColor': colors['background']}),

                html.Div(id='tab-content', style={'padding': '20px', 'backgroundColor': colors['background']})
            ], style={'backgroundColor': colors['background'], 'minHeight': '100vh'})
        ], style={'fontFamily': 'Arial, sans-serif', 'backgroundColor': colors['background']})

    def _setup_callbacks(self):
        """Setup dashboard callbacks"""

        @self.app.callback(
            Output('tab-content', 'children'),
            [Input('tabs', 'value'),
             Input('interval-component', 'n_intervals')]
        )
        def render_content(tab, n):
            """Render selected tab content"""

            if tab == 'overview':
                return self._render_overview()
            elif tab == 'smart_wallets':
                return self._render_smart_wallets()
            elif tab == 'token_monitor':
                return self._render_token_monitor()
            elif tab == 'journal':
                return self._render_journal()
            elif tab == 'ai':
                return self._render_ai_patterns()
            elif tab == 'cost':
                return self._render_cost_optimization()
            elif tab == 'predictions':
                return self._render_predictions()
            elif tab == 'strategy':
                return self._render_strategy()
            elif tab == 'command_center':
                return self._render_command_center()

            return html.Div("Loading...")

        # Monitor control callbacks
        for monitor_id in self.monitor_manager.MONITORS.keys():
            self._create_monitor_callback(monitor_id)

    def _create_monitor_callback(self, monitor_id: str):
        """Create callback for a specific monitor's control button"""
        @self.app.callback(
            Output(f'monitor-msg-{monitor_id}', 'children'),
            [Input(f'monitor-btn-{monitor_id}', 'n_clicks')]
        )
        def control_monitor(n_clicks):
            if n_clicks == 0:
                return ""

            # Check current status
            status = self.monitor_manager.get_monitor_status(monitor_id)

            if status['running']:
                # Stop the monitor
                result = self.monitor_manager.stop_monitor(monitor_id)
            else:
                # Start the monitor
                result = self.monitor_manager.start_monitor(monitor_id)

            if result['success']:
                return f"✅ {result['message']}"
            else:
                return f"❌ {result['error']}"

    def _render_overview(self):
        """Render overview tab"""
        predictions_df = self._load_predictions()
        journal = self._load_trading_journal()
        cost_stats = self._load_cost_stats()

        # Calculate metrics
        total_predictions = len(predictions_df)
        buy_recs = len(predictions_df[predictions_df['recommendation'] == 'BUY']) if not predictions_df.empty else 0

        initial_capital = journal.get('initial_capital', 10000)
        current_capital = journal.get('current_capital', initial_capital)
        total_pnl = journal.get('total_pnl', 0)
        total_trades = journal.get('total_trades', 0)
        win_rate = journal.get('win_rate', 0)

        return_pct = ((current_capital / initial_capital) - 1) * 100 if initial_capital > 0 else 0

        # Stats cards
        stats_cards = html.Div([
            # Row 1: Trading Stats
            html.Div([
                self._create_stat_card("💰 Portfolio Value", f"${current_capital:,.2f}",
                                      f"{return_pct:+.2f}%", return_pct >= 0),
                self._create_stat_card("📈 Total P&L", f"${total_pnl:,.2f}",
                                      f"{total_trades} trades", total_pnl >= 0),
                self._create_stat_card("🎯 Win Rate", f"{win_rate*100:.1f}%",
                                      f"{journal.get('winning_trades', 0)} wins", win_rate >= 0.5),
                self._create_stat_card("🤖 Predictions", f"{total_predictions}",
                                      f"{buy_recs} BUY signals", True),
            ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px', 'flexWrap': 'wrap'}),

            # Row 2: System Stats
            html.Div([
                self._create_stat_card("💾 Features Cached", f"{cost_stats.get('features', 0)}",
                                      "Fast retrieval", True),
                self._create_stat_card("🔍 Patterns Stored", f"{cost_stats.get('patterns', 0)}",
                                      "Historical learning", True),
                self._create_stat_card("🧠 Claude Decisions", f"{cost_stats.get('claude_decisions', 0)}",
                                      "Cached responses", True),
                self._create_stat_card("📊 Trade Outcomes", f"{cost_stats.get('trade_outcomes', 0)}",
                                      "Performance tracking", True),
            ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px', 'flexWrap': 'wrap'}),

            # Charts
            html.Div([
                html.Div([
                    dcc.Graph(id='overview-pnl-chart', figure=self._create_pnl_chart(journal))
                ], style={'flex': '1', 'minWidth': '300px'}),
                html.Div([
                    dcc.Graph(id='overview-recommendations', figure=self._create_recommendation_chart(predictions_df))
                ], style={'flex': '1', 'minWidth': '300px'}),
            ], style={'display': 'flex', 'gap': '20px', 'flexWrap': 'wrap'})
        ])

        return stats_cards

    def _create_stat_card(self, title, value, subtitle, positive=True):
        """Create a stat card"""
        color = '#00ff9f' if positive else '#ff4444'

        return html.Div([
            html.H4(title, style={'color': '#999', 'margin': '0', 'fontSize': '14px'}),
            html.H2(value, style={'color': color, 'margin': '10px 0', 'fontSize': '32px'}),
            html.P(subtitle, style={'color': '#ccc', 'margin': '0', 'fontSize': '12px'}),
        ], style={
            'backgroundColor': '#1e2130',
            'padding': '20px',
            'borderRadius': '10px',
            'flex': '1',
            'minWidth': '200px',
            'boxShadow': '0 4px 6px rgba(0,0,0,0.3)'
        })

    def _create_pnl_chart(self, journal):
        """Create P&L chart"""
        closed = journal.get('closed_positions', [])

        if not closed:
            fig = go.Figure()
            fig.add_annotation(text="No trades yet", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False)
            fig.update_layout(template='plotly_dark', title="P&L Over Time")
            return fig

        # Calculate cumulative P&L
        cumulative_pnl = []
        running_total = 0
        dates = []

        for trade in sorted(closed, key=lambda x: x.get('exit_time', '')):
            running_total += trade.get('realized_pnl', 0)
            cumulative_pnl.append(running_total)
            dates.append(trade.get('exit_time', '')[:10])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_pnl,
            mode='lines+markers',
            name='Cumulative P&L',
            line=dict(color='#00ff9f', width=3),
            fill='tozeroy',
            fillcolor='rgba(0,255,159,0.1)'
        ))

        fig.update_layout(
            template='plotly_dark',
            title="Cumulative P&L",
            xaxis_title="Date",
            yaxis_title="P&L ($)",
            hovermode='closest',
            showlegend=False
        )

        return fig

    def _create_recommendation_chart(self, df):
        """Create recommendation pie chart"""
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No predictions", xref="paper", yref="paper",
                             x=0.5, y=0.5, showarrow=False)
            fig.update_layout(template='plotly_dark', title="Recommendations")
            return fig

        rec_counts = df['recommendation'].value_counts()

        colors = {'BUY': '#00ff9f', 'HOLD': '#ffd700', 'AVOID': '#ff4444', 'UNKNOWN': '#999'}

        fig = go.Figure(data=[go.Pie(
            labels=rec_counts.index,
            values=rec_counts.values,
            marker=dict(colors=[colors.get(label, '#999') for label in rec_counts.index]),
            hole=0.4
        )])

        fig.update_layout(
            template='plotly_dark',
            title="AI Recommendations",
            showlegend=True
        )

        return fig

    def _render_journal(self):
        """Render trading journal tab"""
        journal = self._load_trading_journal()

        if not journal:
            return html.Div([
                html.H3("📭 No trading history yet", style={'color': '#999', 'textAlign': 'center', 'padding': '40px'}),
                html.P("Start paper trading to see your trades here", style={'color': '#666', 'textAlign': 'center'})
            ])

        closed = journal.get('closed_positions', [])

        if not closed:
            return html.Div([
                html.H3("📭 No completed trades yet", style={'color': '#999', 'textAlign': 'center', 'padding': '40px'}),
                html.P("Trades will appear here once they are closed", style={'color': '#666', 'textAlign': 'center'})
            ])

        # Create trades table with clickable DexScreener links
        trades_rows = []
        for trade in sorted(closed, key=lambda x: x.get('exit_time', ''), reverse=True)[:50]:
            entry_price = trade.get('entry_price', 0)
            exit_price = trade.get('current_price', 0)
            pnl = trade.get('realized_pnl', 0)
            return_pct = ((exit_price / entry_price) - 1) * 100 if entry_price else 0

            # Get token address and symbol
            token_address = trade.get('token_address', '')
            symbol = trade.get('symbol', token_address[:8])

            # Create DexScreener link
            dex_link = f"https://dexscreener.com/solana/{token_address}"

            trades_rows.append(
                html.Tr([
                    html.Td(html.A(symbol[:12], href=dex_link, target="_blank",
                                  style={'color': '#00d4ff', 'textDecoration': 'none'},
                                  className='token-link'),
                           style={'padding': '10px'}),
                    html.Td(trade.get('token_type', 'unknown'), style={'padding': '10px'}),
                    html.Td(f"${entry_price:.6f}", style={'padding': '10px'}),
                    html.Td(f"${exit_price:.6f}", style={'padding': '10px'}),
                    html.Td(f"{return_pct:+.1f}%", style={'color': '#00ff9f' if pnl > 0 else '#ff4444', 'fontWeight': 'bold', 'padding': '10px'}),
                    html.Td(f"${pnl:+.2f}", style={'color': '#00ff9f' if pnl > 0 else '#ff4444', 'fontWeight': 'bold', 'padding': '10px'}),
                    html.Td(trade.get('exit_reason', 'N/A'), style={'padding': '10px'}),
                    html.Td(trade.get('entry_time', 'N/A')[:16], style={'padding': '10px'})
                ], style={'backgroundColor': '#1e2130', 'border': '1px solid #333'})
            )

        return html.Div([
            html.H3("💼 Trading History", style={'color': '#00d4ff'}),

            html.Table([
                html.Thead(html.Tr([
                    html.Th('Token', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Type', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Entry', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Exit', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Return', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('P&L', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Exit Reason', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Entry Time', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'})
                ])),
                html.Tbody(trades_rows)
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'color': '#fff'})
        ])

    def _render_ai_patterns(self):
        """Render AI patterns and trends tab"""
        opt_log = self._load_optimization_log()
        journal = self._load_trading_journal()

        if not opt_log:
            return html.Div([
                html.H3("🤖 No optimization data yet", style={'color': '#999', 'textAlign': 'center', 'padding': '40px'}),
                html.P("AI will start learning patterns after enough trades", style={'color': '#666', 'textAlign': 'center'})
            ])

        # Get latest optimization
        latest = opt_log[-1] if opt_log else {}
        analysis = latest.get('analysis', {})
        patterns = analysis.get('patterns', [])
        recommendations = analysis.get('recommendations', [])

        return html.Div([
            html.H3("🤖 AI Learning & Patterns", style={'color': '#00d4ff'}),

            # Pattern summary cards
            html.Div([
                self._create_stat_card("📊 Patterns Found", f"{len(patterns)}",
                                      f"{len(opt_log)} optimizations", True),
                self._create_stat_card("💡 Recommendations", f"{len(recommendations)}",
                                      "Parameter adjustments", True),
                self._create_stat_card("🎯 Latest Analysis",
                                      latest.get('timestamp', 'N/A')[:10],
                                      f"{latest.get('total_trades', 0)} trades analyzed", True),
            ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px', 'flexWrap': 'wrap'}),

            # Patterns discovered
            html.H4("📈 Patterns Discovered", style={'color': '#00ff9f', 'marginTop': '30px'}),
            html.Div([
                html.Div([
                    html.H5(f"Pattern #{i+1}: {p.get('description', 'Unknown')}",
                           style={'color': '#00d4ff'}),
                    html.P(f"Category: {p.get('category', 'N/A')}", style={'color': '#999'}),
                    html.P(f"Metric: {p.get('metric', 'N/A')}: {p.get('current_value', 0):.2f}",
                          style={'color': '#ccc'}),
                    html.P(f"Significance: {p.get('significance', 'unknown')}",
                          style={'color': '#ffd700' if p.get('significance') == 'high' else '#999'})
                ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px',
                         'marginBottom': '10px', 'border': '1px solid #333'})
                for i, p in enumerate(patterns[:10])
            ]) if patterns else html.P("No patterns detected yet", style={'color': '#666'}),

            # AI Recommendations
            html.H4("💡 AI Recommendations", style={'color': '#00ff9f', 'marginTop': '30px'}),
            html.Div([
                html.Div([
                    html.H5(f"{rec.get('category', 'unknown').title()}: {rec.get('parameter', 'N/A')}",
                           style={'color': '#00d4ff'}),
                    html.P(f"Current: {rec.get('current_value', 'N/A')} → Recommended: {rec.get('recommended_value', 'N/A')}",
                          style={'color': '#ffd700', 'fontWeight': 'bold'}),
                    html.P(f"Reasoning: {rec.get('reasoning', 'N/A')}", style={'color': '#ccc'}),
                    html.P(f"Expected Impact: {rec.get('expected_impact', 'N/A')}", style={'color': '#00ff9f'}),
                    html.P(f"Priority: {rec.get('priority', 'unknown').upper()}",
                          style={'color': '#ff4444' if rec.get('priority') == 'high' else '#999'})
                ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px',
                         'marginBottom': '10px', 'border': '1px solid #333'})
                for rec in recommendations[:10]
            ]) if recommendations else html.P("No recommendations yet", style={'color': '#666'})
        ])

    def _render_cost_optimization(self):
        """Render cost optimization tab"""
        cost_stats = self._load_cost_stats()

        return html.Div([
            html.H3("💰 Cost Optimization Dashboard", style={'color': '#00d4ff'}),

            # Stats cards
            html.Div([
                self._create_stat_card("💾 Features Cached",
                                      f"{cost_stats.get('features', 0)}",
                                      "Precomputed & stored", True),
                self._create_stat_card("🔍 Similar Patterns",
                                      f"{cost_stats.get('patterns', 0)}",
                                      "Historical matches", True),
                self._create_stat_card("🧠 Claude Cache Hits",
                                      f"{cost_stats.get('claude_decisions', 0)}",
                                      "Saved API calls", True),
                self._create_stat_card("📊 Trade Outcomes",
                                      f"{cost_stats.get('trade_outcomes', 0)}",
                                      "Learning database", True),
            ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px', 'flexWrap': 'wrap'}),

            # Benefits list
            html.H4("✅ System Benefits", style={'color': '#00ff9f', 'marginTop': '30px'}),
            html.Div([
                html.Div([
                    html.H5("💸 70-80% Cost Reduction", style={'color': '#00ff9f'}),
                    html.P("Compact summaries use 65% fewer tokens", style={'color': '#ccc'})
                ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '10px'}),

                html.Div([
                    html.H5("⚡ Instant Cache Hits", style={'color': '#00ff9f'}),
                    html.P("Repeated analyses return in ~10ms instead of 2s", style={'color': '#ccc'})
                ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '10px'}),

                html.Div([
                    html.H5("🧠 Historical Learning", style={'color': '#00ff9f'}),
                    html.P("Pattern matching provides context from similar past tokens", style={'color': '#ccc'})
                ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '10px'}),

                html.Div([
                    html.H5("📈 Continuous Improvement", style={'color': '#00ff9f'}),
                    html.P("Every trade outcome improves future predictions", style={'color': '#ccc'})
                ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '10px'}),
            ])
        ])

    def _render_predictions(self):
        """Render live predictions tab"""
        df = self._load_predictions()

        if df.empty:
            return html.Div([
                html.H3("📭 No predictions yet", style={'color': '#999', 'textAlign': 'center', 'padding': '40px'}),
                html.P("Predictions will appear here as tokens are analyzed", style={'color': '#666', 'textAlign': 'center'})
            ])

        # Recent predictions - create table with clickable links
        recent = df.tail(20).copy()

        prediction_rows = []
        for _, row in recent.iterrows():
            token_address = row.get('token_address', '')
            # Try to get symbol from metadata, fallback to shortened address
            symbol = row.get('symbol', token_address[:12] if token_address else 'N/A')

            pred_return = row.get('predicted_return', 0) * 100
            recommendation = row.get('recommendation', 'UNKNOWN')
            risk = row.get('risk_score', 5)
            confidence = row.get('confidence', 'MEDIUM')
            migration_time = row.get('migration_time', 'N/A')

            # DexScreener link
            dex_link = f"https://dexscreener.com/solana/{token_address}"

            # Color code recommendation
            rec_color = '#00ff9f' if recommendation == 'BUY' else '#ff4444' if recommendation == 'AVOID' else '#ffd700'
            rec_bg = 'rgba(0,255,159,0.2)' if recommendation == 'BUY' else 'rgba(255,68,68,0.2)' if recommendation == 'AVOID' else 'transparent'

            prediction_rows.append(
                html.Tr([
                    html.Td(html.A(symbol, href=dex_link, target="_blank",
                                  style={'color': '#00d4ff', 'textDecoration': 'none'},
                                  className='token-link'),
                           style={'padding': '10px'}),
                    html.Td(migration_time[:16] if migration_time != 'N/A' else 'N/A', style={'padding': '10px'}),
                    html.Td(f"{pred_return:+.1f}%", style={'color': '#00ff9f' if pred_return > 0 else '#ff4444', 'fontWeight': 'bold', 'padding': '10px'}),
                    html.Td(recommendation, style={'color': rec_color, 'fontWeight': 'bold', 'backgroundColor': rec_bg, 'padding': '10px'}),
                    html.Td(f"{risk}/10", style={'color': '#ff4444' if risk >= 7 else '#ffd700' if risk >= 4 else '#00ff9f', 'padding': '10px'}),
                    html.Td(confidence, style={'color': '#00ff9f' if confidence == 'HIGH' else '#ffd700' if confidence == 'MEDIUM' else '#999', 'padding': '10px'})
                ], style={'backgroundColor': '#1e2130', 'border': '1px solid #333'})
            )

        return html.Div([
            html.H3("🎯 Recent Predictions", style={'color': '#00d4ff'}),

            html.Table([
                html.Thead(html.Tr([
                    html.Th('Token', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Migration', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Predicted Return', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Recommendation', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Risk', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Confidence', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'})
                ])),
                html.Tbody(prediction_rows)
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'color': '#fff'})
        ])

    def _render_strategy(self):
        """Render strategy parameters tab"""
        params = self._load_strategy_params()

        if not params:
            return html.Div([
                html.H3("⚙️ No strategy parameters yet", style={'color': '#999', 'textAlign': 'center', 'padding': '40px'}),
                html.P("Parameters will be created on first paper trade", style={'color': '#666', 'textAlign': 'center'})
            ])

        sl = params.get('stop_loss', {})
        ps = params.get('position_sizing', {})
        filt = params.get('filters', {})

        return html.Div([
            html.H3("⚙️ Current Strategy Parameters", style={'color': '#00d4ff'}),

            # Stop Loss
            html.Div([
                html.H4("🛑 Stop Loss Settings", style={'color': '#00ff9f'}),
                html.P(f"High Risk (7-10): {sl.get('high_risk_pct', 0)*100:.1f}%", style={'color': '#ccc'}),
                html.P(f"Medium Risk (4-6): {sl.get('medium_risk_pct', 0)*100:.1f}%", style={'color': '#ccc'}),
                html.P(f"Low Risk (0-3): {sl.get('low_risk_pct', 0)*100:.1f}%", style={'color': '#ccc'}),
                html.P(f"Tech Multiplier: {sl.get('tech_multiplier', 1):.2f}x", style={'color': '#ffd700'}),
                html.P(f"Viral Multiplier: {sl.get('viral_multiplier', 1):.2f}x", style={'color': '#ffd700'}),
            ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '20px'}),

            # Position Sizing
            html.Div([
                html.H4("💰 Position Sizing", style={'color': '#00ff9f'}),
                html.P(f"Max Position: {ps.get('max_position_pct', 0)*100:.1f}%", style={'color': '#ccc'}),
                html.P(f"HIGH Confidence: {ps.get('high_confidence_mult', 1):.2f}x", style={'color': '#ccc'}),
                html.P(f"MEDIUM Confidence: {ps.get('medium_confidence_mult', 1):.2f}x", style={'color': '#ccc'}),
                html.P(f"LOW Confidence: {ps.get('low_confidence_mult', 1):.2f}x", style={'color': '#ccc'}),
            ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '20px'}),

            # Filters
            html.Div([
                html.H4("🔍 Filtering Rules", style={'color': '#00ff9f'}),
                html.P(f"Min Confidence: {filt.get('min_confidence', 'None (all accepted)')}", style={'color': '#ccc'}),
                html.P(f"Max Risk Score: {filt.get('max_risk_score', 10)}/10", style={'color': '#ccc'}),
                html.P(f"Min Liquidity: {filt.get('min_liquidity_sol', 0)} SOL", style={'color': '#ccc'}),
            ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '8px', 'marginBottom': '20px'}),

            # Metadata
            html.Div([
                html.P(f"Last Updated: {params.get('last_updated', 'N/A')}", style={'color': '#999'}),
                html.P(f"Version: {params.get('version', 1)}", style={'color': '#999'}),
            ], style={'marginTop': '20px'})
        ])

    def _load_indicator_weights(self) -> dict:
        """Load indicator weights configuration"""
        if not self.indicator_weights_file.exists():
            return {'indicators': {}}

        try:
            with open(self.indicator_weights_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading indicator weights: {e}")
            return {'indicators': {}}

    def _render_command_center(self):
        """Render comprehensive command center with monitors and indicator configuration"""
        # Monitor status section
        statuses = self.monitor_manager.get_all_statuses()

        monitor_cards = []
        for monitor_id, status in statuses.items():
            is_running = status['running']
            status_color = '#00ff9f' if is_running else '#999'
            status_text = '🟢 Running' if is_running else '⚫ Stopped'
            button_color = '#ff4444' if is_running else '#00ff9f'
            button_text = '⏸ Stop' if is_running else '▶️ Start'

            monitor_cards.append(
                html.Div([
                    html.Div([
                        html.H4(status['name'], style={'color': '#00d4ff', 'margin': '0'}),
                        html.P(status['description'], style={'color': '#999', 'margin': '5px 0'}),
                    ], style={'flex': '1'}),

                    html.Div([
                        html.P(status_text, style={'color': status_color, 'fontWeight': 'bold', 'margin': '0 0 10px 0'}),
                        html.Button(
                            button_text,
                            id=f'monitor-btn-{monitor_id}',
                            n_clicks=0,
                            style={
                                'backgroundColor': button_color,
                                'color': '#000',
                                'border': 'none',
                                'padding': '10px 20px',
                                'borderRadius': '5px',
                                'cursor': 'pointer',
                                'fontWeight': 'bold',
                                'fontSize': '14px'
                            }
                        ),
                        html.Div(id=f'monitor-msg-{monitor_id}', style={'marginTop': '10px', 'color': '#ffd700', 'fontSize': '12px'})
                    ], style={'textAlign': 'right'})
                ], style={
                    'backgroundColor': '#1e2130',
                    'padding': '20px',
                    'borderRadius': '10px',
                    'marginBottom': '15px',
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'alignItems': 'center',
                    'border': f'2px solid {status_color}'
                })
            )

        # Indicator weights section
        weights_config = self._load_indicator_weights()
        indicators = weights_config.get('indicators', {})

        # Count indicators
        total_indicators = 0
        enabled_indicators = 0
        for category_name, category_data in indicators.items():
            if isinstance(category_data, dict) and 'indicators' in category_data:
                cat_indicators = category_data['indicators']
                total_indicators += len(cat_indicators)
                enabled_indicators += sum(1 for ind in cat_indicators.values() if ind.get('enabled', True))

        # Build indicator display by category
        indicator_sections = []
        for category_name, category_data in indicators.items():
            if not isinstance(category_data, dict) or 'indicators' not in category_data:
                continue

            category_label = category_data.get('category', category_name)
            category_enabled = category_data.get('enabled', True)
            cat_indicators = category_data['indicators']

            # Create indicator rows for this category
            indicator_rows = []
            for ind_name, ind_config in cat_indicators.items():
                weight = ind_config.get('weight', 0.5)
                description = ind_config.get('description', ind_name)
                ind_enabled = ind_config.get('enabled', True)

                # Color code by weight
                weight_color = '#00ff9f' if weight >= 0.8 else '#ffd700' if weight >= 0.5 else '#ff9999'

                indicator_rows.append(
                    html.Tr([
                        html.Td(ind_name, style={'padding': '10px', 'fontSize': '13px', 'fontFamily': 'monospace'}),
                        html.Td(description, style={'padding': '10px', 'fontSize': '12px', 'color': '#ccc'}),
                        html.Td(f"{weight:.2f}", style={'padding': '10px', 'fontWeight': 'bold', 'color': weight_color, 'textAlign': 'center'}),
                        html.Td('✅' if ind_enabled else '❌', style={'padding': '10px', 'textAlign': 'center'})
                    ], style={'backgroundColor': '#1e2130' if ind_enabled else '#2a2a2a', 'border': '1px solid #333'})
                )

            indicator_sections.append(
                html.Div([
                    html.H4(f"{category_label} Indicators {'✅' if category_enabled else '❌'}",
                           style={'color': '#00d4ff', 'marginTop': '30px', 'marginBottom': '15px'}),
                    html.P(f"{len(cat_indicators)} indicators in this category",
                          style={'color': '#999', 'fontSize': '12px', 'marginBottom': '10px'}),
                    html.Table([
                        html.Thead(html.Tr([
                            html.Th('Indicator Name', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333', 'fontSize': '12px'}),
                            html.Th('Description', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333', 'fontSize': '12px'}),
                            html.Th('Weight', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333', 'textAlign': 'center', 'fontSize': '12px'}),
                            html.Th('Status', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333', 'textAlign': 'center', 'fontSize': '12px'})
                        ])),
                        html.Tbody(indicator_rows)
                    ], style={'width': '100%', 'borderCollapse': 'collapse', 'marginBottom': '20px'})
                ])
            )

        return html.Div([
            html.H3("🎮 Command Center", style={'color': '#00d4ff'}),

            # Monitor Control Section
            html.H4("🎛️ Monitor Control", style={'color': '#00ff9f', 'marginTop': '20px'}),
            html.P("Start and stop monitoring processes from the dashboard",
                   style={'color': '#999', 'marginBottom': '20px'}),
            html.Div(monitor_cards),

            # Indicator Configuration Section
            html.H4("📊 Indicator Configuration", style={'color': '#00ff9f', 'marginTop': '40px'}),
            html.P(f"Total Indicators: {total_indicators} | Enabled: {enabled_indicators} | Disabled: {total_indicators - enabled_indicators}",
                   style={'color': '#999', 'marginBottom': '20px'}),
            html.Div([
                html.P("💡 Indicator weights control how much each signal influences trading decisions. Higher weights (closer to 1.0) = stronger influence.",
                      style={'color': '#ccc', 'fontSize': '13px', 'marginBottom': '10px'}),
                html.P("📝 To modify indicator weights, edit data/indicator_weights.json and reload the dashboard.",
                      style={'color': '#ffd700', 'fontSize': '13px', 'marginBottom': '20px'})
            ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '30px'}),

            # Indicator tables by category
            html.Div(indicator_sections)
        ])

    def _load_smart_wallets(self) -> dict:
        """Load smart wallet data"""
        if not self.smart_wallets_file.exists():
            return {'wallets': [], 'total_wallets': 0}

        try:
            with open(self.smart_wallets_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading smart wallets: {e}")
            return {'wallets': [], 'total_wallets': 0}

    def _load_cabal_groups(self) -> dict:
        """Load cabal groups data"""
        if not self.cabal_groups_file.exists():
            return {'groups': [], 'total_groups': 0}

        try:
            with open(self.cabal_groups_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cabal groups: {e}")
            return {'groups': [], 'total_groups': 0}

    def _render_smart_wallets(self):
        """Render smart wallets and cabal tracking tab"""
        wallet_data = self._load_smart_wallets()
        cabal_data = self._load_cabal_groups()

        wallets = wallet_data.get('wallets', [])
        groups = cabal_data.get('groups', [])

        # Sort wallets by win rate and PnL
        sorted_wallets = sorted(wallets, key=lambda x: (x.get('win_rate', 0), x.get('pnl_total', 0)), reverse=True)[:50]

        if not sorted_wallets:
            return html.Div([
                html.H3("🔥 Smart Money Tracker", style={'color': '#00d4ff'}),
                html.P("No smart wallets tracked yet. Start the Smart Money Monitor to begin tracking elite wallets.",
                       style={'color': '#999', 'textAlign': 'center', 'padding': '40px'}),
                html.Div([
                    html.P("💡 Smart wallets are automatically discovered by tracking:", style={'color': '#ccc'}),
                    html.Ul([
                        html.Li("Pre-migration timing accuracy", style={'color': '#999'}),
                        html.Li("Post-migration performance", style={'color': '#999'}),
                        html.Li("Win rate and profitability", style={'color': '#999'}),
                        html.Li("Coordinated group behavior (cabals)", style={'color': '#999'})
                    ])
                ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '8px', 'maxWidth': '600px', 'margin': '0 auto'})
            ])

        # Stats cards
        total_tracked = len(wallets)
        avg_win_rate = sum(w.get('win_rate', 0) for w in wallets) / len(wallets) if wallets else 0
        total_cabal_groups = len(groups)
        high_performers = len([w for w in wallets if w.get('win_rate', 0) > 0.6])

        stats = html.Div([
            self._create_stat_card("👛 Wallets Tracked", f"{total_tracked}", f"{high_performers} high performers", True),
            self._create_stat_card("🎯 Avg Win Rate", f"{avg_win_rate*100:.1f}%", "Across all wallets", avg_win_rate >= 0.5),
            self._create_stat_card("🔥 Cabal Groups", f"{total_cabal_groups}", "Coordinated groups detected", True),
            self._create_stat_card("💰 Total Volume", f"${sum(w.get('total_volume_sol', 0) for w in wallets):,.0f}", "SOL traded", True),
        ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px', 'flexWrap': 'wrap'})

        # Wallet table
        wallet_rows = []
        for wallet in sorted_wallets[:20]:
            address = wallet.get('wallet_address', '')
            short_address = f"{address[:6]}...{address[-4:]}" if address else 'N/A'
            win_rate = wallet.get('win_rate', 0) * 100
            pnl = wallet.get('pnl_total', 0)
            trades = wallet.get('total_trades', 0)
            cabal_score = wallet.get('cabal_score', 0)
            volume = wallet.get('total_volume_sol', 0)

            # Solscan link
            solscan_link = f"https://solscan.io/account/{address}"

            # Color code based on performance
            win_color = '#00ff9f' if win_rate >= 60 else '#ffd700' if win_rate >= 40 else '#ff4444'
            cabal_color = '#ff4444' if cabal_score >= 70 else '#ffd700' if cabal_score >= 40 else '#00ff9f'

            wallet_rows.append(
                html.Tr([
                    html.Td(html.A(short_address, href=solscan_link, target="_blank",
                                  style={'color': '#00d4ff', 'textDecoration': 'none'}),
                           style={'padding': '10px'}),
                    html.Td(f"{win_rate:.1f}%", style={'color': win_color, 'fontWeight': 'bold', 'padding': '10px'}),
                    html.Td(f"${pnl:+.2f}", style={'color': '#00ff9f' if pnl > 0 else '#ff4444', 'padding': '10px'}),
                    html.Td(f"{trades}", style={'padding': '10px'}),
                    html.Td(f"{volume:.1f} SOL", style={'padding': '10px'}),
                    html.Td(f"{cabal_score:.0f}", style={'color': cabal_color, 'fontWeight': 'bold', 'padding': '10px'}),
                    html.Td(', '.join(wallet.get('meta_tags', [])[:3]), style={'padding': '10px', 'fontSize': '11px', 'color': '#999'})
                ], style={'backgroundColor': '#1e2130', 'border': '1px solid #333'})
            )

        # Cabal groups section
        cabal_section = html.Div([
            html.H4("🔥 Detected Cabal Groups", style={'color': '#00ff9f', 'marginTop': '30px'}),
            html.Div([
                html.Div([
                    html.H5(f"{group.get('group_name', 'Unknown Group')}", style={'color': '#ff4444', 'margin': '0'}),
                    html.P(f"Members: {len(group.get('wallet_addresses', []))} | Win Rate: {group.get('group_win_rate', 0)*100:.1f}% | Trades: {group.get('total_trades', 0)}",
                          style={'color': '#ccc', 'margin': '5px 0'}),
                    html.P(f"Coordination Strength: {group.get('coordination_strength', 0)*100:.0f}% | Focus: {', '.join(group.get('meta_focus', ['General'])[:3])}",
                          style={'color': '#ffd700', 'fontSize': '12px', 'margin': '5px 0'})
                ], style={'backgroundColor': '#1e2130', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '10px', 'border': '2px solid #ff4444'})
                for group in groups[:10]
            ]) if groups else html.P("No cabal groups detected yet", style={'color': '#666'})
        ])

        return html.Div([
            html.H3("🔥 Smart Money & Cabal Tracker", style={'color': '#00d4ff'}),
            stats,

            html.H4("💎 Top Performing Wallets", style={'color': '#00ff9f'}),
            html.Table([
                html.Thead(html.Tr([
                    html.Th('Wallet', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Win Rate', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('P&L', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Trades', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Volume', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Cabal Score', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'}),
                    html.Th('Meta Tags', style={'backgroundColor': '#2a2d3a', 'color': '#fff', 'padding': '12px', 'border': '1px solid #333'})
                ])),
                html.Tbody(wallet_rows)
            ], style={'width': '100%', 'borderCollapse': 'collapse', 'color': '#fff', 'marginBottom': '30px'}),

            cabal_section
        ])

    def _render_token_monitor(self):
        """Render real-time token monitor data tab"""
        predictions_df = self._load_predictions()

        if predictions_df.empty:
            return html.Div([
                html.H3("📡 Token Monitor", style={'color': '#00d4ff'}),
                html.P("No token data yet. Start a monitor to begin analyzing tokens in real-time.",
                       style={'color': '#999', 'textAlign': 'center', 'padding': '40px'}),
                html.Div([
                    html.P("💡 The Token Monitor displays:", style={'color': '#ccc'}),
                    html.Ul([
                        html.Li("AI analysis and recommendations", style={'color': '#999'}),
                        html.Li("Technical indicators (RSI, volume, liquidity)", style={'color': '#999'}),
                        html.Li("Social signals (Twitter mentions, holder count)", style={'color': '#999'}),
                        html.Li("Smart money activity on each token", style={'color': '#999'}),
                        html.Li("Risk scores and confidence levels", style={'color': '#999'})
                    ])
                ], style={'backgroundColor': '#1e2130', 'padding': '20px', 'borderRadius': '8px', 'maxWidth': '600px', 'margin': '0 auto'})
            ])

        # Get recent tokens
        recent_tokens = predictions_df.tail(30).sort_values('timestamp' if 'timestamp' in predictions_df.columns else predictions_df.index, ascending=False)

        # Stats
        total_analyzed = len(predictions_df)
        buy_signals = len(predictions_df[predictions_df['recommendation'] == 'BUY']) if 'recommendation' in predictions_df.columns else 0
        avg_risk = predictions_df['risk_score'].mean() if 'risk_score' in predictions_df.columns else 5
        high_confidence = len(predictions_df[predictions_df.get('confidence', 'LOW') == 'HIGH']) if 'confidence' in predictions_df.columns else 0

        stats = html.Div([
            self._create_stat_card("📊 Tokens Analyzed", f"{total_analyzed}", "All time", True),
            self._create_stat_card("✅ BUY Signals", f"{buy_signals}", f"{(buy_signals/total_analyzed*100):.1f}% of total", True),
            self._create_stat_card("⚠️ Avg Risk Score", f"{avg_risk:.1f}/10", "Lower is better", avg_risk < 6),
            self._create_stat_card("🎯 High Confidence", f"{high_confidence}", "Strong signals", True),
        ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '30px', 'flexWrap': 'wrap'})

        # Token cards with full details
        token_cards = []
        for _, token in recent_tokens.head(20).iterrows():
            address = token.get('token_address', token.get('mint', ''))
            symbol = token.get('symbol', address[:12] if address else 'Unknown')
            recommendation = token.get('recommendation', 'UNKNOWN')
            risk = token.get('risk_score', 5)
            confidence = token.get('confidence', 'MEDIUM')
            predicted_return = token.get('predicted_return', token.get('prediction', 0)) * 100 if isinstance(token.get('predicted_return', 0), (int, float)) else 0

            # Get detailed analysis from claude_analysis if available
            analysis = token.get('claude_analysis', {}) if isinstance(token.get('claude_analysis'), dict) else {}
            reasoning = analysis.get('reasoning', 'No detailed analysis available')[:200]

            # Color coding
            rec_color = '#00ff9f' if recommendation == 'BUY' else '#ff4444' if recommendation == 'AVOID' else '#ffd700'
            rec_bg = 'rgba(0,255,159,0.1)' if recommendation == 'BUY' else 'rgba(255,68,68,0.1)' if recommendation == 'AVOID' else 'transparent'

            # DexScreener link
            dex_link = f"https://dexscreener.com/solana/{address}"

            token_cards.append(
                html.Div([
                    html.Div([
                        html.H4(html.A(symbol, href=dex_link, target="_blank", style={'color': '#00d4ff', 'textDecoration': 'none', 'margin': '0'})),
                        html.P(f"{address[:8]}...{address[-6:]}" if address else 'N/A', style={'color': '#666', 'fontSize': '12px', 'margin': '5px 0'})
                    ]),

                    html.Div([
                        html.Div([
                            html.Span("Recommendation: ", style={'color': '#999'}),
                            html.Span(recommendation, style={'color': rec_color, 'fontWeight': 'bold', 'backgroundColor': rec_bg, 'padding': '2px 8px', 'borderRadius': '4px'})
                        ], style={'marginBottom': '10px'}),

                        html.Div([
                            html.Span(f"Risk: {risk}/10", style={'color': '#ff4444' if risk >= 7 else '#ffd700' if risk >= 4 else '#00ff9f', 'marginRight': '15px'}),
                            html.Span(f"Confidence: {confidence}", style={'color': '#00ff9f' if confidence == 'HIGH' else '#ffd700' if confidence == 'MEDIUM' else '#999', 'marginRight': '15px'}),
                            html.Span(f"Predicted: {predicted_return:+.1f}%", style={'color': '#00ff9f' if predicted_return > 0 else '#ff4444'})
                        ], style={'fontSize': '14px', 'marginBottom': '10px'}),

                        html.P(reasoning, style={'color': '#ccc', 'fontSize': '13px', 'fontStyle': 'italic', 'margin': '10px 0'})
                    ])
                ], style={
                    'backgroundColor': '#1e2130',
                    'padding': '20px',
                    'borderRadius': '10px',
                    'marginBottom': '15px',
                    'border': f'2px solid {rec_color}'
                })
            )

        return html.Div([
            html.H3("📡 Real-Time Token Monitor", style={'color': '#00d4ff'}),
            stats,

            html.H4("🔍 Recently Analyzed Tokens", style={'color': '#00ff9f', 'marginTop': '20px'}),
            html.Div(token_cards)
        ])

    def run(self):
        """Run the dashboard server"""
        logger.info(f"🚀 Starting comprehensive dashboard on http://localhost:{self.port}")
        self.app.run_server(debug=True, port=self.port, host='127.0.0.1')


def main():
    dashboard = ComprehensiveDashboard(port=8050)
    dashboard.run()


if __name__ == "__main__":
    main()
