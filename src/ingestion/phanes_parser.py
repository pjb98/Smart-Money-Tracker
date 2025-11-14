"""
Phanes Telegram Bot Parser
Scrapes and parses Phanes bot scan responses for sentiment and popularity signals
"""
import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from telethon import TelegramClient, events
from telethon.tl.types import Message
import json


class PhanesParser:
    """Parser for Phanes Telegram bot scan responses"""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        channel_id: int,
        session_name: str = "phanes_session"
    ):
        """
        Initialize Phanes parser

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: Phone number for authentication
            channel_id: Phanes channel/group ID
            session_name: Session file name
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.channel_id = channel_id
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None
        self.scan_history: List[Dict[str, Any]] = []

        logger.info("Initialized Phanes parser")

    async def connect(self):
        """Connect to Telegram"""
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            logger.info("Connected to Telegram successfully")

            # Verify channel access
            try:
                entity = await self.client.get_entity(self.channel_id)
                logger.info(f"Connected to channel: {entity.title if hasattr(entity, 'title') else 'Unknown'}")
            except Exception as e:
                logger.error(f"Could not access channel {self.channel_id}: {e}")

        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram")

    def parse_scan_message(self, message_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse a Phanes bot scan message

        Expected format (example):
        Token: MOCKTOKEN ($MOCK)
        Scans: 1,234
        Scan Velocity: 45/hour
        Rank: #12
        Risk: LOW
        Sentiment: Bullish

        Args:
            message_text: Raw message text from bot

        Returns:
            Parsed scan data dict or None
        """
        try:
            data = {}

            # Extract token name and symbol
            token_match = re.search(r'Token:\s*(.+?)\s*\((\$\w+)\)', message_text, re.IGNORECASE)
            if token_match:
                data['token_name'] = token_match.group(1).strip()
                data['token_symbol'] = token_match.group(2).strip()

            # Extract scan count
            scan_match = re.search(r'Scans?:\s*([\d,]+)', message_text, re.IGNORECASE)
            if scan_match:
                data['scan_count'] = int(scan_match.group(1).replace(',', ''))

            # Extract scan velocity
            velocity_match = re.search(r'Scan\s+Velocity:\s*([\d,]+)\s*/\s*hour', message_text, re.IGNORECASE)
            if velocity_match:
                data['scan_velocity'] = int(velocity_match.group(1).replace(',', ''))

            # Extract rank
            rank_match = re.search(r'Rank:\s*#(\d+)', message_text, re.IGNORECASE)
            if rank_match:
                data['popularity_rank'] = int(rank_match.group(1))

            # Extract risk level
            risk_match = re.search(r'Risk:\s*(\w+)', message_text, re.IGNORECASE)
            if risk_match:
                risk_level = risk_match.group(1).upper()
                data['rug_warning'] = risk_level in ['HIGH', 'CRITICAL']
                data['risk_level'] = risk_level

            # Extract sentiment
            sentiment_match = re.search(r'Sentiment:\s*(\w+)', message_text, re.IGNORECASE)
            if sentiment_match:
                sentiment = sentiment_match.group(1).lower()
                data['sentiment'] = sentiment
                # Convert to numeric score
                sentiment_scores = {
                    'very bullish': 1.0,
                    'bullish': 0.5,
                    'neutral': 0.0,
                    'bearish': -0.5,
                    'very bearish': -1.0
                }
                data['sentiment_score'] = sentiment_scores.get(sentiment, 0.0)

            # Extract contract address if present
            contract_match = re.search(r'Contract:\s*([A-Za-z0-9]{32,44})', message_text)
            if contract_match:
                data['contract_address'] = contract_match.group(1)

            if data:
                data['timestamp'] = datetime.now().isoformat()
                data['raw_message'] = message_text
                return data

            return None

        except Exception as e:
            logger.error(f"Error parsing scan message: {e}")
            return None

    async def fetch_recent_scans(
        self,
        hours_back: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch and parse recent Phanes scan messages

        Args:
            hours_back: How many hours of history to fetch
            limit: Maximum messages to fetch

        Returns:
            List of parsed scan dicts
        """
        if not self.client:
            await self.connect()

        scans = []
        try:
            since_time = datetime.now() - timedelta(hours=hours_back)

            async for message in self.client.iter_messages(
                self.channel_id,
                limit=limit
            ):
                if message.date < since_time:
                    break

                if message.text:
                    parsed = self.parse_scan_message(message.text)
                    if parsed:
                        parsed['message_id'] = message.id
                        parsed['message_date'] = message.date.isoformat()
                        scans.append(parsed)

            logger.info(f"Fetched {len(scans)} Phanes scans from last {hours_back} hours")
            return scans

        except Exception as e:
            logger.error(f"Error fetching recent scans: {e}")
            return scans

    async def listen_for_scans(self, callback=None):
        """
        Listen for new Phanes scan messages in real-time

        Args:
            callback: Optional async function to call with each new scan
        """
        if not self.client:
            await self.connect()

        @self.client.on(events.NewMessage(chats=self.channel_id))
        async def handler(event: events.NewMessage.Event):
            message: Message = event.message
            if message.text:
                parsed = self.parse_scan_message(message.text)
                if parsed:
                    parsed['message_id'] = message.id
                    parsed['message_date'] = message.date.isoformat()
                    self.scan_history.append(parsed)

                    logger.info(f"New scan detected: {parsed.get('token_symbol', 'Unknown')}")

                    if callback:
                        await callback(parsed)

        logger.info("Started listening for Phanes scans...")
        await self.client.run_until_disconnected()

    def get_token_scan_metrics(
        self,
        token_address: str,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Aggregate scan metrics for a specific token

        Args:
            token_address: Token contract address
            lookback_hours: Hours to look back

        Returns:
            Aggregated metrics dict
        """
        since_time = datetime.now() - timedelta(hours=lookback_hours)

        relevant_scans = [
            scan for scan in self.scan_history
            if scan.get('contract_address') == token_address
            and datetime.fromisoformat(scan['timestamp']) > since_time
        ]

        if not relevant_scans:
            return {
                'token_address': token_address,
                'scan_count': 0,
                'avg_scan_velocity': 0,
                'latest_rank': None,
                'rug_warning': False,
                'avg_sentiment_score': 0
            }

        # Sort by timestamp
        relevant_scans.sort(key=lambda x: x['timestamp'], reverse=True)
        latest = relevant_scans[0]

        return {
            'token_address': token_address,
            'scan_count': len(relevant_scans),
            'avg_scan_velocity': sum(s.get('scan_velocity', 0) for s in relevant_scans) / len(relevant_scans),
            'latest_rank': latest.get('popularity_rank'),
            'rug_warning': latest.get('rug_warning', False),
            'risk_level': latest.get('risk_level', 'UNKNOWN'),
            'avg_sentiment_score': sum(s.get('sentiment_score', 0) for s in relevant_scans) / len(relevant_scans),
            'latest_sentiment': latest.get('sentiment', 'neutral'),
            'scan_history': relevant_scans
        }


class MockPhanesParser(PhanesParser):
    """Mock Phanes parser for testing without Telegram access"""

    def __init__(self):
        logger.info("Initialized MOCK Phanes parser")
        self.scan_history = []

    async def connect(self):
        """Mock connection"""
        logger.info("Mock Phanes parser connected")

    async def disconnect(self):
        """Mock disconnection"""
        logger.info("Mock Phanes parser disconnected")

    async def fetch_recent_scans(
        self,
        hours_back: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Generate mock scan data"""
        mock_scans = []

        for i in range(min(limit, 10)):
            timestamp = datetime.now() - timedelta(hours=hours_back - i * 2)
            mock_scans.append({
                'token_name': f'Mock Token {i}',
                'token_symbol': f'$MOCK{i}',
                'scan_count': 100 + i * 50,
                'scan_velocity': 10 + i * 2,
                'popularity_rank': i + 1,
                'rug_warning': i % 5 == 0,  # Every 5th token has rug warning
                'risk_level': 'HIGH' if i % 5 == 0 else 'LOW',
                'sentiment': ['bullish', 'neutral', 'bearish'][i % 3],
                'sentiment_score': [0.5, 0.0, -0.5][i % 3],
                'contract_address': f"MOCK{'x' * 40}{i}",
                'timestamp': timestamp.isoformat(),
                'message_id': 1000 + i,
                'message_date': timestamp.isoformat()
            })

        logger.info(f"Generated {len(mock_scans)} mock Phanes scans")
        return mock_scans


# Example usage
async def main():
    # Use mock parser for testing
    parser = MockPhanesParser()

    await parser.connect()

    # Fetch recent scans
    scans = await parser.fetch_recent_scans(hours_back=48, limit=20)
    print(f"Fetched {len(scans)} scans:")
    for scan in scans[:5]:
        print(f"  - {scan['token_symbol']}: {scan['scan_count']} scans, rank #{scan['popularity_rank']}")

    await parser.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
