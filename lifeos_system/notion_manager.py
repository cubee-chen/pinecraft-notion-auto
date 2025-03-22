import os
from dotenv import load_dotenv
from pprint import pprint
import asyncio
import json
from datetime import datetime, timezone

from notion_client import AsyncClient

from synced_document import SyncedDocumentManager
from cache import Cache

#! =========== Load Environmental Variables ===========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")

USER_NOTION = os.getenv("USER_NOTION")
PROJECT_NOTION = os.getenv("PROJECT_NOTION")

#! ============ Define Commonly Used Keys =============
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

#! =================== Define Class ===================
class NotionManager:
    def __init__(self, cache: Cache, synced_document_manager: SyncedDocumentManager):
        self.notion = AsyncClient(auth=NOTION_TOKEN)
        self.cache = cache
        self.synced_document_manager = synced_document_manager

    #! ============ General CRUD Operations ============
            
    # Delete any page
    async def delete_page_by_notion_id(self, notion_id):
        await self.notion.pages.update(notion_id, archived=True)
        return True

    #! ============ CRUD Operations on User or Project ============

    # Fetch all users' metadata by USER_NOTION
    async def fetch_all_user_metadata(self):
        all_raw_user_metadata = await self.notion.databases.query(database_id=USER_NOTION)
        # Convert Everything before processing
        all_user_metadata = [{
            NOTION_ID: raw_user_metadata["id"],
            LAST_EDITED_TIME: NotionManager.notion_time_to_seconds(raw_user_metadata[LAST_EDITED_TIME]),
            NOTION_PROPERTIES: raw_user_metadata["properties"],
            NOTION_CONTENT: []
        } for raw_user_metadata in all_raw_user_metadata["results"]]
        return all_user_metadata
    
    # Fetch all projects' metadata by USER_NOTION
    async def fetch_all_project_metadata(self):
        all_raw_project_metadata = await self.notion.databases.query(database_id=PROJECT_NOTION)
        # Convert Everything before processing
        all_project_metadata = [{
            NOTION_ID: raw_project_metadata["id"],
            LAST_EDITED_TIME: NotionManager.notion_time_to_seconds(raw_project_metadata[LAST_EDITED_TIME]),
            NOTION_PROPERTIES: raw_project_metadata["properties"],
            NOTION_CONTENT: []
        } for raw_project_metadata in all_raw_project_metadata["results"]]
        return all_project_metadata

    # Fetch a single user's content from Notion by user_metadata
    async def fetch_user_content(self, user_metadata, includes_content=True):
        notion_id = user_metadata[NOTION_ID]
        last_edited_time = user_metadata[LAST_EDITED_TIME]
        notion_properties = user_metadata[NOTION_PROPERTIES]

        if len(notion_properties["姓名"]["people"]) > 0:
            user_id = notion_properties["姓名"]["people"][0]["id"]
            if user_id:
                self.cache.update_person_id_to_notion_id(user_id, notion_id)
        
        if includes_content:
            notion_content = await self.notion.blocks.children.list(notion_id)
        else:
            notion_content = {"results": []}
        
        return {
            NOTION_ID: notion_id,
            LAST_EDITED_TIME: last_edited_time,
            NOTION_PROPERTIES: notion_properties,
            NOTION_CONTENT: notion_content["results"]
        }

    # Fetch a single project's content from Notion by project_metadata
    async def fetch_project_content(self, project_metadata, includes_content=True):
        notion_id = project_metadata[NOTION_ID]
        last_edited_time = project_metadata[LAST_EDITED_TIME]
        notion_properties = project_metadata[NOTION_PROPERTIES]

        if includes_content:
            notion_content = await self.notion.blocks.children.list(notion_id)
        else:
            notion_content = {"results": []}
        
        return {
            NOTION_ID: notion_id,
            LAST_EDITED_TIME: last_edited_time,
            NOTION_PROPERTIES: notion_properties,
            NOTION_CONTENT: notion_content["results"]
        }
        
    async def update_project_partial_properties(self, project_notion_id, partial_properties):
        await self.notion.pages.update(project_notion_id, properties=partial_properties)

    #! ============ CRUD Operations on Schedule ============

    # Fetch a single schedule's data from Notion by Notion ID.
    async def fetch_schedule_by_notion_id(self, notion_id, includes_content=True):
        
        # Query the Notion database to find the specific schedule
        # print(f"Fetching Notion Page Data for User ID: {notion_id}...")
        schedule_metadata = await self.notion.pages.retrieve(notion_id)

        if not schedule_metadata:
            print(f"No schedule found with Notion ID: {notion_id}")
            return None

        async def fetch_schedule_data(schedule_metadata):
            last_edited_time = NotionManager.notion_time_to_seconds(schedule_metadata[LAST_EDITED_TIME])
            notion_properties = schedule_metadata["properties"]
            if includes_content:
                notion_content = await self.notion.blocks.children.list(notion_id)
            else:
                notion_content = {"results": []}
            return {
                NOTION_ID: notion_id,
                LAST_EDITED_TIME: last_edited_time,
                NOTION_PROPERTIES: notion_properties,
                NOTION_CONTENT: notion_content["results"]
            }

        # Fetch schedule data asynchronously
        schedule_data = await fetch_schedule_data(schedule_metadata)

        return schedule_data

    # Fetch schedule by project object and extend schedule_data
    async def fetch_schedules_by_parent_project(self, project, schedule_data):
        """Fetch schedule data for a single project."""
        if "schedule" not in project:
            print(f"No Schedule DB Exist in Project: {project[NOTION_ID]}")
            return  #! Skip projects without schedules
        
        schedule_id = project["schedule"]
        schedules = (await self.notion.databases.query(database_id=schedule_id))["results"]
        
        schedule_data.extend(await asyncio.gather(*[
            self.fetch_schedule_content(schedule, project[NOTION_ID]) for schedule in schedules
        ]))

    # Fetch schedule details by schedule object
    async def fetch_schedule_content(self, schedule_raw, r_parent_db_notion_id):
        # Fetch schedule details for each schedule item.
        last_edited_time = NotionManager.notion_time_to_seconds(schedule_raw[LAST_EDITED_TIME])
        return {
            NOTION_ID: schedule_raw["id"],
            NOTION_PROPERTIES: schedule_raw["properties"],
            NOTION_CONTENT: (await self.notion.blocks.children.list(schedule_raw["id"]))["results"],
            "r_parent_db": r_parent_db_notion_id,
            LAST_EDITED_TIME: last_edited_time
        }

    # Insert schedule to users' schedule database according to the project's schedule database
    async def insert_schedules_to_user_schedule_db(self, project_schedule):
        people = project_schedule[NOTION_PROPERTIES]["負責人"]["people"]
        await asyncio.gather(*(self.insert_user_schedule_db_by_person(person, project_schedule) for person in people))

    async def insert_user_schedule_db_by_person(self, person, project_schedule):
        person_id = person["id"]
        notion_id = self.cache.get_person_id_to_notion_id(person_id)
        if not notion_id:
            #! Handle cache not yet saved user_id -> notion_id mapping
            # might be because a user shared the project to other users
            return
        # Add schedule data to a specific user's schedule database
        user_schedule_id = self.cache.get_notion_id_to_schedule_id(notion_id)
        if not user_schedule_id:
            #! Handle cache not yet saved notion_id -> schedule_id mapping
            # brute search?
            return
        new_schedule_id = await self.insert_user_schedule(user_schedule_id, project_schedule)

        # Add link to synced document
        self.synced_document_manager.create_instance_link(project_schedule[NOTION_ID], new_schedule_id, is_user=True)

    # Create user schedule page
    async def insert_user_schedule(self, schedule_db_id, schedule):
        mapped_properties = NotionManager.convert_project_schedule_to_user_schedule(schedule["r_parent_db"], schedule[NOTION_PROPERTIES])
        new_page = await self.notion.pages.create(
            parent={"database_id": schedule_db_id},
            properties=mapped_properties
        )
        return new_page["id"]

    # Update user schedule page to the newest version
    async def update_user_schedule(self, schedule_notion_id, schedule):
        mapped_properties = NotionManager.convert_project_schedule_to_user_schedule(schedule["r_parent_db"], schedule[NOTION_PROPERTIES])
        await self.notion.pages.update(schedule_notion_id, properties=mapped_properties)

        #! Notion currently doesn't allow direct content editing yet
        await self.notion.blocks.children.append(schedule_notion_id, children=schedule[NOTION_CONTENT])

    # Update project schedule page to the newest version
    async def update_project_schedule(self, schedule_notion_id, schedule):
        mapped_properties = NotionManager.filter_project_schedule_before_updating_notion(schedule[NOTION_PROPERTIES])
        await self.notion.pages.update(schedule_notion_id, properties=mapped_properties)

        #! Notion currently doesn't allow direct content editing yet
        await self.notion.blocks.children.append(schedule_notion_id, children=schedule[NOTION_CONTENT])

    async def update_project_schedules_by_partial_properties(self, schedule_notion_id, partial_propterties):
        await self.notion.pages.update(schedule_notion_id, properties=partial_propterties)

    # Delete schedules in user that corresponds to a specific project
    async def delete_user_schedules_by_project_notion_id(self, user, project_notion_ids):
        if "schedule" not in user:
            return
        #! prop: "[勿動] IS任務"
        pages_to_delete = await self.notion.databases.query(user["schedule"], **{
            "property": "所屬專案",
            "rich_text": {"is_not_empty": True}
        })
        # Filter those with the related project ids
        #! Filter Ref: "所屬專案": { "rich_text": [ { "text": { "content": project_notion_id } }]},
        page_ids = [page["id"] for page in pages_to_delete["results"] 
                    if (
                        len(page["properties"]["所屬專案"]["rich_text"]) > 0 
                        and page["properties"]["所屬專案"]["rich_text"][0]["text"]["content"] in project_notion_ids
                    )]
        await asyncio.gather(*(self.delete_page_by_notion_id(page_id) for page_id in page_ids))
        print(f"Deleted {len(page_ids)} Outdated Schedules")
    
    #! ================ Other CRUD Operations ===============

    async def fetch_class_schedule_by_db_id(self, class_schedule_db_id):
        return await self.notion.databases.query(class_schedule_db_id)
    
    async def fetch_schedule_by_db_id(self, schedule_db_id):
        return await self.notion.databases.query(schedule_db_id)
    
    async def delete_all_when_to_meet_schedules(self, when_to_meet_db_id):
        all_when_to_meet = await self.notion.databases.query(when_to_meet_db_id)
        await asyncio.gather(*(self.delete_page_by_notion_id(when_to_meet["id"]) for when_to_meet in all_when_to_meet["results"]))

    async def insert_when_to_meet_schedule(self, when_to_meet_db_id, properties):
        await self.notion.pages.create(
            parent={"database_id": when_to_meet_db_id},
            properties=properties
        )

    async def change_when_to_meet_property_names_sorted(self, when_to_meet_db_id, property_names_sorted):
        retrieved_db = await self.notion.databases.retrieve(when_to_meet_db_id)
        old_properties = retrieved_db["properties"]
        
        index = 0
        for property_name in sorted(old_properties.keys()):
            if property_name == "時段":
                continue
            await self.notion.databases.update(when_to_meet_db_id, properties = {
                property_name: {
                    "name": property_names_sorted[index]
                }
            })
            index += 1

    #! ============ Utility Functions for Notion ============

    # Converts notion datetime to seconds since epoch
    @staticmethod
    def notion_time_to_seconds(last_edited_time):
        return int(datetime.strptime(last_edited_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp())
    
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
            "When to Meet": "when_to_meet"
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
