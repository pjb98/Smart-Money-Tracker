"""
Birdeye API Client for Wallet Intelligence
Identifies whale wallets, highly profitable wallets, and insider trading patterns
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger


class BirdeyeClient:
    """Client for Birdeye API - wallet and token analytics"""

    def __init__(self, api_key: str = "public", api_base: str = "https://public-api.birdeye.so"):
        """
        Initialize Birdeye client

        Args:
            api_key: Birdeye API key (use "public" for free tier)
            api_base: Base URL for Birdeye API
        """
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Initialized Birdeye client with API key: {api_key[:8]}...")

    async def _ensure_session(self):
        """Ensure HTTP session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-API-KEY": self.api_key,
                    "accept": "application/json"
                }
            )

    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_token_holders(
        self,
        token_address: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get top token holders for a token

        Args:
            token_address: Token mint address
            limit: Number of holders to fetch (max 10,000)
            offset: Offset for pagination

        Returns:
            List of holder dicts with address, balance, percentage
        """
        try:
            await self._ensure_session()

            url = f"{self.api_base}/defi/v3/token/holder"
            params = {
                "address": token_address,
                "limit": min(limit, 10000),
                "offset": offset
            }
            headers = {"x-chain": "solana"}

            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    holders = data.get('data', {}).get('items', [])
                    logger.debug(f"Fetched {len(holders)} holders for {token_address[:8]}...")
                    return holders
                else:
                    logger.warning(f"Failed to fetch holders: {response.status}")
                    # Try to read error message
                    try:
                        error = await response.json()
                        logger.warning(f"Error details: {error}")
                    except:
                        pass
                    return []

        except Exception as e:
            logger.error(f"Error fetching token holders for {token_address}: {e}")
            return []

    async def get_wallet_pnl(
        self,
        wallet_address: str,
        token_addresses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get profit/loss data for a wallet

        Args:
            wallet_address: Wallet address to analyze
            token_addresses: Optional list of specific tokens (max 50)

        Returns:
            Dict with PnL metrics
        """
        try:
            await self._ensure_session()

            url = f"{self.api_base}/wallet/v2/pnl"
            params = {
                "wallet": wallet_address
            }

            # Add token addresses if specified
            if token_addresses:
                params["tokens"] = ",".join(token_addresses[:50])

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Fetched PnL data for wallet {wallet_address[:8]}...")
                    return data
                else:
                    logger.warning(f"Failed to fetch wallet PnL: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error fetching wallet PnL for {wallet_address}: {e}")
            return {}

    async def analyze_wallet_intelligence(
        self,
        token_address: str,
        top_n_holders: int = 50
    ) -> Dict[str, Any]:
        """
        Comprehensive wallet intelligence analysis for a token

        Args:
            token_address: Token to analyze
            top_n_holders: How many top holders to analyze

        Returns:
            Dict with whale identification, profitable wallet analysis, etc.
        """
        logger.info(f"Analyzing wallet intelligence for {token_address[:8]}...")

        # 1. Get top holders
        holders = await self.get_token_holders(token_address, limit=top_n_holders)

        if not holders:
            logger.warning("No holder data available")
            return {
                'whale_count': 0,
                'total_holders_analyzed': 0,
                'highly_profitable_wallets': [],
                'whale_wallets': [],
                'insider_risk_score': 0
            }

        # 2. Analyze holder distribution
        whale_wallets = []
        highly_profitable_wallets = []
        total_supply = sum(h.get('amount', 0) for h in holders) if holders else 1

        for holder in holders:
            wallet_addr = holder.get('address', '')
            balance = holder.get('amount', 0)
            percentage = (balance / total_supply * 100) if total_supply > 0 else 0

            # Whale threshold: > 5% of total supply
            if percentage > 5.0:
                whale_wallets.append({
                    'address': wallet_addr,
                    'balance': balance,
                    'percentage': percentage,
                    'rank': holder.get('rank', 0)
                })

        # 3. Get PnL data for top holders (rate limited - only do top 10)
        logger.info("Analyzing PnL for top 10 holders...")
        for holder in holders[:10]:
            wallet_addr = holder.get('address', '')

            # Fetch wallet PnL
            pnl_data = await self.get_wallet_pnl(wallet_addr)

            if pnl_data:
                # Calculate success metrics
                tokens = pnl_data.get('data', {}).get('tokens', [])

                # Count profitable trades
                profitable_tokens = 0
                total_tokens_traded = len(tokens)
                total_roi = 0

                for token in tokens:
                    total_pnl_pct = token.get('total_percent', 0)
                    if total_pnl_pct > 0:
                        profitable_tokens += 1
                        total_roi += total_pnl_pct

                # Highly profitable: > 70% win rate
                win_rate = (profitable_tokens / total_tokens_traded * 100) if total_tokens_traded > 0 else 0
                avg_roi = total_roi / total_tokens_traded if total_tokens_traded > 0 else 0

                if win_rate > 70 and total_tokens_traded >= 5:
                    highly_profitable_wallets.append({
                        'address': wallet_addr,
                        'win_rate': win_rate,
                        'avg_roi': avg_roi,
                        'total_trades': total_tokens_traded,
                        'profitable_trades': profitable_tokens
                    })

            # Rate limiting - small delay between requests
            await asyncio.sleep(0.2)

        # 4. Calculate insider risk score
        # High risk if:
        # - Many whales (> 3)
        # - Whales hold > 30% combined
        # - Multiple highly profitable wallets present
        insider_risk_score = 0
        whale_count = len(whale_wallets)
        whale_total_pct = sum(w['percentage'] for w in whale_wallets)
        profitable_wallet_count = len(highly_profitable_wallets)

        if whale_count > 3:
            insider_risk_score += 3
        if whale_total_pct > 30:
            insider_risk_score += 3
        if profitable_wallet_count > 2:
            insider_risk_score += 2

        # 5. Identify potential insider wallets
        # Insiders = wallets that are both whales AND highly profitable
        insider_wallets = []
        whale_addrs = {w['address'] for w in whale_wallets}
        profitable_addrs = {w['address'] for w in highly_profitable_wallets}
        insider_addrs = whale_addrs & profitable_addrs

        for addr in insider_addrs:
            whale_info = next((w for w in whale_wallets if w['address'] == addr), None)
            profitable_info = next((w for w in highly_profitable_wallets if w['address'] == addr), None)

            if whale_info and profitable_info:
                insider_wallets.append({
                    'address': addr,
                    'percentage_held': whale_info['percentage'],
                    'win_rate': profitable_info['win_rate'],
                    'avg_roi': profitable_info['avg_roi']
                })

        logger.info(f"Found {whale_count} whales, {profitable_wallet_count} profitable wallets, {len(insider_wallets)} potential insiders")

        return {
            'whale_count': whale_count,
            'whale_wallets': whale_wallets,
            'whale_total_percentage': whale_total_pct,
            'highly_profitable_wallets': highly_profitable_wallets,
            'insider_wallets': insider_wallets,
            'insider_risk_score': insider_risk_score,  # 0-10 scale
            'total_holders_analyzed': len(holders),
            'analysis_timestamp': datetime.now().isoformat()
        }

    async def get_wallet_win_rate(
        self,
        wallet_address: str,
        min_trades: int = 5
    ) -> Dict[str, Any]:
        """
        Calculate wallet's win rate and performance metrics

        Args:
            wallet_address: Wallet to analyze
            min_trades: Minimum trades to consider valid

        Returns:
            Dict with win_rate, total_pnl, avg_roi, etc.
        """
        try:
            pnl_data = await self.get_wallet_pnl(wallet_address)

            if not pnl_data:
                return {
                    'win_rate': 0.0,
                    'total_pnl': 0.0,
                    'total_trades': 0,
                    'profitable_trades': 0,
                    'avg_roi': 0.0,
                    'confidence': 'LOW'
                }

            tokens = pnl_data.get('data', {}).get('tokens', [])
            total_trades = len(tokens)

            if total_trades < min_trades:
                return {
                    'win_rate': 0.0,
                    'total_pnl': 0.0,
                    'total_trades': total_trades,
                    'profitable_trades': 0,
                    'avg_roi': 0.0,
                    'confidence': 'LOW'
                }

            # Calculate metrics
            profitable_trades = 0
            total_pnl = 0.0
            total_roi = 0.0

            for token in tokens:
                pnl_pct = token.get('total_percent', 0)
                if pnl_pct > 0:
                    profitable_trades += 1
                total_roi += pnl_pct
                total_pnl += token.get('total_usd', 0)

            win_rate = profitable_trades / total_trades if total_trades > 0 else 0.0
            avg_roi = total_roi / total_trades if total_trades > 0 else 0.0

            # Confidence based on number of trades
            if total_trades >= 20:
                confidence = 'HIGH'
            elif total_trades >= 10:
                confidence = 'MEDIUM'
            else:
                confidence = 'LOW'

            return {
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'avg_roi': avg_roi,
                'confidence': confidence
            }

        except Exception as e:
            logger.error(f"Error calculating win rate for {wallet_address}: {e}")
            return {
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'total_trades': 0,
                'profitable_trades': 0,
                'avg_roi': 0.0,
                'confidence': 'LOW'
            }

    async def get_wallet_token_pnl(
        self,
        wallet_address: str,
        token_address: str
    ) -> Dict[str, Any]:
        """
        Get PnL for a specific wallet on a specific token

        Args:
            wallet_address: Wallet address
            token_address: Token address

        Returns:
            PnL data for that wallet/token pair
        """
        try:
            pnl_data = await self.get_wallet_pnl(wallet_address, token_addresses=[token_address])

            if not pnl_data:
                return {
                    'pnl_sol': 0.0,
                    'pnl_usd': 0.0,
                    'is_profitable': False,
                    'roi_pct': 0.0
                }

            tokens = pnl_data.get('data', {}).get('tokens', [])

            # Find the specific token
            token_data = next((t for t in tokens if t.get('address') == token_address), None)

            if not token_data:
                return {
                    'pnl_sol': 0.0,
                    'pnl_usd': 0.0,
                    'is_profitable': False,
                    'roi_pct': 0.0
                }

            pnl_usd = token_data.get('total_usd', 0)
            roi_pct = token_data.get('total_percent', 0)

            return {
                'pnl_sol': pnl_usd / 200,  # Rough conversion (assuming $200/SOL)
                'pnl_usd': pnl_usd,
                'is_profitable': pnl_usd > 0,
                'roi_pct': roi_pct
            }

        except Exception as e:
            logger.error(f"Error getting token PnL for {wallet_address}: {e}")
            return {
                'pnl_sol': 0.0,
                'pnl_usd': 0.0,
                'is_profitable': False,
                'roi_pct': 0.0
            }

    async def get_token_trades(
        self,
        token_address: str,
        trade_type: str = "all",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades for a token (optional - for more detailed analysis)

        Args:
            token_address: Token address
            trade_type: "buy", "sell", or "all"
            limit: Number of trades
            offset: Pagination offset

        Returns:
            List of trade dicts
        """
        try:
            await self._ensure_session()

            url = f"{self.api_base}/defi/v3/token/trade-data/single"
            params = {
                "address": token_address,
                "trade_type": trade_type,
                "limit": limit,
                "offset": offset
            }
            headers = {"x-chain": "solana"}

            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    trades = data.get('data', {}).get('items', [])
                    logger.debug(f"Fetched {len(trades)} trades for {token_address[:8]}...")
                    return trades
                else:
                    logger.warning(f"Failed to fetch trades: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching trades for {token_address}: {e}")
            return []


# Example usage
async def example():
    """Test the client"""
    client = BirdeyeClient(api_key="public")

    # Example token address (replace with real token)
    token = "So11111111111111111111111111111111111111112"  # Wrapped SOL

    # Analyze wallet intelligence
    intelligence = await client.analyze_wallet_intelligence(token, top_n_holders=20)

    import json
    print(json.dumps(intelligence, indent=2))

    await client.close()


if __name__ == "__main__":
    asyncio.run(example())
