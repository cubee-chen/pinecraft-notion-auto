import os
from dotenv import load_dotenv
from pprint import pprint
import asyncio
import json
from datetime import datetime

from notion_client import AsyncClient

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

        # Instance Variables
        self.notion = AsyncClient(auth=NOTION_TOKEN)
        self.users = []

    async def get_all_users_and_projects(self):

        # get all users and projects and save them in tracked_document
        # run at program start

        # get all properties from all the users
        all_user_metadata =  await self.notion.databases.query(**{
            "database_id": USER_NOTION,
            # No filters yet
        })

        # get all content from notion
        user_data = [{
            "notion_id": user_metadata["id"],
            "last_edited_time": NotionManager.notion_time_to_seconds(user_metadata["last_edited_time"]),
            "notion_properties": user_metadata["properties"],
            "notion_content": (await self.notion.blocks.children.list(user_metadata["id"]))["results"] 
        } for user_metadata in all_user_metadata["results"]]

        NotionManager.output_to_json(user_data)

    async def get_all_calendars(self):

        # get calendar db id from user and project page content
        # run at program start
        pass

    def get_last_updated_time(self):
        pass

    # ============ Utility Functions for Notion ============

    # Converts notion datetime to seconds since epoch
    @staticmethod
    def notion_time_to_seconds(last_edited_time):
        return int(datetime.strptime(last_edited_time, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())
    
    # Saves object to JSON
    @staticmethod
    def output_to_json(object, filename="output.json"):
        with open(filename, "w") as file:
            file.write(json.dumps(object, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    notion_manager = NotionManager()
    asyncio.run(notion_manager.get_all_users_and_projects())