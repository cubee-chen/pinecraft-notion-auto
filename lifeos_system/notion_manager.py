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

    # Get all users and projects and return user_data and project_data
    async def get_all_users_and_projects(self): 

        # run at program start

        # Get all properties from all the users
        print("Fetching Notion Page Data From All Users...")
        all_user_metadata = await self.notion.databases.query(
            database_id=USER_NOTION
        )

        async def fetch_user_data(user_metadata):
            notion_id = user_metadata["id"]
            last_edited_time = NotionManager.notion_time_to_seconds(user_metadata["last_edited_time"])
            notion_properties = user_metadata["properties"]
            notion_content = await self.notion.blocks.children.list(notion_id)
            return {
                "notion_id": notion_id,
                "last_edited_time": last_edited_time,
                "notion_properties": notion_properties,
                "notion_content": notion_content["results"]
            }

        # Run all content fetches concurrently
        user_data = await asyncio.gather(*[fetch_user_data(user) for user in all_user_metadata["results"]])

        # Get all properties from all the projects
        print("Fetching Notion Page Data From All Projects...")
        all_project_metadata = await self.notion.databases.query(
            database_id=PROJECT_NOTION
        )

        async def fetch_project_data(project_metadata):
            notion_id = project_metadata["id"]
            last_edited_time = NotionManager.notion_time_to_seconds(project_metadata["last_edited_time"])
            notion_properties = project_metadata["properties"]
            notion_content = await self.notion.blocks.children.list(notion_id)
            return {
                "notion_id": notion_id,
                "last_edited_time": last_edited_time,
                "notion_properties": notion_properties,
                "notion_content": notion_content["results"]
            }

        # Run all content fetches concurrently
        project_data = await asyncio.gather(*[fetch_project_data(project) for project in all_project_metadata["results"]])

        return user_data, project_data

    # Fetch a single user's data from Notion by Notion ID.  
    async def get_user_by_notion_id(self, notion_id):
        
        # Query the Notion database to find the specific user
        print(f"Fetching Notion Page Data for User ID: {notion_id}...")
        user_metadata = await self.notion.databases.query(
            database_id=USER_NOTION,
            filter={"property": "id", "text": {"equals": notion_id}}  # Adjust filter based on Notion schema
        )

        if not user_metadata["results"]:
            print(f"No user found with Notion ID: {notion_id}")
            return None

        user_metadata = user_metadata["results"][0]  # Get the first matching user

        async def fetch_user_data(user_metadata):
            last_edited_time = NotionManager.notion_time_to_seconds(user_metadata["last_edited_time"])
            notion_properties = user_metadata["properties"]
            notion_content = await self.notion.blocks.children.list(notion_id)
            return {
                "notion_id": notion_id,
                "last_edited_time": last_edited_time,
                "notion_properties": notion_properties,
                "notion_content": notion_content["results"]
            }

        # Fetch user data asynchronously
        user_data = await fetch_user_data(user_metadata)

        return user_data
    
    # Fetch a single project's data from Notion by Notion ID.
    async def get_project_by_notion_id(self, notion_id):
        
        # Query the Notion database to find the specific project
        print(f"Fetching Notion Page Data for User ID: {notion_id}...")
        project_metadata = await self.notion.databases.query(
            database_id=PROJECT_NOTION,
            filter={"property": "id", "text": {"equals": notion_id}}  # Adjust filter based on Notion schema
        )

        if not project_metadata["results"]:
            print(f"No project found with Notion ID: {notion_id}")
            return None

        project_metadata = project_metadata["results"][0]  # Get the first matching project

        async def fetch_project_data(project_metadata):
            last_edited_time = NotionManager.notion_time_to_seconds(project_metadata["last_edited_time"])
            notion_properties = project_metadata["properties"]
            notion_content = await self.notion.blocks.children.list(notion_id)
            return {
                "notion_id": notion_id,
                "last_edited_time": last_edited_time,
                "notion_properties": notion_properties,
                "notion_content": notion_content["results"]
            }

        # Fetch project data asynchronously
        project_data = await fetch_project_data(project_metadata)

        return project_data
    
    async def extract_all_calendars(self, user_data, project_data):

        # get calendar db id from user and project page content
        # run at program start

        for user in user_data:
            notion_content = user["notion_content"]
            for block in notion_content:
                if block["type"] == "child_database":
                    db_name = NotionManager.get_db_name(block["child_database"]["title"])
                    user[db_name] = block["id"]
        
        for project in project_data:
            notion_content = project["notion_content"]
            for block in notion_content:
                if block["type"] == "child_database":
                    db_name = NotionManager.get_db_name(block["child_database"]["title"])
                    project[db_name] = block["id"]

        return user_data, project_data

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

    # Maps database title to standardized name
    @staticmethod
    def get_db_name(db_title):
        # standardized db names
        map = {
            "課表": "class_schedule",
            "行事曆": "schedule",
            "專案": "projects",
        }
        for title in map:
            if title in db_title:
                return map[title]
        return "unknown"

# ================= Test Run =================

if __name__ == "__main__":
    notion_manager = NotionManager()
    async def test_run():
        user_data, project_data = await notion_manager.get_all_users_and_projects()
        user_data, project_data = await notion_manager.extract_all_calendars(user_data, project_data)
        # NotionManager.output_to_json({"user_data": user_data, "project_data": project_data}, "data_sample/sample_notion_manager_output.json")

    asyncio.run(test_run())