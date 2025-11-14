"""
Helper script to get Telegram channel IDs
Run this after setting up your Telegram API credentials
"""
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

# You'll need to fill these in
API_ID = 12345678  # Replace with your api_id from my.telegram.org
API_HASH = 'your_api_hash_here'  # Replace with your api_hash
PHONE = '+1234567890'  # Replace with your phone number (with country code)


async def get_channels():
    """List all channels you're subscribed to with their IDs"""

    # Create the client
    client = TelegramClient('session_name', API_ID, API_HASH)

    await client.start(phone=PHONE)

    print("Fetching your channels...")
    print("=" * 60)

    # Get all dialogs (chats)
    dialogs = await client.get_dialogs()

    channels = []
    for dialog in dialogs:
        if dialog.is_channel:
            channels.append({
                'title': dialog.title,
                'id': dialog.id,
                'username': dialog.entity.username if hasattr(dialog.entity, 'username') else None
            })

    # Print channels
    print(f"Found {len(channels)} channels:\n")
    for i, channel in enumerate(channels, 1):
        print(f"{i}. {channel['title']}")
        print(f"   ID: {channel['id']}")
        if channel['username']:
            print(f"   Username: @{channel['username']}")
        print()

    print("=" * 60)
    print("\nLook for 'Phanes' in the list above and copy its ID")
    print("Then add it to your .env file as PHANES_CHANNEL_ID")

    await client.disconnect()


if __name__ == "__main__":
    print("Telegram Channel ID Finder")
    print("=" * 60)
    print("This script will show all channels you're subscribed to.")
    print("Make sure you've joined the Phanes channel first!\n")

    asyncio.run(get_channels())
