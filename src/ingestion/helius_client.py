"""
Helius API Client for enhanced Solana data
Provides dev wallet history, transaction parsing, and enhanced analytics
"""
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import time


class HeliusClient:
    """Client for Helius enhanced API endpoints"""

    def __init__(self, api_key: str):
        """
        Initialize Helius client

        Args:
            api_key: Helius API key
        """
        self.api_key = api_key
        self.base_url = "https://api.helius.xyz/v0"
        self.session = requests.Session()
        self.rate_limit_delay = 0.1  # 100ms between requests

        logger.info("Initialized Helius client")

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make API request with rate limiting

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response JSON or None
        """
        url = f"{self.base_url}/{endpoint}"

        if params is None:
            params = {}

        params['api-key'] = self.api_key

        try:
            time.sleep(self.rate_limit_delay)  # Rate limiting
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Helius API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Helius request failed: {e}")
            return None

    def get_wallet_transactions(
        self,
        wallet_address: str,
        before: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for a wallet

        Args:
            wallet_address: Wallet address
            before: Transaction signature to paginate from
            limit: Max transactions to return

        Returns:
            List of enhanced transaction objects
        """
        params = {
            'limit': min(limit, 100)  # Helius max is 100
        }

        if before:
            params['before'] = before

        response = self._request(f"addresses/{wallet_address}/transactions", params)

        if response:
            return response
        return []

    def get_token_metadata(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """
        Get token metadata including mint info

        Args:
            mint_address: Token mint address

        Returns:
            Token metadata dict
        """
        response = self._request(f"token-metadata", {'mintAddress': mint_address})
        return response

    def get_wallet_token_accounts(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Get all token accounts owned by wallet

        Args:
            wallet_address: Wallet address

        Returns:
            List of token accounts with balances
        """
        response = self._request(f"addresses/{wallet_address}/balances")

        if response and 'tokens' in response:
            return response['tokens']
        return []

    def analyze_dev_wallet_history(self, dev_wallet: str, lookback_days: int = 90) -> Dict[str, Any]:
        """
        Analyze developer wallet history for red flags

        Args:
            dev_wallet: Developer wallet address
            lookback_days: Days to look back

        Returns:
            Analysis dict with risk metrics
        """
        logger.info(f"Analyzing dev wallet: {dev_wallet[:8]}...")

        # Get transaction history
        transactions = self.get_wallet_transactions(dev_wallet, limit=100)

        # Get current token holdings
        token_accounts = self.get_wallet_token_accounts(dev_wallet)

        # Analysis metrics
        analysis = {
            'wallet_address': dev_wallet,
            'total_transactions': len(transactions),
            'token_holdings_count': len(token_accounts),
            'created_tokens': [],
            'suspicious_patterns': [],
            'rug_pull_indicators': [],
            'credibility_score': 100.0,  # Start at 100, deduct for red flags
            'analyzed_at': datetime.now().isoformat()
        }

        # Analyze transactions for patterns
        large_sells = []
        token_creates = []
        repeated_patterns = []

        for tx in transactions:
            tx_type = tx.get('type', '')

            # Track token creations
            if 'CREATE' in tx_type or 'MINT' in tx_type:
                token_creates.append({
                    'signature': tx.get('signature'),
                    'timestamp': tx.get('timestamp')
                })

            # Track large sells
            if 'SELL' in tx_type or 'SWAP' in tx_type:
                # Check if this was a large sell
                native_transfers = tx.get('nativeTransfers', [])
                for transfer in native_transfers:
                    if transfer.get('fromUserAccount') == dev_wallet:
                        amount_sol = transfer.get('amount', 0) / 1e9
                        if amount_sol > 10:  # Large sell threshold: 10 SOL
                            large_sells.append({
                                'amount_sol': amount_sol,
                                'timestamp': tx.get('timestamp'),
                                'signature': tx.get('signature')
                            })

        analysis['created_tokens'] = token_creates
        analysis['large_sells'] = large_sells

        # Red flag detection
        if len(token_creates) > 10:
            analysis['suspicious_patterns'].append('High token creation count (>10)')
            analysis['credibility_score'] -= 20

        if len(large_sells) > 5:
            analysis['rug_pull_indicators'].append('Multiple large sells (>5)')
            analysis['credibility_score'] -= 30

        # Check for quick sell patterns (token create followed by large sell within 24h)
        for create in token_creates:
            create_time = datetime.fromisoformat(create['timestamp'].replace('Z', '+00:00'))
            for sell in large_sells:
                sell_time = datetime.fromisoformat(sell['timestamp'].replace('Z', '+00:00'))
                time_diff = (sell_time - create_time).total_seconds() / 3600  # hours

                if 0 < time_diff < 24:
                    analysis['rug_pull_indicators'].append(
                        f'Quick sell pattern: Created token then sold {sell["amount_sol"]:.1f} SOL within {time_diff:.1f}h'
                    )
                    analysis['credibility_score'] -= 50

        # Wallet age check (older = more credible)
        if transactions:
            oldest_tx = min(transactions, key=lambda x: x.get('timestamp', ''))
            oldest_time = datetime.fromisoformat(oldest_tx['timestamp'].replace('Z', '+00:00'))
            wallet_age_days = (datetime.now(oldest_time.tzinfo) - oldest_time).days

            analysis['wallet_age_days'] = wallet_age_days

            if wallet_age_days < 7:
                analysis['suspicious_patterns'].append('Very new wallet (<7 days)')
                analysis['credibility_score'] -= 40
            elif wallet_age_days < 30:
                analysis['credibility_score'] -= 10

        # Floor at 0
        analysis['credibility_score'] = max(0, analysis['credibility_score'])

        logger.info(f"Dev analysis complete. Credibility: {analysis['credibility_score']:.1f}/100")

        return analysis

    def detect_bundle_wallets(self, wallet_addresses: List[str]) -> Dict[str, Any]:
        """
        Analyze if wallets are part of a coordinated bundle

        Args:
            wallet_addresses: List of wallet addresses to check

        Returns:
            Bundle analysis dict
        """
        logger.info(f"Analyzing {len(wallet_addresses)} wallets for bundle patterns...")

        bundle_analysis = {
            'is_likely_bundle': False,
            'confidence': 0.0,
            'indicators': [],
            'wallet_count': len(wallet_addresses),
            'analyzed_at': datetime.now().isoformat()
        }

        if len(wallet_addresses) < 2:
            return bundle_analysis

        # Get transaction histories for all wallets
        wallet_histories = {}
        for addr in wallet_addresses[:10]:  # Limit to first 10 to avoid rate limits
            txs = self.get_wallet_transactions(addr, limit=50)
            wallet_histories[addr] = txs

        # Pattern detection
        creation_times = []
        common_funding_sources = set()
        first_iteration = True

        for addr, txs in wallet_histories.items():
            if not txs:
                continue

            # Get wallet creation time
            oldest_tx = min(txs, key=lambda x: x.get('timestamp', ''))
            creation_times.append(datetime.fromisoformat(oldest_tx['timestamp'].replace('Z', '+00:00')))

            # Find funding sources (first SOL received)
            for tx in reversed(txs):  # Start from oldest
                native_transfers = tx.get('nativeTransfers', [])
                for transfer in native_transfers:
                    if transfer.get('toUserAccount') == addr:
                        funding_source = transfer.get('fromUserAccount')
                        if funding_source:
                            if first_iteration:
                                common_funding_sources.add(funding_source)
                            else:
                                common_funding_sources &= {funding_source}
                        break
                break

            first_iteration = False

        # Check creation time clustering (within 1 hour)
        if len(creation_times) >= 2:
            time_diffs = []
            for i in range(len(creation_times) - 1):
                diff_seconds = abs((creation_times[i+1] - creation_times[i]).total_seconds())
                time_diffs.append(diff_seconds)

            avg_diff = sum(time_diffs) / len(time_diffs)

            if avg_diff < 3600:  # Within 1 hour
                bundle_analysis['indicators'].append(f'Wallets created within {avg_diff/60:.1f} minutes of each other')
                bundle_analysis['confidence'] += 40

        # Check for common funding source
        if common_funding_sources:
            bundle_analysis['indicators'].append(f'Common funding source detected')
            bundle_analysis['confidence'] += 50

        # Determine if it's a bundle
        bundle_analysis['is_likely_bundle'] = bundle_analysis['confidence'] >= 60

        logger.info(f"Bundle analysis: {bundle_analysis['confidence']:.0f}% confidence")

        return bundle_analysis

    def get_parsed_transactions(
        self,
        wallet_address: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get human-readable parsed transactions

        Args:
            wallet_address: Wallet address
            limit: Max transactions

        Returns:
            List of parsed transaction objects
        """
        response = self._request(
            f"addresses/{wallet_address}/transactions",
            {'limit': limit, 'type': 'SWAP'}
        )

        if response:
            return response
        return []


def test_helius():
    """Test Helius client functionality"""
    from config import settings

    # Extract API key from RPC URL or use direct key
    if hasattr(settings, 'helius_api_key') and settings.helius_api_key:
        api_key = settings.helius_api_key
    else:
        # Extract from RPC URL
        import re
        match = re.search(r'api-key=([a-f0-9\-]+)', settings.solana_rpc_url)
        if match:
            api_key = match.group(1)
        else:
            print("❌ No Helius API key found")
            return

    client = HeliusClient(api_key)

    # Test dev wallet analysis
    print("\n🔍 Testing dev wallet analysis...")
    test_wallet = "YOUR_TEST_WALLET_HERE"  # Replace with actual wallet
    analysis = client.analyze_dev_wallet_history(test_wallet)

    print(f"\n📊 Analysis Results:")
    print(f"  Credibility Score: {analysis['credibility_score']:.1f}/100")
    print(f"  Tokens Created: {len(analysis['created_tokens'])}")
    print(f"  Large Sells: {len(analysis['large_sells'])}")
    print(f"  Suspicious Patterns: {len(analysis['suspicious_patterns'])}")

    for pattern in analysis['suspicious_patterns']:
        print(f"    ⚠️  {pattern}")

    for indicator in analysis['rug_pull_indicators']:
        print(f"    🚨 {indicator}")


if __name__ == "__main__":
    test_helius()
