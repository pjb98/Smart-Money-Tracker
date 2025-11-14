"""
PumpPortal WebSocket client for real-time Pump.fun data
Monitors token launches and Raydium migrations
"""
import asyncio
import json
import websockets
from typing import Optional, Callable, Dict, Any
from loguru import logger
from datetime import datetime


class PumpPortalClient:
    """WebSocket client for PumpPortal real-time data"""

    def __init__(self, ws_url: str = "wss://pumpportal.fun/api/data"):
        """
        Initialize PumpPortal WebSocket client

        Args:
            ws_url: WebSocket endpoint URL
        """
        self.ws_url = ws_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.migration_callback: Optional[Callable] = None
        self.new_token_callback: Optional[Callable] = None
        logger.info(f"Initialized PumpPortal client for {ws_url}")

    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            logger.info("✅ Connected to PumpPortal WebSocket")
        except Exception as e:
            logger.error(f"Failed to connect to PumpPortal: {e}")
            raise

    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from PumpPortal")

    async def subscribe_migrations(self):
        """
        Subscribe to Raydium migration events
        This captures when tokens graduate from Pump.fun bonding curve to Raydium
        """
        if not self.websocket:
            raise Exception("Not connected. Call connect() first.")

        payload = {
            "method": "subscribeMigration"
        }

        await self.websocket.send(json.dumps(payload))
        logger.info("📡 Subscribed to Raydium migrations")

    async def subscribe_new_tokens(self):
        """Subscribe to new token creation events"""
        if not self.websocket:
            raise Exception("Not connected. Call connect() first.")

        payload = {
            "method": "subscribeNewToken"
        }

        await self.websocket.send(json.dumps(payload))
        logger.info("📡 Subscribed to new token launches")

    async def subscribe_token_trades(self, token_addresses: list):
        """
        Subscribe to trades for specific tokens

        Args:
            token_addresses: List of token mint addresses
        """
        if not self.websocket:
            raise Exception("Not connected. Call connect() first.")

        payload = {
            "method": "subscribeTokenTrade",
            "keys": token_addresses
        }

        await self.websocket.send(json.dumps(payload))
        logger.info(f"📡 Subscribed to trades for {len(token_addresses)} tokens")

    async def unsubscribe_migrations(self):
        """Unsubscribe from migration events"""
        if not self.websocket:
            return

        payload = {
            "method": "unsubscribeMigration"
        }

        await self.websocket.send(json.dumps(payload))
        logger.info("Unsubscribed from migrations")

    def on_migration(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register callback for migration events

        Args:
            callback: Async function to call when migration occurs
        """
        self.migration_callback = callback

    def on_new_token(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Register callback for new token events

        Args:
            callback: Async function to call when new token is created
        """
        self.new_token_callback = callback

    async def listen(self):
        """
        Main listening loop - processes incoming WebSocket messages
        Call this after subscribing to events
        """
        if not self.websocket:
            raise Exception("Not connected. Call connect() first.")

        logger.info("👂 Listening for PumpPortal events...")

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)

                    # Determine event type and call appropriate callback
                    # Migration events
                    if self._is_migration_event(data) and self.migration_callback:
                        await self.migration_callback(data)

                    # New token events
                    elif self._is_new_token_event(data) and self.new_token_callback:
                        await self.new_token_callback(data)

                    # Log unknown event types for debugging
                    else:
                        logger.debug(f"Received event: {data.get('type', 'unknown')}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
            self.is_connected = False

    def _is_migration_event(self, data: dict) -> bool:
        """Check if event is a Pump.fun migration to Raydium"""
        # PumpPortal migration events will have specific fields
        # Adjust based on actual API response structure
        is_migration = (
            data.get('txType') == 'migration' or
            'migration' in str(data.get('type', '')).lower() or
            'raydium' in str(data).lower()
        )

        if not is_migration:
            return False

        # Filter for Pump.fun tokens only
        # Pump.fun program ID: 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P
        # Check if event contains Pump.fun indicators
        PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

        # Log raw event for debugging (first time only)
        if not hasattr(self, '_logged_migration_example'):
            logger.debug(f"Raw migration event example: {json.dumps(data, indent=2)}")
            self._logged_migration_example = True

        # Check for Pump.fun indicators in the event
        event_str = json.dumps(data).lower()

        # Filter OUT non-Pump.fun launchpads
        non_pumpfun_indicators = ['launchlab', 'moonshot', 'jupiter']
        if any(indicator in event_str for indicator in non_pumpfun_indicators):
            logger.info(f"Skipping non-Pump.fun migration: {data.get('symbol', 'UNKNOWN')}")
            return False

        # Check for Pump.fun program ID or bonding curve
        if PUMPFUN_PROGRAM_ID.lower() in event_str:
            return True

        # If program ID not found but has pump.fun indicators
        if 'pump' in event_str and 'fun' in event_str:
            return True

        # Default to accepting migrations if we can't determine
        # (can make this stricter by returning False)
        logger.warning(f"Migration without clear Pump.fun indicators: {data.get('symbol', 'UNKNOWN')}")
        return True

    def _is_new_token_event(self, data: dict) -> bool:
        """Check if event is a new token creation"""
        return (
            data.get('txType') == 'create' or
            data.get('type') == 'newToken'
        )

    async def run(self, on_migration=None, on_new_token=None):
        """
        Convenience method to connect, subscribe, and listen

        Args:
            on_migration: Callback for migration events
            on_new_token: Callback for new token events
        """
        await self.connect()

        # Register callbacks
        if on_migration:
            self.on_migration(on_migration)
            await self.subscribe_migrations()

        if on_new_token:
            self.on_new_token(on_new_token)
            await self.subscribe_new_tokens()

        # Start listening
        await self.listen()


# Example usage
async def example():
    """Example usage of PumpPortal client"""

    async def handle_migration(event: dict):
        """Handle migration event"""
        logger.info(f"🚀 MIGRATION DETECTED: {event}")
        # Extract token address and process

    async def handle_new_token(event: dict):
        """Handle new token event"""
        logger.info(f"✨ NEW TOKEN: {event}")

    # Create client
    client = PumpPortalClient()

    try:
        # Connect and subscribe
        await client.run(
            on_migration=handle_migration,
            on_new_token=handle_new_token
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(example())
