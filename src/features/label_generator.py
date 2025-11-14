"""
Label generation for supervised learning
Computes target variables (returns, pump events, rug detection)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger


class LabelGenerator:
    """Generate training labels from price data"""

    def __init__(
        self,
        label_windows: Dict[str, int] = None,
        pump_thresholds: Dict[str, float] = None,
        rug_threshold: float = -0.5
    ):
        """
        Initialize label generator

        Args:
            label_windows: Time windows (seconds) for computing returns
            pump_thresholds: Gain thresholds for pump classification
            rug_threshold: Loss threshold for rug detection
        """
        self.label_windows = label_windows or {
            "1h": 3600,
            "6h": 21600,
            "24h": 86400,
            "7d": 604800
        }

        self.pump_thresholds = pump_thresholds or {
            "1h": 0.10,   # 10% gain
            "24h": 0.20,  # 20% gain
            "7d": 0.50    # 50% gain
        }

        self.rug_threshold = rug_threshold

        logger.info("Initialized label generator")

    def compute_returns(
        self,
        price_history: List[Dict[str, any]],
        reference_time: datetime
    ) -> Dict[str, float]:
        """
        Compute returns over various time windows

        Args:
            price_history: List of price dicts with timestamp and price
            reference_time: Reference time (migration time)

        Returns:
            Dict of returns for each window
        """
        returns = {}

        if not price_history:
            for window_label in self.label_windows.keys():
                returns[f'return_{window_label}'] = 0.0
                returns[f'log_return_{window_label}'] = 0.0
            return returns

        # Convert to DataFrame
        df = pd.DataFrame(price_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Get reference price (price at migration time)
        ref_prices = df[df['timestamp'] <= reference_time]
        if len(ref_prices) == 0:
            reference_price = df.iloc[0]['price']
        else:
            reference_price = ref_prices.iloc[-1]['price']

        if reference_price == 0:
            logger.warning("Reference price is zero, cannot compute returns")
            for window_label in self.label_windows.keys():
                returns[f'return_{window_label}'] = 0.0
                returns[f'log_return_{window_label}'] = 0.0
            return returns

        # Compute returns for each window
        for window_label, window_seconds in self.label_windows.items():
            window_end = reference_time + timedelta(seconds=window_seconds)

            # Get prices within window
            window_prices = df[
                (df['timestamp'] > reference_time) &
                (df['timestamp'] <= window_end)
            ]

            if len(window_prices) > 0:
                # Use final price in window
                final_price = window_prices.iloc[-1]['price']

                # Calculate simple and log returns
                simple_return = (final_price - reference_price) / reference_price
                log_return = np.log(final_price / reference_price) if final_price > 0 else 0

                returns[f'return_{window_label}'] = simple_return
                returns[f'log_return_{window_label}'] = log_return
            else:
                returns[f'return_{window_label}'] = 0.0
                returns[f'log_return_{window_label}'] = 0.0

        return returns

    def compute_pump_labels(
        self,
        returns: Dict[str, float]
    ) -> Dict[str, int]:
        """
        Generate binary pump labels based on return thresholds

        Args:
            returns: Dict of returns from compute_returns

        Returns:
            Dict of binary pump labels
        """
        labels = {}

        for window_label, threshold in self.pump_thresholds.items():
            return_key = f'return_{window_label}'
            if return_key in returns:
                labels[f'pump_{window_label}'] = int(returns[return_key] > threshold)
            else:
                labels[f'pump_{window_label}'] = 0

        return labels

    def detect_rug(
        self,
        price_history: List[Dict[str, any]],
        reference_time: datetime,
        window_hours: int = 24
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Detect if a rug pull occurred

        A rug is detected if:
        1. Price drops by > rug_threshold within window
        2. Drop is sustained (doesn't recover within 1 hour)

        Args:
            price_history: Price history
            reference_time: Migration time
            window_hours: Hours to monitor for rug

        Returns:
            Tuple of (is_rug, rug_timestamp)
        """
        if not price_history:
            return False, None

        df = pd.DataFrame(price_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Get reference price
        ref_prices = df[df['timestamp'] <= reference_time]
        if len(ref_prices) == 0:
            reference_price = df.iloc[0]['price']
        else:
            reference_price = ref_prices.iloc[-1]['price']

        if reference_price == 0:
            return False, None

        # Monitor price within window
        window_end = reference_time + timedelta(hours=window_hours)
        window_prices = df[
            (df['timestamp'] > reference_time) &
            (df['timestamp'] <= window_end)
        ]

        for idx, row in window_prices.iterrows():
            current_price = row['price']
            current_time = row['timestamp']

            # Check if price dropped below threshold
            if current_price / reference_price - 1 < self.rug_threshold:
                # Check if drop is sustained (no recovery in next hour)
                recovery_window = df[
                    (df['timestamp'] > current_time) &
                    (df['timestamp'] <= current_time + timedelta(hours=1))
                ]

                if len(recovery_window) > 0:
                    max_recovery_price = recovery_window['price'].max()
                    recovery_ratio = max_recovery_price / reference_price

                    # If doesn't recover to at least 80% of reference, it's a rug
                    if recovery_ratio < 0.8:
                        logger.info(f"Rug detected at {current_time}, price dropped to {current_price:.6f}")
                        return True, current_time
                else:
                    # No recovery data available, assume rug
                    return True, current_time

        return False, None

    def compute_volatility(
        self,
        price_history: List[Dict[str, any]],
        reference_time: datetime,
        window_seconds: int = 86400
    ) -> float:
        """
        Compute realized volatility over a window

        Args:
            price_history: Price history
            reference_time: Reference time
            window_seconds: Window size in seconds

        Returns:
            Volatility (standard deviation of log returns)
        """
        if not price_history:
            return 0.0

        df = pd.DataFrame(price_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Get prices in window
        window_end = reference_time + timedelta(seconds=window_seconds)
        window_prices = df[
            (df['timestamp'] > reference_time) &
            (df['timestamp'] <= window_end)
        ].copy()

        if len(window_prices) < 2:
            return 0.0

        # Compute log returns
        window_prices['log_return'] = np.log(
            window_prices['price'] / window_prices['price'].shift(1)
        )

        volatility = window_prices['log_return'].std()
        return volatility if not np.isnan(volatility) else 0.0

    def generate_labels(
        self,
        token_address: str,
        migration_time: datetime,
        price_history: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Generate all labels for a token

        Args:
            token_address: Token address
            migration_time: Migration timestamp
            price_history: Price history with timestamps

        Returns:
            Dict of all labels
        """
        labels = {
            'token_address': token_address,
            'migration_time': migration_time.isoformat()
        }

        # Compute returns
        returns = self.compute_returns(price_history, migration_time)
        labels.update(returns)

        # Compute pump labels
        pump_labels = self.compute_pump_labels(returns)
        labels.update(pump_labels)

        # Detect rug
        is_rug, rug_time = self.detect_rug(price_history, migration_time)
        labels['is_rug'] = int(is_rug)
        labels['rug_timestamp'] = rug_time.isoformat() if rug_time else None

        # Compute volatility
        labels['volatility_24h'] = self.compute_volatility(
            price_history,
            migration_time,
            window_seconds=86400
        )

        # Add max gain/loss in 24h for additional insights
        returns_24h = self.compute_max_gain_loss(price_history, migration_time, hours=24)
        labels.update(returns_24h)

        logger.debug(f"Generated labels for {token_address}")
        return labels

    def compute_max_gain_loss(
        self,
        price_history: List[Dict[str, any]],
        reference_time: datetime,
        hours: int = 24
    ) -> Dict[str, float]:
        """
        Compute maximum gain and loss within window

        Args:
            price_history: Price history
            reference_time: Reference time
            hours: Window size in hours

        Returns:
            Dict with max_gain and max_loss
        """
        result = {'max_gain_24h': 0.0, 'max_loss_24h': 0.0}

        if not price_history:
            return result

        df = pd.DataFrame(price_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Get reference price
        ref_prices = df[df['timestamp'] <= reference_time]
        if len(ref_prices) == 0:
            reference_price = df.iloc[0]['price']
        else:
            reference_price = ref_prices.iloc[-1]['price']

        if reference_price == 0:
            return result

        # Get prices in window
        window_end = reference_time + timedelta(hours=hours)
        window_prices = df[
            (df['timestamp'] > reference_time) &
            (df['timestamp'] <= window_end)
        ]

        if len(window_prices) > 0:
            max_price = window_prices['price'].max()
            min_price = window_prices['price'].min()

            result['max_gain_24h'] = (max_price - reference_price) / reference_price
            result['max_loss_24h'] = (min_price - reference_price) / reference_price

        return result


# Example usage
def main():
    generator = LabelGenerator()

    # Mock price data
    reference_time = datetime(2025, 1, 1, 12, 0, 0)
    price_history = []

    # Generate mock price sequence (pump then dump)
    for i in range(100):
        timestamp = reference_time + timedelta(minutes=i * 15)

        # Simulate price movement
        if i < 10:
            price = 1.0 + i * 0.1  # Pump
        elif i < 30:
            price = 2.0  # Stable high
        else:
            price = 2.0 - (i - 30) * 0.03  # Slow decline

        price_history.append({
            'timestamp': timestamp,
            'price': max(0.1, price)  # Floor at 0.1
        })

    labels = generator.generate_labels(
        token_address='MOCKTOKEN123',
        migration_time=reference_time,
        price_history=price_history
    )

    print("Generated labels:")
    for key, value in labels.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
