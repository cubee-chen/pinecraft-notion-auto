from pprint import pprint
from datetime import datetime
from collections import defaultdict
import asyncio
import pandas as pd

from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache
from gantt.call_gantt import ParseData, UpdateData
from gantt.main import GanttGenerator
from meeting.meeting_alg import main_algorithm_meeting_time

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
        
        if project[NOTION_PROPERTIES]["會議排程演算法"]["status"]["name"] == "執行請求":
            await self.handle_meeting_request(project)

    #! =================== Handle Requests ===================
    async def handle_gantt_request(self, project):
        project["schedule"] = self.cache.get_notion_id_to_schedule_id(project[NOTION_ID])
        print(f"GANTT REQUEST: {project[NOTION_ID]}")
        await self.notion_manager.update_project_partial_properties(project[NOTION_ID], {
            "甘特圖演算法": {"status": {"name": "執行中..."}}
        })
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
        gantt_output = gantt.run()
        NotionManager.output_to_json(gantt_output, "gantt_output.json")

        # ===== Update Notion =====
        if gantt_output["success"] == True:
            gantt_result = gantt_output["result"]
            update_data = UpdateData()
            btm_mission_to_be_updated = update_data.update_btm_mission(
                btm_mission_dict=gantt_result["btm_mission_dict"],
                date_dict=gantt_result["date_dict"],
                critical_path=gantt_result["critical_path"]
            )
            parent_child_to_be_updated = update_data.update_parentChild(nested_mission_dict=gantt_result["nested_mission_dict"])
            
            # Merge the two dicts
            to_be_updated = defaultdict(dict)
            for key, subdict in btm_mission_to_be_updated.items():
                to_be_updated[key].update(subdict)
            for key, subdict in parent_child_to_be_updated.items():
                to_be_updated[key].update(subdict)
            to_be_updated = dict(to_be_updated)

            async def update_schedule(schedule_id, properties_to_be_updated):
                # pprint(properties_to_be_updated)
                await self.notion_manager.update_project_schedules_by_partial_properties(schedule_id, properties_to_be_updated)

            await asyncio.gather(*(update_schedule(schedule_id, to_be_updated[schedule_id]) for schedule_id in to_be_updated))

            # change the notion '執行狀態' to 成功
            await self.notion_manager.update_project_partial_properties(project[NOTION_ID], {
                "甘特圖演算法": {"status": {"name": "執行完成"}}
            })
        else:
            error_message = gantt_output["error_msg"]
            # UPDATE NOTION WITH ERROR MSG
            await self.notion_manager.update_project_partial_properties(project[NOTION_ID], {
                "系統訊息": { "rich_text": [ { "text": { "content": error_message } }]}
            })
        
    async def handle_meeting_request(self, project):
        users_meeting = [{ "email": self.cache.get_person_id_to_notion_id(person_id["id"]) } for person_id in project[NOTION_PROPERTIES]["成員"]["people"]]

        async def fetch_user_class_meeting(user_meeting):
            user_notion_id = user_meeting["email"]
            class_schedule_id = self.cache.get_notion_id_to_class_schedule_id(user_notion_id)
            if class_schedule_id == None:
                users_meeting.remove(user_meeting)
                return
            user_meeting["timetable_db"] = await self.notion_manager.fetch_class_schedule_by_db_id(class_schedule_id)
            
            schedule_id = self.cache.get_notion_id_to_schedule_id(user_notion_id)
            if schedule_id == None:
                users_meeting.remove(user_meeting)
                return
            user_meeting["calendar_db"] = await self.notion_manager.fetch_schedule_by_db_id(schedule_id)
            
        await asyncio.gather(*(fetch_user_class_meeting(user_meeting) for user_meeting in users_meeting))
        meeting_result_df = main_algorithm_meeting_time(users_meeting)
        print(meeting_result_df)