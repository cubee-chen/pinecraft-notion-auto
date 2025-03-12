from pprint import pprint
from datetime import datetime, timezone
import asyncio

from db_manager import DBManager

# =================== Define Class ===================

# Data structure to store and index the SyncedDocument
#! The middleware between DB and the program. The DB should not be accessed by the main program directly
class SyncedDocumentManager:

    # Class Variables
    NOT_TRACKED = -1
    UP_TO_DATE = 0
    AHEAD = 1
    BEHIND = 2

    def __init__(self):
        # instance_notion_id -> schedule_notion_id, synced_document
        self.map = {}
        # [schedule_notion_id]
        self.schedule_list = []
        self.db_manager = DBManager()

    def print(self):
        print("=== Synced Document Mapping ===") 
        for instance_notion_id in self.map:
            if self.map[instance_notion_id]["is_user"] == None:
                print(f"(error no is_user) {instance_notion_id} -> ({self.map[instance_notion_id]['schedule_notion_id']})")
            elif self.map[instance_notion_id]["is_user"]:
                print(f"{instance_notion_id} -> ({self.map[instance_notion_id]['schedule_notion_id']})")
            else:
                print(f"{instance_notion_id} (datasource)")
        print("===============================")

    def get_all_instance_notion_id(self):
        return self.map.keys()
    
    def get_schedule_notion_id(self, instance_notion_id):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            #! Error not handled
            return None
        return self.map[instance_notion_id]["schedule_notion_id"]

    def is_user(self, instance_notion_id):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            #! Error not handled
            return None
        return self.map[instance_notion_id]["is_user"]
    # Create SyncedDocument if not exist, update link if exist
    #   schedule_notion_id is the reference to the schedule element
    #   schedule_notion_id is defined as the id to the project schedule database
    #   instance_notion_id can refer to the project's schedule element or the users' schedule element
    def create_instance_link(self, schedule_notion_id, instance_notion_id, is_user):
        # print(f"create_instance_link: {schedule_notion_id} <-> {instance_notion_id}")
        if instance_notion_id in self.map:
            return True
        if schedule_notion_id in self.schedule_list:
            # Task already exist in the mapping
            #! Maybe we can resort to better search methods in the future
            synced_document = None
            for notion_id in self.map:
                if self.map[notion_id]["schedule_notion_id"] == schedule_notion_id:
                    synced_document = self.map[notion_id]["synced_document"]
            if not synced_document:
                raise KeyError("No Synced Document Exist!")
            self.map[instance_notion_id] = {
                "schedule_notion_id": schedule_notion_id,
                "synced_document": synced_document,
                "is_user": is_user
            }
        else:
            # Task doesn't exist in the mapping
            self.schedule_list.append(schedule_notion_id)
            synced_document = SyncedDocument(schedule_notion_id, self.db_manager) #! Consider passing arguments in the future
            self.map[instance_notion_id] = {
                "schedule_notion_id": schedule_notion_id,
                "synced_document": synced_document,
                "is_user": is_user
            }
        return True
    
    def schedule_notion_id_is_synced(self, schedule_notion_id):
        return schedule_notion_id in self.schedule_list

    def instance_notion_id_is_synced(self, instance_notion_id):
        return instance_notion_id in self.map

    # Version Control:
    #!   AHEAD: Notion is ahead of DB
    #!   NOT_TRACKED: Not tracked
    #!   UP_TO_DATE: Notion is at the same version with DB
    #!   Object: Notion is behind DB -> Returns the newer version content
    async def check_version_by_notion_id(self, instance_notion_id, last_edited_time):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            return SyncedDocumentManager.NOT_TRACKED
        synced_document: SyncedDocument = self.map[instance_notion_id]["synced_document"]
        return await synced_document.check_version(last_edited_time)

    async def get_latest_version_by_notion_id(self, instance_notion_id):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            #! Deal with this error
            return False
        synced_document: SyncedDocument = self.map[instance_notion_id]["synced_document"]
        return await synced_document.get_latest_version()

    async def save_version_by_notion_id(self, instance_notion_id, content, last_edited_time=None):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            return False
        synced_document: SyncedDocument = self.map[instance_notion_id]["synced_document"]
        return await synced_document.save_version(content, last_edited_time)

# A mapping of Notion Page and Physical DB via a Virtual Page (SyncedDocument)
class SyncedDocument:
    def __init__(self, notion_id, db_manager: DBManager):
        self.last_edited_time = 0
        # Physical Notion Page
        self.notion_id = notion_id
        self.db_manager = db_manager
        
    async def check_version(self, last_edited_time):
        print(f"Check Version: {last_edited_time} (incoming) - {self.last_edited_time} (saved) = {last_edited_time - self.last_edited_time}")
        if last_edited_time == self.last_edited_time:
            # Notion is currently at the same version with DB
            return SyncedDocumentManager.UP_TO_DATE
        elif last_edited_time > self.last_edited_time:
            # Notion is ahead of DB
            self.last_edited_time = last_edited_time
            return SyncedDocumentManager.AHEAD
            #! The program would then call save_version
        elif last_edited_time < self.last_edited_time:
            # Notion is behind DB
            return SyncedDocumentManager.BEHIND
            #! The program would then call get_latest_version
        else:
            #! BUG
            print(f"Last_edited_time: {self.last_edited_time} vs {last_edited_time}")

    async def get_latest_version(self):
        # Fetch content from DB
        return await self.db_manager.get_schedule_by_notion_id(self.notion_id)
    
    async def save_version(self, content, last_edited_time=None):
        if last_edited_time == None:
            last_edited_time = int(datetime.now(timezone.utc).timestamp() // 60 * 60)
        self.last_edited_time = last_edited_time

        #! Save content to DB
        return await self.db_manager.update_schedule_by_notion_id(self.notion_id, content)