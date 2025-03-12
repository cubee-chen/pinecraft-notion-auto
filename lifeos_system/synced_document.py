from pprint import pprint
from datetime import datetime
import asyncio

from db_manager import DBManager

# =================== Define Class ===================

# Data structure to store and index the SyncedDocument
#! The middleware between DB and the program. The DB should not be accessed by the main program directly
class SyncedDocumentManager:
    def __init__(self):
        # instance_notion_id -> schedule_notion_id, synced_document
        self.map = {}
        # [schedule_notion_id]
        self.schedule_list = []
        self.db_manager = DBManager()

    def print(self):
        pprint(self.map)
    
    # Create SyncedDocument if not exist, update link if exist
    #   schedule_notion_id is the reference to the schedule element
    #   schedule_notion_id is defined as the id to the project schedule database
    #   instance_notion_id can refer to the project's schedule element or the users' schedule element
    def create_document_link(self, schedule_notion_id, instance_notion_id):
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
                "synced_document": synced_document
            }
        else:
            # Task doesn't exist in the mapping
            self.schedule_list.append(schedule_notion_id)
            synced_document = SyncedDocument(schedule_notion_id, self.db_manager) #! Consider passing arguments in the future
            self.map[instance_notion_id] = {
                "schedule_notion_id": schedule_notion_id,
                "synced_document": synced_document
            }
        return True
    
    def schedule_notion_id_is_synced(self, schedule_notion_id):
        return schedule_notion_id in self.schedule_list

    def instance_notion_id_is_synced(self, instance_notion_id):
        return instance_notion_id in self.map

    # Version Control:
    #!   True: Notion is ahead of DB
    #!   False: Not tracked
    #!   None: Notion is at the same version with DB
    #!   Object: Notion is behind DB -> Returns the newer version content
    async def check_version_by_notion_id(self, instance_notion_id, last_updated):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            return False
        synced_document: SyncedDocument = self.map[instance_notion_id]["synced_document"]
        return await synced_document.check_version(last_updated)
    
    async def save_version_by_notion_id(self, instance_notion_id, content, last_updated=None):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            return False
        synced_document: SyncedDocument = self.map[instance_notion_id]["synced_document"]
        return await synced_document.save_version(content, last_updated)

# A mapping of Notion Page and Physical DB via a Virtual Page (SyncedDocument)
class SyncedDocument:
    def __init__(self, notion_id, db_manager: DBManager):
        self.last_updated = 0
        # Physical Notion Page
        self.notion_id = notion_id
        self.db_manager = db_manager
        
    async def check_version(self, last_updated):
        if self.last_updated == last_updated:
            # Notion is currently at the same version with DB
            return None
        elif self.last_updated > last_updated:
            # Notion is ahead of DB
            self.last_updated = last_updated
            return True
            #! The program would then call save_version
        else:
            # Notion is behind DB
            #! Fetch content from DB
            content = []
            return content

    async def save_version(self, content, last_updated=None):
        if last_updated == None:
            last_updated = int(datetime.now().timestamp())
        self.last_updated = last_updated

        #! Save content to DB
        return await self.db_manager.update_schedule_by_notion_id(self.notion_id, content)