# main.py
from hydrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="SecurityBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins"), # Ye line plugins auto-load karegi
        )

    async def start(self):
        await super().start()
        print("Bot is Online! 🚀")

    async def stop(self):
        await super().stop()
        print("Bot Stopped! 🛑")

if __name__ == "__main__":
    Bot().run()
