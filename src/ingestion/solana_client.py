"""
Solana RPC client for fetching on-chain data
Handles transaction history, account info, and token metrics
"""
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import aiohttp
from loguru import logger
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from solders.signature import Signature


class SolanaClient:
    """Client for interacting with Solana blockchain"""

    def __init__(self, rpc_url: str, rate_limit_delay: float = 0.5):
        """
        Initialize Solana RPC client

        Args:
            rpc_url: Solana RPC endpoint URL
            rate_limit_delay: Delay between requests to avoid rate limiting
        """
        self.rpc_url = rpc_url
        self.rate_limit_delay = rate_limit_delay
        self.client = AsyncClient(rpc_url, commitment=Confirmed)
        logger.info(f"Initialized Solana client with RPC: {rpc_url}")

    async def close(self):
        """Close the client connection"""
        await self.client.close()

    async def get_token_transactions(
        self,
        token_address: str,
        limit: int = 1000,
        before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch transaction signatures for a token address

        Args:
            token_address: Token mint address
            limit: Maximum number of transactions to fetch
            before: Fetch transactions before this signature

        Returns:
            List of transaction signature info dicts
        """
        try:
            pubkey = Pubkey.from_string(token_address)

            params = {"limit": limit}
            if before:
                params["before"] = before

            response = await self.client.get_signatures_for_address(
                pubkey,
                **params
            )

            await asyncio.sleep(self.rate_limit_delay)

            if response.value:
                transactions = [
                    {
                        "signature": str(tx.signature),
                        "slot": tx.slot,
                        "block_time": tx.block_time,
                        "err": tx.err,
                    }
                    for tx in response.value
                ]
                logger.debug(f"Fetched {len(transactions)} transactions for {token_address}")
                return transactions
            return []

        except Exception as e:
            logger.error(f"Error fetching transactions for {token_address}: {e}")
            return []

    async def get_transaction_details(self, signature: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed transaction information

        Args:
            signature: Transaction signature

        Returns:
            Transaction details dict or None
        """
        try:
            sig = Signature.from_string(signature)
            response = await self.client.get_transaction(sig, max_supported_transaction_version=0)

            await asyncio.sleep(self.rate_limit_delay)

            if response.value:
                return {
                    "signature": signature,
                    "slot": response.value.slot,
                    "block_time": response.value.block_time,
                    "meta": response.value.transaction.meta,
                }
            return None

        except Exception as e:
            logger.error(f"Error fetching transaction details for {signature}: {e}")
            return None

    async def get_token_accounts(self, token_address: str) -> List[Dict[str, Any]]:
        """
        Fetch all token accounts (holders) for a token using getProgramAccounts

        Args:
            token_address: Token mint address

        Returns:
            List of token account info with owner and balance
        """
        try:
            from solders.rpc.filter import Memcmp
            from solders.rpc.config import RpcAccountInfoConfig

            mint_pubkey = Pubkey.from_string(token_address)

            # SPL Token program ID
            TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

            # Create memcmp filter for mint address
            # In SPL token account data, mint is at offset 0 (first 32 bytes)
            mint_filter = Memcmp(offset=0, bytes=str(mint_pubkey))

            # Get all token accounts for this mint
            response = await self.client.get_program_accounts(
                TOKEN_PROGRAM_ID,
                encoding="jsonParsed",
                filters=[mint_filter],
                config=RpcAccountInfoConfig(data_slice=None)
            )

            await asyncio.sleep(self.rate_limit_delay)

            if response.value:
                accounts = []
                for acc in response.value:
                    try:
                        # Parse the account data
                        parsed = acc.account.data.parsed
                        info = parsed.get("info", {})
                        token_amount = info.get("tokenAmount", {})

                        # Only include accounts with balance > 0
                        ui_amount = token_amount.get("uiAmount", 0)
                        if ui_amount and ui_amount > 0:
                            accounts.append({
                                "owner": info.get("owner", ""),
                                "amount": ui_amount,
                                "decimals": token_amount.get("decimals", 0),
                            })
                    except Exception as e:
                        logger.debug(f"Error parsing token account: {e}")
                        continue

                logger.info(f"Fetched {len(accounts)} token holders for {token_address}")
                return accounts
            return []

        except Exception as e:
            logger.error(f"Error fetching token accounts for {token_address}: {e}")
            return []

    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch account information

        Args:
            address: Account address

        Returns:
            Account info dict or None
        """
        try:
            pubkey = Pubkey.from_string(address)
            response = await self.client.get_account_info(pubkey)

            await asyncio.sleep(self.rate_limit_delay)

            if response.value:
                return {
                    "address": address,
                    "lamports": response.value.lamports,
                    "owner": str(response.value.owner),
                    "executable": response.value.executable,
                    "rent_epoch": response.value.rent_epoch,
                }
            return None

        except Exception as e:
            logger.error(f"Error fetching account info for {address}: {e}")
            return None

    async def get_token_supply(self, token_address: str) -> Optional[float]:
        """
        Get total supply of a token

        Args:
            token_address: Token mint address

        Returns:
            Total supply or None
        """
        try:
            pubkey = Pubkey.from_string(token_address)
            response = await self.client.get_token_supply(pubkey)

            await asyncio.sleep(self.rate_limit_delay)

            if response.value:
                return float(response.value.ui_amount)
            return None

        except Exception as e:
            logger.error(f"Error fetching token supply for {token_address}: {e}")
            return None

    async def get_transactions_in_timeframe(
        self,
        token_address: str,
        start_time: datetime,
        end_time: datetime,
        max_transactions: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Fetch all transactions for a token within a time window

        Args:
            token_address: Token mint address
            start_time: Start of time window
            end_time: End of time window
            max_transactions: Maximum transactions to fetch

        Returns:
            List of transactions within timeframe
        """
        transactions = []
        before_signature = None
        start_ts = start_time.timestamp()
        end_ts = end_time.timestamp()

        try:
            while len(transactions) < max_transactions:
                batch = await self.get_token_transactions(
                    token_address,
                    limit=min(1000, max_transactions - len(transactions)),
                    before=before_signature
                )

                if not batch:
                    break

                # Filter by time
                filtered = [
                    tx for tx in batch
                    if tx["block_time"] and start_ts <= tx["block_time"] <= end_ts
                ]
                transactions.extend(filtered)

                # Check if we've gone past the start time
                if batch[-1]["block_time"] and batch[-1]["block_time"] < start_ts:
                    break

                before_signature = batch[-1]["signature"]

            logger.info(f"Fetched {len(transactions)} transactions for {token_address} in timeframe")
            return transactions

        except Exception as e:
            logger.error(f"Error fetching transactions in timeframe: {e}")
            return transactions


# Example usage
async def main():
    client = SolanaClient("https://api.mainnet-beta.solana.com")

    # Example: Get token transactions
    token_address = "So11111111111111111111111111111111111111112"  # Wrapped SOL
    transactions = await client.get_token_transactions(token_address, limit=10)
    print(f"Found {len(transactions)} transactions")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
