import asyncio
from pprint import pprint
from datetime import datetime, timezone

from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache
from request_manager import RequestManager

#! =========== System Variables ===========
FAST_FETCH_INTERVAL = 0.1 # seconds
NORMAL_FETCH_INTERVAL = 10 # seconds
SLOW_FETCH_INTERVAL = 600 # seconds

MAX_SYNC_ATTEMPTS = 5 # continuously sync the pages

#! =========== Debug Variables ===========
SAVE_DATA_SAMPLE = False

#! ===== Define Commonly Used Keys ======
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

#! =========== Driver Class ===========
class Driver:
    def __init__(self):
        # Runtime Variables
        self.fetch_interval = NORMAL_FETCH_INTERVAL
        self.last_updated_time = datetime.now(timezone.utc).timestamp()
        
        # Manager Functions
        self.cache = Cache()
        self.synced_document_manager = SyncedDocumentManager()
        self.notion_manager = NotionManager(self.cache, self.synced_document_manager)
        #! Database can only be accessed via SyncedDocumentManager
        self.request_manager = RequestManager(self.notion_manager, self.cache, self.synced_document_manager)

    #! ================ STARTUP FUNCTIONS ================
    
    # 1. Get all users and projects and return user_data and project_data
    async def get_all_users_and_projects(self, includes_content = True): 

        # Get all properties and content from all the users
        print("Fetching Notion Page Data From All Users...")
        all_user_metadata = await self.notion_manager.fetch_all_user_metadata()
        user_data = await asyncio.gather(*[self.notion_manager.fetch_user_content(user_metadata, includes_content) for user_metadata in all_user_metadata])

        # Get all properties and content from all the projects
        print("Fetching Notion Page Data From All Projects...")
        all_project_metadata = await self.notion_manager.fetch_all_project_metadata()
        project_data = await asyncio.gather(*[self.notion_manager.fetch_project_content(project_metadata, includes_content) for project_metadata in all_project_metadata])

        return user_data, project_data
    
    # 2. Extract child db ids from a Notion page
    async def extract_child_db_ids(self, data):

        # get db ids from parent page content
        # run at program start
        # print("Extracting Child Databases...")
        # pprint(data)
        for entry in data:
            notion_content = entry[NOTION_CONTENT]
            for block in notion_content:
                if block["type"] == "child_database":
                    db_name = NotionManager.get_db_name(block["child_database"]["title"])
                    entry[db_name] = block["id"]
                    if db_name == "schedule":
                        self.cache.update_notion_id_to_schedule_id(entry[NOTION_ID], block["id"])
                    elif db_name == "class_schedule":
                        self.cache.update_notion_id_to_class_schedule_id(entry[NOTION_ID], block["id"])
                    elif db_name == "when_to_meet":
                        self.cache.update_notion_id_to_when_to_meet_id(entry[NOTION_ID], block["id"])


        return data
    
    # 3. Fetch all schedule data collected in project_data
    async def get_all_schedules_from_project(self, project_data):

        schedule_data = []
        
        # Run all schedule fetches in parallel
        print("Fetching Schedules From All Projects' Homepages...")
        await asyncio.gather(*(self.notion_manager.fetch_schedules_by_parent_project(project, schedule_data) for project in project_data))

        return schedule_data

    # 4. Delete all schedule data collected in user_data that corresponds to one in project_data
    #    and insert new schedule data by cloing these in project data
    async def renew_all_schedules_in_user(self, user_data, project_notion_ids, schedule_data):
        
        # Delete
        print("Deleting all Outdated Schedules...")
        await asyncio.gather(*(self.notion_manager.delete_user_schedules_by_project_notion_id(user, project_notion_ids) for user in user_data))
        
        # Insert
        print("Inserting New Schedules to User Notion...")
        await asyncio.gather(*(self.notion_manager.insert_schedules_to_user_schedule_db(schedule) for schedule in schedule_data))
        
        # Insert schedule to DB
        print("Inserting All Schedules to the Database...")
        await asyncio.gather(*[self.synced_document_manager.sync_project_schedule(project_schedule) for project_schedule in schedule_data])
        
        # synced_document_manager.print()
        return True
    

    #! ================ DRIVER FUNCTIONS ================

    # Sync schedules
    async def sweep_all_schedules(self):
        # get schedules from synced_document_manager
        all_schedule_notion_id = self.synced_document_manager.get_all_instance_notion_id()
        # self.synced_document_manager.print()
        async def sweep(instance_notion_id):
            # get only properties
            instance_schedule = await self.notion_manager.fetch_schedule_by_notion_id(instance_notion_id, includes_content=False)
            last_edited_time = instance_schedule[LAST_EDITED_TIME]

            # version control
            version_control = await self.synced_document_manager.check_version_by_notion_id(instance_notion_id, last_edited_time)
            if version_control == SyncedDocumentManager.UP_TO_DATE:
                # Great!
                pass
            elif version_control == SyncedDocumentManager.AHEAD:
                # Save the current version to DB
                full_instance_schedule = await self.notion_manager.fetch_schedule_by_notion_id(instance_notion_id, includes_content=True)
                
                #! Set notion_id to schedule_notion_id
                full_instance_schedule[NOTION_ID] = self.synced_document_manager.get_schedule_notion_id(instance_notion_id)

                # Check if the properties are correct
                is_user = self.synced_document_manager.is_user(instance_notion_id)
                if is_user == None:
                    #! Error
                    print("document not synced")
                if is_user:
                    full_instance_schedule[NOTION_PROPERTIES] = self.notion_manager.convert_user_schedule_to_project_schedule(instance_notion_id, full_instance_schedule[NOTION_PROPERTIES])
                
                #! Check if new collaborators are added to the schedule page
                # Compare collaborators property
                previous_version_schedule = await self.synced_document_manager.get_latest_version_by_notion_id(instance_notion_id)
                
                #! ERROR: Couldn't be resolved using current structure
                if "負責人" in full_instance_schedule[NOTION_PROPERTIES] and "負責人" in previous_version_schedule[NOTION_PROPERTIES]:
                    previous_people = previous_version_schedule[NOTION_PROPERTIES]["負責人"]["people"]
                    incoming_people = full_instance_schedule[NOTION_PROPERTIES]["負責人"]["people"]
                    new_people = list(set(incoming_people) - set(previous_people))
                    #! Not handled yet
                    deleted_people = list(set(previous_people) - set(incoming_people))
                    # Add pages in users' schedule_db corresponding to new people
                    print(f"Added {len(new_people)} people to schedule {full_instance_schedule[NOTION_ID]}")
                    await asyncio.gather(*(self.notion_manager.insert_user_schedule_db_by_person(new_person, full_instance_schedule) for new_person in new_people))

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

    # Respond to actions on users and projects
    async def sweep_all_users_and_projects(self):
        user_metadata, project_metadata = await self.get_all_users_and_projects(includes_content=False)
        created_users_metadata, updated_users_metadata = self.cache.compare_and_update_user_data(user_metadata)
        created_projects_metadata, updated_projects_metadata = self.cache.compare_and_update_project_data(project_metadata)

        # Handle Create User or Project
        if len(created_users_metadata) > 0 or len(created_projects_metadata) > 0:
            print(f"Creating {len(created_users_metadata)} users and {len(created_projects_metadata)} projects")
            
            # Fetch content using metadata
            created_users = await asyncio.gather(*(self.notion_manager.fetch_user_content(user_metadata, includes_content=True) for user_metadata in created_users_metadata))
            created_projects = await asyncio.gather(*(self.notion_manager.fetch_project_content(project_metadata, includes_content=True) for project_metadata in created_projects_metadata))
            
            # Extract child db ids from content
            created_users = await self.extract_child_db_ids(created_users)
            created_projects = await self.extract_child_db_ids(created_projects)
            
            created_schedules = await self.get_all_schedules_from_project(created_projects)

            self.cache.compare_and_update_user_data(created_users)
            self.cache.compare_and_update_project_data(created_projects)

            await self.synced_document_manager.db_manager.update_users_and_projects(created_users, created_projects, drop_content=True)
            project_notion_ids = [project[NOTION_ID] for project in created_projects]
            await self.renew_all_schedules_in_user(created_users, project_notion_ids, created_schedules)

        # Handle Update User or Project
        await asyncio.gather(*(self.request_manager.handle_user_update_requests(user_notion_id) for user_notion_id in updated_users_metadata))
        await asyncio.gather(*(self.request_manager.handle_project_update_requests(project_notion_id) for project_notion_id in updated_projects_metadata))

        #! Handle New Schedules Or Schedules with New Mentions to Sync in Old Project
        async def sync_new_schedules_in_old_project(project, user_data):
            schedule_id = self.cache.get_notion_id_to_schedule_id(project[NOTION_ID])
            if not schedule_id:
                #! Unhandled error: schedule id is not tracked in the cache
                print("Error: Project ID Not Saved in Cache: ", project[NOTION_ID])
                return

            # Check if new schedules are created
            linked_schedules_raw = await self.notion_manager.notion.databases.query(schedule_id, **{
                "filter": {
                    "property": "負責人",
                    "people": {"is_not_empty": True}
                }
            })
            if "results" not in linked_schedules_raw or len(linked_schedules_raw["results"]) == 0:
                # print("No schedules with people linked exist.")
                return
            
            # filter out schedules that are already tracked
            linked_schedules = [schedule_raw for schedule_raw in linked_schedules_raw["results"] if not self.synced_document_manager.schedule_notion_id_is_synced(schedule_raw["id"])]

            # Fetch new schedule data including content from Notion
            linked_schedules = await asyncio.gather(*(self.notion_manager.fetch_schedule_content(schedule, project["notion_id"]) for schedule in linked_schedules))
            # pprint(linked_schedules)
            await self.renew_all_schedules_in_user(user_data, [project[NOTION_ID]], linked_schedules)
            print(f"Synced {len(linked_schedules)} new Schedules.")
        
        await asyncio.gather(*(sync_new_schedules_in_old_project(project, user_metadata) for project in project_metadata))

    #! ================ CONTROL FUNCTIONS ================

    # Startup Function: runs when start up
    async def startup(self):
        print("Starting Up Driver...")
        
        # Fetch all data from Notion, Setup Synced Document, and save into Database
        user_data, project_data = await self.get_all_users_and_projects(includes_content=True)
        user_data = await self.extract_child_db_ids(user_data)
        project_data = await self.extract_child_db_ids(project_data)
        schedule_data = await self.get_all_schedules_from_project(project_data)
        
        self.cache.refresh_user_data(user_data)
        self.cache.refresh_project_data(project_data)

        if SAVE_DATA_SAMPLE:
            NotionManager.output_to_json(user_data, "data_sample/user_data.json")
            NotionManager.output_to_json(project_data, "data_sample/project_data.json")
            NotionManager.output_to_json(schedule_data, "data_sample/schedule_data.json")
        
        await self.synced_document_manager.db_manager.update_users_and_projects(user_data, project_data, drop_content=True)
        project_notion_ids = [project[NOTION_ID] for project in project_data]
        await self.renew_all_schedules_in_user(user_data, project_notion_ids, schedule_data)
        
        # self.synced_document_manager.print()
        print("Startup Complete!")
    
    # Main Function: runs every FETCH_INTERVAL seconds
    async def driver(self):
        
        # TODO: (Advanced) Pull from Admin DB and dynamically control the fetch interval

        # Sweep Users and Projects
        await self.sweep_all_users_and_projects()

        # Sync schedules
        print("---")
        synced = await self.sweep_all_schedules()
        sync_attempt = 2
        while not synced:
            if sync_attempt > MAX_SYNC_ATTEMPTS:
                break
            print(f"--- Sync Attempt {sync_attempt} ---")
            synced = await self.sweep_all_schedules()
            sync_attempt += 1
        self.last_updated_time = datetime.now(timezone.utc).timestamp()
        print("")
        print(f"--- Last Synced at {datetime.now(timezone.utc)} ---")
        print("")

    # Async Entry FUnction
    async def main(self):
        await self.startup()
        print("Driver Running!")
        print("")
        while True:
            await self.driver()
            await asyncio.sleep(self.fetch_interval)

    # Entry Function
    def run(self):
        asyncio.run(self.main())

if __name__ == "__main__":
    print("")
    print("")
    print("")
    print("")
    print("========== PINECRAFT NOTION AUTOMATION VERSION 2025/03/30 ==========")
    print("")
    print("""	
        nnnnnnnnnnnnnnnnnnnnnnnnnnnnnn	
        nnnn                         nnnn	
        nnnnnnn                          nnnn	
        nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn	
        nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn	
        nnnnnnnn                           nnn	
        nnnnnnnn    nnnnnnnn     nnnnnnn   nnn	
        nnnnnnnn      nnnnnnn      nnn     nnn	
        nnnnnnnn      nnnnnnnn     nnn     nnn	
        nnnnnnnn      nnnnnnnnnn   nnn     nnn	
        nnnnnnnn      nnn nnnnnnn  nnn     nnn	
        nnnnnnnn      nnn  nnnnnnnnnnn     nnn	
        nnnnnnnn      nnn   nnnnnnnnnn     nnn	
        nnnnnnnn      nnn     nnnnnnnn     nnn	
        nnnnnnnn      nnn      nnnnnnn     nnn	
        nnnnnnnn    nnnnnnnn    nnnnnn     nnn
          nnnnnn                           nnn
            nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn	
              nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn	
    
        """)
    driver = Driver()
    driver.run()