import asyncio

from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache
from request_manager import RequestManager

# =========== System Variables ===========
FAST_FETCH_INTERVAL = 0.1 # seconds
NORMAL_FETCH_INTERVAL = 10 # seconds
SLOW_FETCH_INTERVAL = 600 # seconds

MAX_SYNC_ATTEMPTS = 5 # continuously sync the pages

# =========== Debug Variables ===========
SAVE_DATA_SAMPLE = False

# ===== Define Commonly Used Keys ======
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

# =========== Driver Class ===========
class Driver:
    def __init__(self):
        # Runtime Variables
        self.fetch_interval = NORMAL_FETCH_INTERVAL
        
        # Manager Functions
        self.notion_manager = NotionManager()
        #! Database can only be accessed via SyncedDocumentManager
        self.synced_document_manager = SyncedDocumentManager()
        self.cache = Cache()
        self.request_manager = RequestManager(self.notion_manager, self.cache, self.synced_document_manager)

    async def sweep_all_schedules(self):
        all_schedule_notion_id = self.synced_document_manager.get_all_instance_notion_id()
        self.synced_document_manager.print()
        async def sweep(instance_notion_id):
            # get only properties
            instance_schedule = await self.notion_manager.get_schedule_by_notion_id(instance_notion_id, includes_content=False)
            last_edited_time = instance_schedule[LAST_EDITED_TIME]

            # version control
            version_control = await self.synced_document_manager.check_version_by_notion_id(instance_notion_id, last_edited_time)
            if version_control == SyncedDocumentManager.UP_TO_DATE:
                # Great!
                pass
            elif version_control == SyncedDocumentManager.AHEAD:
                # Save the current version to DB
                full_instance_schedule = await self.notion_manager.get_schedule_by_notion_id(instance_notion_id, includes_content=True)
                
                #! Set notion_id to schedule_notion_id
                full_instance_schedule[NOTION_ID] = self.synced_document_manager.get_schedule_notion_id(instance_notion_id)

                # Check if the properties are correct
                is_user = self.synced_document_manager.is_user(instance_notion_id)
                if is_user == None:
                    #! Error
                    print("document not synced")
                if is_user:
                    full_instance_schedule[NOTION_PROPERTIES] = self.notion_manager.convert_user_schedule_to_project_schedule(instance_notion_id, full_instance_schedule[NOTION_PROPERTIES])
                
                print(f"Page {instance_notion_id} is Ahead of the Current Version. Updating DB...")
                await self.synced_document_manager.save_version_by_notion_id(instance_notion_id, full_instance_schedule)
            elif version_control == SyncedDocumentManager.NOT_TRACKED:
                #! Deal with it
                print(f"'{instance_notion_id}' NOT TRACKED IN VERSION CONTROL!")
            elif version_control == SyncedDocumentManager.BEHIND:
                # Fetch the latest version
                latest_version_schedule = await self.synced_document_manager.get_latest_version_by_notion_id(instance_notion_id)
                is_user = self.synced_document_manager.is_user(instance_notion_id)
                if not latest_version_schedule:
                    #! Error Handling
                    return version_control
                if is_user == None:
                    #! Error
                    print("document not synced")
                elif is_user:
                    print(f"User Schedule {instance_notion_id} is Behind the Current Version. Syncing...")
                    await self.notion_manager.update_user_schedule(instance_notion_id, latest_version_schedule)
                else:
                    print(f"Project Schedule {instance_notion_id} is Behind the Current Version. Syncing...")
                    await self.notion_manager.update_project_schedule(instance_notion_id, latest_version_schedule)
                
            return version_control

        version_control_aggregation = await asyncio.gather(*(sweep(instance_notion_id) for instance_notion_id in all_schedule_notion_id))
        
        print("=== Version Control Check ===")
        print(f"{version_control_aggregation.count(SyncedDocumentManager.AHEAD)} Pages Ahead")
        print(f"{version_control_aggregation.count(SyncedDocumentManager.BEHIND)} Pages Behind")
        print(f"{version_control_aggregation.count(SyncedDocumentManager.UP_TO_DATE)} Pages Up to Date")
        print(f"{version_control_aggregation.count(SyncedDocumentManager.NOT_TRACKED)} Pages Not Tracked")
        print("=============================")

        if version_control_aggregation.count(SyncedDocumentManager.AHEAD) > 0:
            # False means not yet fully synced -> There would still be pages behind after the "ahead" is synced
            return False
        return True

    async def sweep_all_users_and_projects(self):
        user_data, project_data = await self.notion_manager.get_all_users_and_projects(self.cache, includes_content=False)
        changed_user_notion_ids = self.cache.compare_and_update_user_data(user_data)
        changed_project_notion_ids = self.cache.compare_and_update_project_data(project_data)

        user_request_results = await asyncio.gather(*(self.request_manager.handle_user_requests_by_id(user_notion_id) for user_notion_id in changed_user_notion_ids))
        project_request_results = await asyncio.gather(*(self.request_manager.handle_project_requests_by_id(project_notion_id) for project_notion_id in changed_project_notion_ids))

    # Startup Function: runs when start up
    async def startup(self):
        print("Starting Up Driver...")
        
        # Fetch all data from Notion, Setup Synced Document, and save into Database
        user_data, project_data = await self.notion_manager.get_all_users_and_projects(self.cache)
        user_data = await self.notion_manager.extract_child_db_ids(user_data, self.cache)
        project_data = await self.notion_manager.extract_child_db_ids(project_data, self.cache)
        schedule_data = await self.notion_manager.get_all_schedules_from_project(project_data)
        
        self.cache.refresh_user_data(user_data)
        self.cache.refresh_project_data(project_data)

        if SAVE_DATA_SAMPLE:
            NotionManager.output_to_json(user_data, "data_sample/user_data.json")
            NotionManager.output_to_json(project_data, "data_sample/project_data.json")
            NotionManager.output_to_json(schedule_data, "data_sample/schedule_data.json")
        
        await self.synced_document_manager.db_manager.update_all_users_and_projects(user_data, project_data, drop_content=True)
        await self.notion_manager.renew_all_schedules_in_user(user_data, schedule_data, self.cache, self.synced_document_manager)
        # self.synced_document_manager.print()
        print("Startup Complete!")
    # Main Function: runs every FETCH_INTERVAL seconds
    async def driver(self):
        
        # TODO: (Advanced) Pull from Admin DB and dynamically control the fetch interval

        # Keep up sync
        print("---")
        synced = await self.sweep_all_schedules()
        sync_attempt = 2
        while not synced:
            if sync_attempt > MAX_SYNC_ATTEMPTS:
                break
            print(f"--- Sync Attempt {sync_attempt} ---")
            synced = await self.sweep_all_schedules()
            sync_attempt += 1

    # Async Entry FUnction
    async def main(self):
        await self.startup()
        print("Driver Running!")
        print("")
        # self.synced_document_manager.print()
        while True:
            await self.driver()
            await asyncio.sleep(self.fetch_interval)

    # Entry Function
    def run(self):
        asyncio.run(self.main())

if __name__ == "__main__":
    driver = Driver()
    driver.run()