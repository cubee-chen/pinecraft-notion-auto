import os
from dotenv import load_dotenv
from pprint import pprint
import asyncio
import json
from datetime import datetime

from notion_client import AsyncClient

from synced_document import SyncedDocumentManager
from cache import Cache

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

    # =================== Startup Functions ===================

    # 1. Get all users and projects and return user_data and project_data
    async def get_all_users_and_projects(self, cache: Cache): 

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
            if len(user_metadata["properties"]["姓名"]["people"]) > 0:
                user_id = user_metadata["properties"]["姓名"]["people"][0]["id"]
                if user_id:
                    cache.update_user_id_to_notion_id(user_id, notion_id)
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

    # 2. Extract child db ids from a Notion page
    async def extract_child_db_ids(self, data, cache: Cache):

        # get db ids from parent page content
        # run at program start
        # print("Extracting Child Databases...")
        for entry in data:
            notion_content = entry["notion_content"]
            for block in notion_content:
                if block["type"] == "child_database":
                    db_name = NotionManager.get_db_name(block["child_database"]["title"])
                    entry[db_name] = block["id"]
                    if db_name == "schedule":
                        cache.update_notion_id_to_schedule_id(entry["notion_id"], block["id"])

        return data

    # 3. Fetch all schedule data collected in project_data
    async def get_all_schedules_from_project(self, project_data):

        schedule_data = []
        
        print("Fetching Schedules From All Projects' Homepages...")
        async def fetch_schedule(project, schedule_data):
            """Fetch schedule data for a single project."""
            if "schedule" not in project:
                print(f"No Schedule DB Exist in User: {project['notion_id']}")
                return  #! Skip projects without schedules
            
            schedule_id = project["schedule"]
            schedules = (await self.notion.databases.query(database_id=schedule_id))["results"]
            
            schedule_data.extend(await asyncio.gather(*[
                fetch_schedule_details(schedule, project['notion_id']) for schedule in schedules
            ]))

        async def fetch_schedule_details(schedule, r_parent_db):
            # Fetch schedule details for each schedule item.
            last_edited_time = NotionManager.notion_time_to_seconds(schedule["last_edited_time"])
            return {
                "notion_id": schedule["id"],
                "notion_properties": schedule["properties"],
                "notion_content": (await self.notion.blocks.children.list(schedule["id"]))["results"],
                "r_parent_db": r_parent_db,
                "last_edited_time": last_edited_time
            }

        # Run all schedule fetches in parallel
        await asyncio.gather(*(fetch_schedule(project, schedule_data) for project in project_data))

        return schedule_data

    # 4. Delete all schedule data collected in user_data that corresponds to one in project_data
    #    and insert new schedule data by cloing these in project data
    async def renew_all_schedules_in_user(self, user_data, schedule_data, cache: Cache, synced_document_manager: SyncedDocumentManager):
        
        # Delete
        print("Deleting all Outdated Schedules...")
        async def process_user(user):
            if "schedule" not in user:
                return
            #! prop: "[勿動] IS任務"
            pages_to_delete = await self.notion.databases.query(user["schedule"], **{
                "property": "所屬專案",
                "rich_text": {"is_not_empty": True}
            })
            page_ids = [page["id"] for page in pages_to_delete["results"]]
            await asyncio.gather(*(self.delete_page_by_notion_id(page_id) for page_id in page_ids))

        await asyncio.gather(*(process_user(user) for user in user_data))
        
        # Insert
        print("Inserting New Schedules to User Notion...")
        async def insert_schedules(schedule):
            people = schedule["notion_properties"]["負責人"]["people"]
            for user in people:
                user_id = user["id"]
                notion_id = cache.get_user_id_to_notion_id(user_id)
                if not notion_id:
                    #! Handle cache not yet saved user_id -> notion_id mapping
                    # might be because a user shared the project to other users
                    continue
                # Add schedule data to a specific user's schedule database
                user_schedule_id = cache.get_notion_id_to_schedule_id(notion_id)
                if not user_schedule_id:
                    #! Handle cache not yet saved notion_id -> schedule_id mapping
                    # brute search?
                    continue
                new_schedule_id = await self.create_user_schedule(user_schedule_id, schedule)

                # Add link to synced document
                synced_document_manager.create_instance_link(schedule["notion_id"], new_schedule_id, is_user=True)
        
        await asyncio.gather(*(insert_schedules(schedule) for schedule in schedule_data))
        
        # Insert schedule to DB
        print("Inserting All Schedules to the Database...")
        async def process_schedule(schedule):
            if synced_document_manager.schedule_notion_id_is_synced(schedule["notion_id"]):
                # Add virtual link with physical element for the project's schedule
                synced_document_manager.create_instance_link(schedule["notion_id"], schedule["notion_id"], is_user=False)
                # Save the physical page to the database
                await synced_document_manager.save_version_by_notion_id(schedule["notion_id"], schedule, schedule["last_edited_time"])
        await asyncio.gather(*[process_schedule(schedule) for schedule in schedule_data])
        # synced_document_manager.print()
        return True
    
    # =============== Dynamic Runtime Functions ===============

    # Fetch a single user's data from Notion by Notion ID.  
    async def get_user_by_notion_id(self, notion_id):
        
        # Query the Notion database to find the specific user
        # print(f"Fetching Notion Page Data for User ID: {notion_id}...")
        user_metadata = await self.notion.pages.retrieve(notion_id)

        if not user_metadata:
            print(f"No user found with Notion ID: {notion_id}")
            return None

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
        # print(f"Fetching Notion Page Data for User ID: {notion_id}...")
        project_metadata = await self.notion.pages.retrieve(notion_id)

        if not project_metadata:
            print(f"No project found with Notion ID: {notion_id}")
            return None

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
    
    # Fetch a single schedule's data from Notion by Notion ID.
    async def get_schedule_by_notion_id(self, notion_id, includes_content=True):
        
        # Query the Notion database to find the specific schedule
        # print(f"Fetching Notion Page Data for User ID: {notion_id}...")
        schedule_metadata = await self.notion.pages.retrieve(notion_id)

        if not schedule_metadata:
            print(f"No schedule found with Notion ID: {notion_id}")
            return None

        async def fetch_schedule_data(schedule_metadata):
            last_edited_time = NotionManager.notion_time_to_seconds(schedule_metadata["last_edited_time"])
            notion_properties = schedule_metadata["properties"]
            if includes_content:
                notion_content = await self.notion.blocks.children.list(notion_id)
            else:
                notion_content = {"results": []}
            return {
                "notion_id": notion_id,
                "last_edited_time": last_edited_time,
                "notion_properties": notion_properties,
                "notion_content": notion_content["results"]
            }

        # Fetch schedule data asynchronously
        schedule_data = await fetch_schedule_data(schedule_metadata)

        return schedule_data

    # Delete data 
    async def delete_page_by_notion_id(self, notion_id):
        await self.notion.pages.update(notion_id, archived=True)
        return True

    # Create user schedule page
    async def create_user_schedule(self, schedule_db_id, schedule):
        mapped_properties = NotionManager.convert_project_schedule_to_user_schedule(schedule["r_parent_db"], schedule["notion_properties"])
        new_page = await self.notion.pages.create(
            parent={"database_id": schedule_db_id},
            properties=mapped_properties
        )
        return new_page["id"]

    # Update user schedule page to the newest version
    async def update_user_schedule(self, schedule_notion_id, schedule):
        mapped_properties = NotionManager.convert_project_schedule_to_user_schedule(schedule["r_parent_db"], schedule["notion_properties"])
        await self.notion.pages.update(schedule_notion_id, properties=mapped_properties)

        #! Notion currently doesn't allow direct content editing yet
        await self.notion.blocks.children.append(schedule_notion_id, children=schedule["notion_content"])

    async def update_project_schedule(self, schedule_notion_id, schedule):
        mapped_properties = NotionManager.filter_project_schedule_before_updating_notion(schedule["notion_properties"])
        await self.notion.pages.update(schedule_notion_id, properties=mapped_properties)

        #! Notion currently doesn't allow direct content editing yet
        await self.notion.blocks.children.append(schedule_notion_id, children=schedule["notion_content"])

    def get_last_edited_time_time(self):
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
            "待辦事項": "schedule",
            "代辦事項": "schedule",
            "任務資料庫": "schedule",
            "專案": "projects",
        }
        for title in map:
            if title in db_title:
                return map[title]
        return "unknown"

    # Extract plain text from rich text
    @staticmethod
    def extract_from_rich_text(rich_text):
        ret = ""
        for text in rich_text:
            ret += text["plain_text"]
        return ret

    @staticmethod
    def convert_project_schedule_to_user_schedule(project_notion_id, properties):
        map_properties = {
            "項目": properties["任務名稱"] if "任務名稱" in properties else { "title": [ { "text": { "content": "新任務" } }]},
            "所屬專案": { "rich_text": [ { "text": { "content": project_notion_id } }]},
            "日期 / Deadline": properties["時間"],
            "已完成": properties["完成"],
            "[勿動] IS任務": { "checkbox": True }
        }
        return map_properties

    @staticmethod
    def convert_user_schedule_to_project_schedule(user_notion_id, properties):
        map_properties = {
            "任務名稱": properties["項目"] if "項目" in properties else { "title": [ { "text": { "content": "任務" } }]},
            "時間": properties["日期 / Deadline"],
            "完成": properties["已完成"]
        }
        return map_properties

    @staticmethod
    def filter_project_schedule_before_updating_notion(properties):
        map_properties = {
            "任務名稱": properties["任務名稱"],
            "時間": properties["時間"],
            "完成": properties["完成"]
        }
        return map_properties

# ================= Test Run =================

if __name__ == "__main__":
    notion_manager = NotionManager()
    async def test_run():
        user_data, project_data = await notion_manager.get_all_users_and_projects()
        user_data = await notion_manager.extract_child_db_ids(user_data)
        project_data = await notion_manager.extract_child_db_ids(project_data)
        user_data, project_data = await notion_manager.get_all_schedules_from_project(user_data, project_data)
        NotionManager.output_to_json({"user_data": user_data, "project_data": project_data}, "data_sample/sample_notion_manager_output.json")

    asyncio.run(test_run())