import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x]