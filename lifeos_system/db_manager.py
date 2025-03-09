import os
from dotenv import load_dotenv

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
    def __init__(self, dbName, collectionName):
        global MONGO_URI

        # Instance Variables
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[dbName]
        self.collection = self.db[collectionName]
