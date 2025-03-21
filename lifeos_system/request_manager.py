from pprint import pprint
from datetime import datetime

from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache
from gantt.call_gantt import ParseData
from gantt.main import GanttGenerator

#! ============ Define Commonly Used Keys =============
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

#! =================== Define Class ===================
class RequestManager:
    def __init__(self, notion_manager: NotionManager, cache: Cache, synced_document_manager: SyncedDocumentManager):
        self.notion_manager = notion_manager
        self.cache = cache
        self.synced_document_manager = synced_document_manager

    #! =================== Classify and Disperse ===================
    async def handle_user_update_requests(self, user):
        pass

    async def handle_project_update_requests(self, project):
        if project[NOTION_PROPERTIES]["甘特圖演算法"]["status"]["name"] == "執行請求":
            await self.handle_gantt_request(project)

    #! =================== Handle Requests ===================
    async def handle_gantt_request(self, project):
        project["schedule"] = self.cache.get_notion_id_to_schedule_id(project[NOTION_ID])
        print(f"GANTT REQUEST: {project[NOTION_ID]}")
        schedule_data = []
        await self.notion_manager.fetch_schedules_by_parent_project(project, schedule_data)
        parse_data = ParseData(schedule_data, project)
        start_date, end_date = parse_data.parse_start_and_end_dates()
        N, btm_mission_dict = parse_data.get_btm_mission()
        nested_mission_dict = parse_data.get_parentChild_mission(btm_mission_dict)
        # NotionManager.output_to_json(schedule_data, "schedule_gantt_input.json")
        # NotionManager.output_to_json(nested_mission_dict, "nested_mission_dict.json")
        # NotionManager.output_to_json(btm_mission_dict, "btm_mission_dict.json")
        gantt = GanttGenerator(start_date, end_date, N, btm_mission_dict, nested_mission_dict)
        output = gantt.run()
        NotionManager.output_to_json(output, "gantt_output.json")
        
