import os
from dotenv import load_dotenv
from pprint import pprint

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

# =================== Define Class ===================
class DBManager:
    
    # init: Establish connection with mongoDB
    def __init__(self):

        # Instance Variables
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DBNAME]
        self.user_collection = self.db[USER_COLLECTION]
        self.project_collection = self.db[PROJECT_COLLECTION]
    
    def update_user_by_notion_id(self, notion_id: str, data):
        # If user exists, save it; if not, create a new BSON and save it (upsert=True)
        self.user_collection.update_one({"notion_id": notion_id}, data, upsert=True)

    def get_user_by_notion_id(self, notion_id: str):
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
            "notion_properties", 
            "notion_content"
        ]
        for key in REQUIRED_KEYS:
            if key not in db_entry:
                print(f"!WARNING! Data validation of '{data_name}' has failed.")
                return False
        return True


if __name__ == "__main__":
    db_manager = DBManager()
    db_manager.get_user_by_notion_id("1b1d801c39b080f08cc6cd31f16d0cb9")