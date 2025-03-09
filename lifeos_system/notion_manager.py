import os
from dotenv import load_dotenv
from pprint import pprint

from notion_client import Client

# =========== Load Environmental Variables ===========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

USER_NOTION = os.getenv("USER_NOTION")
PROJECT_NOTION = os.getenv("PROJECT_NOTION")

# =================== Define Class ===================
class NotionManager:
    def __init__(self):
        global NOTION_TOKEN

        # Instance Variables
        self.notion = Client(auth=NOTION_TOKEN)