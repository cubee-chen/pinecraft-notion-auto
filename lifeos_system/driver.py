import asyncio

from notion_manager import NotionManager
from db_manager import DBManager
from synced_document import SyncedDocumentManager
from synced_document import SyncedDocument

FETCH_INTERVAL = 1 # seconds

class Driver:
    def __init__(self):
        self.notion_manager = NotionManager()
        self.db_manager = DBManager()
        self.synced_document_manager = SyncedDocumentManager()

    # Startup Function: runs when start up
    async def startup(self):
        print("Starting Up Driver...")
        
        # Fetch all data from Notion, Setup Synced Document, and save into Database
        user_data, project_data = await self.notion_manager.get_all_users_and_projects()
        user_data = await self.notion_manager.extract_child_db_ids(user_data)
        project_data = await self.notion_manager.extract_child_db_ids(project_data)
        schedule_data = await self.notion_manager.get_all_schedules_from_parent(user_data, project_data)
        NotionManager.output_to_json(schedule_data)

    # Main Function: runs every FETCH_INTERVAL seconds
    async def driver(self):
        print("Driver Running!")

    # Async Entry FUnction
    async def main(self):
        await self.startup()
        while True:
            await self.driver()
            await asyncio.sleep(FETCH_INTERVAL)

    # Entry Function
    def run(self):
        asyncio.run(self.main())

if __name__ == "__main__":
    driver = Driver()
    driver.run()