import os
from dotenv import load_dotenv
from pprint import pprint
import asyncio

from pymongo.mongo_client import MongoClient

#! =========== Load Environmental Variables ===========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

#! ================= Default Variables ================
DBNAME = "WebService"
USER_COLLECTION = "user_db"
PROJECT_COLLECTION = "project_db"
SCHEDULE_COLLECTION = "schedule_db"

#! ============ Define Commonly Used Keys =============
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

#! =================== Define Class ===================
class DBManager:
    
    # init: Establish connection with mongoDB
    def __init__(self):

        # Instance Variables
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DBNAME]
        self.user_collection = self.db[USER_COLLECTION]
        self.project_collection = self.db[PROJECT_COLLECTION]
        self.schedule_collection = self.db[SCHEDULE_COLLECTION]
    
    # Run at start, After NotionManager.extract_all_schedules
    async def update_users_and_projects(self, user_data, project_data, drop_content=True):
        # Upsert Data Concurrently

        print(f"{'(drop_content) ' if drop_content else ''}Saving {len(user_data)} users and {len(project_data)} projects to the Database...")
        # Process users
        async def process_user(user):
            if drop_content:
                # user.pop(NOTION_CONTENT, None)
                user[NOTION_CONTENT] = []
            return await self.update_user_by_notion_id(user[NOTION_ID], user)

        # Process projects
        async def process_project(project):
            if drop_content:
                project.pop(NOTION_CONTENT, None)
            return await self.update_project_by_notion_id(project[NOTION_ID], project)

        # Run user and project updates concurrently
        #! Not yet handled data invalid situations
        await asyncio.gather(
            *(process_user(user) for user in user_data),
            *(process_project(project) for project in project_data)
        )

        return True

    async def update_user_by_notion_id(self, notion_id: str, data):
        #! Fake async. Can be upgraded to "real" async

        # Validate user data
        user_validated = DBManager.data_validation(data, f"user_{notion_id}")
        if not user_validated:
            #! Program wouldn't insert into DB if the data isn't validated.
            return False

        # If user exists, save it; if not, create a new BSON and save it (upsert=True)
        self.user_collection.update_one({NOTION_ID: notion_id}, {"$set": data}, upsert=True)
        
        return True
    
    async def update_project_by_notion_id(self, notion_id: str, data):
        #! Fake async. Can be upgraded to "real" async

        # Validate project data
        project_validated = DBManager.data_validation(data, f"project_{notion_id}")
        if not project_validated:
            #! Program wouldn't insert into DB if the data isn't validated.
            return False

        # If project exists, save it; if not, create a new BSON and save it (upsert=True)
        self.project_collection.update_one({NOTION_ID: notion_id}, {"$set": data}, upsert=True)
        
        return True

    async def update_schedule_by_notion_id(self, notion_id: str, data):
        #! Fake async. Can be upgraded to "real" async
        # print("Update DB: ", notion_id, data[NOTION_ID])

        # Validate schedule data
        schedule_validated = DBManager.data_validation(data, f"schedule_{notion_id}")
        schedule_property_validated = DBManager.schedule_property_validation(data[NOTION_PROPERTIES], f"property of schedule_{notion_id}")
        
        if not schedule_validated or not schedule_property_validated:
            #! Program wouldn't insert into DB if the data isn't validated.
            return False
        
        # Redundant Check
        if notion_id != data[NOTION_ID]:
            print("!WARNING! notion_id != data['notion_id]")
            data[NOTION_ID] = notion_id
        
        # If schedule exists, save it; if not, create a new BSON and save it (upsert=True)
        self.schedule_collection.update_one({NOTION_ID: notion_id}, {"$set": data}, upsert=True)
        
        return True
    
    async def get_user_by_notion_id(self, notion_id: str):
        user = self.user_collection.find_one({NOTION_ID: notion_id})
        if not user:
            # No user with this ID exists
            return None
        return user
    
    async def get_schedule_by_notion_id(self, notion_id: str):
        schedule = self.schedule_collection.find_one({NOTION_ID: notion_id})
        if not schedule:
            # No schedule with this ID exists
            #! Error Handling
            print(f"!ERROR! No schedule with id '{notion_id}' exist!")
            return None
        return schedule

    #! Danger Zone
    async def delete_everything(self):
        self.user_collection.delete_many({})
        self.project_collection.delete_many({})
        self.schedule_collection.delete_many({})
        print("Deleted Everything in three collections")
    
    #! ============ Utility Functions for DB ============

    # Checks schema
    @staticmethod
    def data_validation(db_entry, data_name="[data]"):
        REQUIRED_KEYS = [
            NOTION_ID, 
            LAST_EDITED_TIME, 
            NOTION_PROPERTIES
        ]
        # ADDITIONAL_KEYS = [
        #     "schedule",
        #     "schedule_data"
        # ]
        for key in REQUIRED_KEYS:
            if key not in db_entry:
                print(f"!ERROR! Data validation of '{data_name}' has failed: Missing {key}")
                return False
        # for key in ADDITIONAL_KEYS:
        #     if key not in db_entry:
        #         print(f"!WARNING! Data '{data_name}' is missing '{key}' key.")
        return True

    @staticmethod
    def schedule_property_validation(property, data_name="[data]"):
        # REQUIRED_KEYS = [
        #     "負責人",
        #     "時間",
        #     "完成",
        #     "前置任務",
        #     "子任務",
        #     "進度",
        #     "預估所需時長(天)",
        #     "類別",
        #     "ID",
        #     "任務權重",
        #     "儲存進度",
        #     "剩餘天數",
        #     "父任務",
        #     "後續任務",
        #     "Blocked by",
        #     "Blocking",
        #     "Parent item",
        #     "Sub-item"
        # ]
        REQUIRED_KEYS = [
            "時間",
            "完成",
            "任務名稱"
        ]
        for key in REQUIRED_KEYS:
            if key not in property:
                print(f"!ERROR! Property validation of '{data_name}' has failed: Missing {key}")
                return False
        return True

if __name__ == "__main__":
    db_manager = DBManager()
    db_manager.get_user_by_notion_id("1b1d801c39b080f08cc6cd31f16d0cb9")