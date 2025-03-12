import os
from dotenv import load_dotenv
from pprint import pprint
import asyncio

from pymongo.mongo_client import MongoClient

# =========== Load Environmental Variables ===========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

# ================= Default Variables ================
DBNAME = "WebService"
USER_COLLECTION = "user_db"
PROJECT_COLLECTION = "project_db"
SCHEDULE_COLLECTION = "schedule_db"

# =================== Define Class ===================
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
    async def update_all_users_and_projects(self, user_data, project_data, drop_content=True):
        # Upsert Data Concurrently

        print(f"{'(drop_content) ' if drop_content else ''}Saving {len(user_data)} users and {len(project_data)} projects to the Database...")
        # Process users
        async def process_user(user):
            if drop_content:
                # user.pop("notion_content", None)
                user["notion_content"] = []
            return await self.update_user_by_notion_id(user["notion_id"], user)

        # Process projects
        async def process_project(project):
            if drop_content:
                project.pop("notion_content", None)
            return await self.update_project_by_notion_id(project["notion_id"], project)

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
        self.user_collection.update_one({"notion_id": notion_id}, {"$set": data}, upsert=True)
        
        return True
    
    async def update_project_by_notion_id(self, notion_id: str, data):
        #! Fake async. Can be upgraded to "real" async

        # Validate project data
        project_validated = DBManager.data_validation(data, f"project_{notion_id}")
        if not project_validated:
            #! Program wouldn't insert into DB if the data isn't validated.
            return False

        # If project exists, save it; if not, create a new BSON and save it (upsert=True)
        self.project_collection.update_one({"notion_id": notion_id}, {"$set": data}, upsert=True)
        
        return True

    async def update_schedule_by_notion_id(self, notion_id: str, data):
        #! Fake async. Can be upgraded to "real" async

        # Validate schedule data
        schedule_validated = DBManager.data_validation(data, f"schedule_{notion_id}")
        if not schedule_validated:
            #! Program wouldn't insert into DB if the data isn't validated.
            return False

        # If schedule exists, save it; if not, create a new BSON and save it (upsert=True)
        self.schedule_collection.update_one({"notion_id": notion_id}, {"$set": data}, upsert=True)
        
        return True
    
    async def get_user_by_notion_id(self, notion_id: str):
        user = self.user_collection.find_one({"notion_id": notion_id})
        if not user:
            # No user with this ID exists
            print("NONE")
        else:
            pprint(user)
        pass

    # ============ Utility Functions for DB ============

    # Checks schema
    @staticmethod
    def data_validation(db_entry, data_name="[data]"):
        REQUIRED_KEYS = [
            "notion_id", 
            "last_edited_time", 
            "notion_properties"
        ]
        # ADDITIONAL_KEYS = [
        #     "schedule",
        #     "schedule_data"
        # ]
        for key in REQUIRED_KEYS:
            if key not in db_entry:
                print(f"!ERROR! Data validation of '{data_name}' has failed.")
                return False
        # for key in ADDITIONAL_KEYS:
        #     if key not in db_entry:
        #         print(f"!WARNING! Data '{data_name}' is missing '{key}' key.")
        return True


if __name__ == "__main__":
    db_manager = DBManager()
    db_manager.get_user_by_notion_id("1b1d801c39b080f08cc6cd31f16d0cb9")