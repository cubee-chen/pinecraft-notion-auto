from pprint import pprint
from datetime import datetime, timezone
import asyncio

from db_manager import DBManager

#! ============ Define Commonly Used Keys =============
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

SCHEDULE_NOTION_ID = "schedule_notion_id"
SYNCED_DOCUMENT = "synced_document"
IS_USER = "is_user"

#! =================== Define Class ===================

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
        self.__map = {} # private
        # [schedule_notion_id]
        self.__schedule_list = [] # private
        self.db_manager = DBManager()

    def print(self):
        print("=== Synced Document Mapping ===") 
        for instance_notion_id in self.__map:
            if self.__map[instance_notion_id][IS_USER] == None:
                print(f"(error no is_user) {instance_notion_id} -> ({self.__map[instance_notion_id]['schedule_notion_id']})")
            elif self.__map[instance_notion_id][IS_USER]:
                print(f"{instance_notion_id} -> ({self.__map[instance_notion_id]['schedule_notion_id']})")
            else:
                print(f"{instance_notion_id} (datasource)")
        print("===============================")

    def get_all_instance_notion_id(self):
        return self.__map.keys()
    
    def get_schedule_notion_id(self, instance_notion_id):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            #! Error not handled
            return None
        return self.__map[instance_notion_id][SCHEDULE_NOTION_ID]

    def is_user(self, instance_notion_id):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            #! Error not handled
            return None
        return self.__map[instance_notion_id][IS_USER]
    # Create SyncedDocument if not exist, update link if exist
    #   schedule_notion_id is the reference to the schedule element
    #   schedule_notion_id is defined as the id to the project schedule database
    #   instance_notion_id can refer to the project's schedule element or the users' schedule element
    def create_instance_link(self, schedule_notion_id, instance_notion_id, is_user):
        # print(f"create_instance_link: {schedule_notion_id} <-> {instance_notion_id}")
        if instance_notion_id in self.__map:
            return True
        if schedule_notion_id in self.__schedule_list:
            # Task already exist in the mapping
            #! Maybe we can resort to better search methods in the future
            synced_document = None
            for notion_id in self.__map:
                if self.__map[notion_id][SCHEDULE_NOTION_ID] == schedule_notion_id:
                    synced_document = self.__map[notion_id][SYNCED_DOCUMENT]
            if not synced_document:
                raise KeyError("No Synced Document Exist!")
            self.__map[instance_notion_id] = {
                SCHEDULE_NOTION_ID: schedule_notion_id,
                SYNCED_DOCUMENT: synced_document,
                IS_USER: is_user
            }
        else:
            # Task doesn't exist in the mapping
            self.__schedule_list.append(schedule_notion_id)
            synced_document = SyncedDocument(schedule_notion_id, self.db_manager) #! Consider passing arguments in the future
            self.__map[instance_notion_id] = {
                SCHEDULE_NOTION_ID: schedule_notion_id,
                SYNCED_DOCUMENT: synced_document,
                IS_USER: is_user
            }
        return True
    
    def schedule_notion_id_is_synced(self, schedule_notion_id):
        return schedule_notion_id in self.__schedule_list

    def instance_notion_id_is_synced(self, instance_notion_id):
        return instance_notion_id in self.__map

    # Version Control:
    #!   AHEAD: Notion is ahead of DB
    #!   NOT_TRACKED: Not tracked
    #!   UP_TO_DATE: Notion is at the same version with DB
    #!   Object: Notion is behind DB -> Returns the newer version content
    async def check_version_by_notion_id(self, instance_notion_id, last_edited_time):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            return SyncedDocumentManager.NOT_TRACKED
        synced_document: SyncedDocument = self.__map[instance_notion_id][SYNCED_DOCUMENT]
        return await synced_document.check_version(last_edited_time)

    async def get_latest_version_by_notion_id(self, instance_notion_id):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            #! Deal with this error
            return False
        synced_document: SyncedDocument = self.__map[instance_notion_id][SYNCED_DOCUMENT]
        return await synced_document.get_latest_version()

    async def save_version_by_notion_id(self, instance_notion_id, content, last_edited_time=None):
        if not self.instance_notion_id_is_synced(instance_notion_id):
            return False
        synced_document: SyncedDocument = self.__map[instance_notion_id][SYNCED_DOCUMENT]
        return await synced_document.save_version(content, last_edited_time)
    
    async def sync_project_schedule(self, project_schedule):
        if self.schedule_notion_id_is_synced(project_schedule[NOTION_ID]):
            # Add virtual link with physical element for the project's schedule
            self.create_instance_link(project_schedule[NOTION_ID], project_schedule[NOTION_ID], is_user=False)
            # Save the physical page to the database
            await self.save_version_by_notion_id(project_schedule[NOTION_ID], project_schedule, project_schedule[LAST_EDITED_TIME])
    

# A mapping of Notion Page and Physical DB via a Virtual Page (SyncedDocument)
class SyncedDocument:
    def __init__(self, notion_id, db_manager: DBManager):
        self.last_edited_time = 0
        # Physical Notion Page
        self.notion_id = notion_id
        self.db_manager = db_manager
        
    async def check_version(self, last_edited_time):
        if last_edited_time == self.last_edited_time:
            # Notion is currently at the same version with DB
            return SyncedDocumentManager.UP_TO_DATE
        elif last_edited_time > self.last_edited_time:
            # Notion is ahead of DB
            self.last_edited_time = last_edited_time
            print(f"Check Version: {last_edited_time} (incoming) - {self.last_edited_time} (saved) = {last_edited_time - self.last_edited_time}")
            return SyncedDocumentManager.AHEAD
            #! The program would then call save_version
        elif last_edited_time < self.last_edited_time:
            # Notion is behind DB
            print(f"Check Version: {last_edited_time} (incoming) - {self.last_edited_time} (saved) = {last_edited_time - self.last_edited_time}")
            return SyncedDocumentManager.BEHIND
            #! The program would then call get_latest_version
        else:
            #! BUG
            print(f"!ERROR! Last_edited_time: {self.last_edited_time} vs {last_edited_time}")
            return SyncedDocumentManager.NOT_TRACKED

    async def get_latest_version(self):
        # Fetch content from DB
        return await self.db_manager.get_schedule_by_notion_id(self.notion_id)
    
    async def save_version(self, content, last_edited_time=None):
        if last_edited_time == None:
            last_edited_time = int(round(datetime.now(timezone.utc).timestamp()/60)*60)
        self.last_edited_time = last_edited_time

        #! Save content to DB
        return await self.db_manager.update_schedule_by_notion_id(self.notion_id, content)