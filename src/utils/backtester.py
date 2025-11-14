"""
Backtesting framework with P&L simulation
Tests trading strategies based on model predictions
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
import json


class Backtester:
    """Backtest trading strategies with P&L simulation"""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        position_size: float = 0.1,
        transaction_fee: float = 0.003,
        slippage: float = 0.001
    ):
        """
        Initialize backtester

        Args:
            initial_capital: Starting capital in USD
            position_size: Fraction of capital per trade
            transaction_fee: Transaction fee (0.3% default)
            slippage: Slippage percentage
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.transaction_fee = transaction_fee
        self.slippage = slippage

        logger.info(f"Initialized backtester with ${initial_capital} capital")

    def simulate_trades(
        self,
        predictions: pd.DataFrame,
        actuals: pd.DataFrame,
        strategy: str = "threshold"
    ) -> Dict[str, any]:
        """
        Simulate trades based on predictions

        Args:
            predictions: DataFrame with predictions
            actuals: DataFrame with actual returns
            strategy: Trading strategy ("threshold", "top_k", "risk_adjusted")

        Returns:
            Backtest results dict
        """
        logger.info(f"Running backtest with {strategy} strategy")

        # Merge predictions with actuals
        data = predictions.merge(
            actuals[['token_address', 'migration_time', 'return_24h']],
            on=['token_address', 'migration_time'],
            how='inner'
        )

        if data.empty:
            logger.warning("No matching data for backtest")
            return self._empty_results()

        # Execute strategy
        if strategy == "threshold":
            trades = self._threshold_strategy(data)
        elif strategy == "top_k":
            trades = self._top_k_strategy(data)
        elif strategy == "risk_adjusted":
            trades = self._risk_adjusted_strategy(data)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Calculate P&L
        results = self._calculate_pnl(trades)

        logger.info(f"Backtest complete: {len(trades)} trades, final capital: ${results['final_capital']:.2f}")
        return results

    def _threshold_strategy(
        self,
        data: pd.DataFrame,
        threshold: float = 0.15
    ) -> pd.DataFrame:
        """
        Buy if predicted return > threshold

        Args:
            data: Data with predictions and actuals
            threshold: Minimum predicted return to trade

        Returns:
            DataFrame of trades
        """
        trades = data[data['predicted_return'] > threshold].copy()
        trades['position_size_usd'] = self.initial_capital * self.position_size

        logger.info(f"Threshold strategy: {len(trades)} trades (threshold={threshold})")
        return trades

    def _top_k_strategy(
        self,
        data: pd.DataFrame,
        k: int = 5
    ) -> pd.DataFrame:
        """
        Buy top K tokens by predicted return each period

        Args:
            data: Data with predictions and actuals
            k: Number of top tokens to buy

        Returns:
            DataFrame of trades
        """
        # Group by time period (assuming daily)
        data['date'] = pd.to_datetime(data['migration_time']).dt.date

        trades = []
        for date, group in data.groupby('date'):
            top_k = group.nlargest(k, 'predicted_return')
            trades.append(top_k)

        trades = pd.concat(trades)
        trades['position_size_usd'] = self.initial_capital * self.position_size / k

        logger.info(f"Top-K strategy: {len(trades)} trades (K={k})")
        return trades

    def _risk_adjusted_strategy(
        self,
        data: pd.DataFrame,
        min_return: float = 0.10,
        max_risk: float = 7
    ) -> pd.DataFrame:
        """
        Buy if predicted return > min AND risk < max

        Args:
            data: Data with predictions and actuals
            min_return: Minimum predicted return
            max_risk: Maximum risk score

        Returns:
            DataFrame of trades
        """
        if 'risk_score' not in data.columns:
            logger.warning("No risk_score column, falling back to threshold strategy")
            return self._threshold_strategy(data, min_return)

        trades = data[
            (data['predicted_return'] > min_return) &
            (data['risk_score'] < max_risk)
        ].copy()

        trades['position_size_usd'] = self.initial_capital * self.position_size

        logger.info(f"Risk-adjusted strategy: {len(trades)} trades")
        return trades

    def _calculate_pnl(self, trades: pd.DataFrame) -> Dict[str, any]:
        """
        Calculate P&L for trades

        Args:
            trades: DataFrame of executed trades

        Returns:
            Results dict with metrics
        """
        if trades.empty:
            return self._empty_results()

        capital = self.initial_capital
        pnl_history = [capital]
        trade_results = []

        for idx, trade in trades.iterrows():
            # Entry
            position_size = trade['position_size_usd']
            entry_cost = position_size * (1 + self.transaction_fee + self.slippage)

            # Exit
            actual_return = trade.get('return_24h', 0)
            exit_value = position_size * (1 + actual_return) * (1 - self.transaction_fee - self.slippage)

            # P&L
            pnl = exit_value - entry_cost

            capital += pnl
            pnl_history.append(capital)

            trade_results.append({
                'token': trade['token_address'],
                'predicted_return': trade['predicted_return'],
                'actual_return': actual_return,
                'pnl': pnl,
                'capital_after': capital
            })

        # Calculate metrics
        pnl_history = np.array(pnl_history)
        returns = np.diff(pnl_history) / pnl_history[:-1]

        total_return = (capital - self.initial_capital) / self.initial_capital
        win_rate = sum(1 for t in trade_results if t['pnl'] > 0) / len(trade_results)

        # Sharpe ratio (annualized, assuming daily)
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(365)
        else:
            sharpe = 0

        # Max drawdown
        cummax = np.maximum.accumulate(pnl_history)
        drawdown = (pnl_history - cummax) / cummax
        max_drawdown = drawdown.min()

        results = {
            'initial_capital': self.initial_capital,
            'final_capital': capital,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'num_trades': len(trade_results),
            'win_rate': win_rate,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'pnl_history': pnl_history.tolist(),
            'trade_results': trade_results
        }

        return results

    def _empty_results(self) -> Dict[str, any]:
        """Return empty results"""
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital,
            'total_return': 0,
            'total_return_pct': 0,
            'num_trades': 0,
            'win_rate': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'max_drawdown_pct': 0,
            'pnl_history': [self.initial_capital],
            'trade_results': []
        }

    def compare_strategies(
        self,
        predictions: pd.DataFrame,
        actuals: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compare multiple strategies

        Args:
            predictions: Predictions DataFrame
            actuals: Actuals DataFrame

        Returns:
            Comparison DataFrame
        """
        strategies = {
            'threshold': lambda: self.simulate_trades(predictions, actuals, 'threshold'),
            'top_k': lambda: self.simulate_trades(predictions, actuals, 'top_k'),
            'risk_adjusted': lambda: self.simulate_trades(predictions, actuals, 'risk_adjusted')
        }

        comparison = []
        for name, strategy_fn in strategies.items():
            results = strategy_fn()
            comparison.append({
                'strategy': name,
                'final_capital': results['final_capital'],
                'total_return_pct': results['total_return_pct'],
                'num_trades': results['num_trades'],
                'win_rate': results['win_rate'],
                'sharpe_ratio': results['sharpe_ratio'],
                'max_drawdown_pct': results['max_drawdown_pct']
            })

        return pd.DataFrame(comparison)


# Example usage
def main():
    # Mock data
    np.random.seed(42)
    n = 100

    predictions = pd.DataFrame({
        'token_address': [f'TOKEN{i}' for i in range(n)],
        'migration_time': pd.date_range('2024-01-01', periods=n, freq='6H'),
        'predicted_return': np.random.randn(n) * 0.15 + 0.10,
        'risk_score': np.random.randint(1, 11, n)
    })

    actuals = pd.DataFrame({
        'token_address': predictions['token_address'],
        'migration_time': predictions['migration_time'],
        'return_24h': np.random.randn(n) * 0.20 + 0.05
    })

    # Run backtest
    backtester = Backtester(initial_capital=10000, position_size=0.1)

    results = backtester.simulate_trades(predictions, actuals, strategy='threshold')

    print("\nBacktest Results:")
    print(f"Final Capital: ${results['final_capital']:.2f}")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Trades: {results['num_trades']}")
    print(f"Win Rate: {results['win_rate']*100:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")

    # Compare strategies
    print("\n\nStrategy Comparison:")
    comparison = backtester.compare_strategies(predictions, actuals)
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
