from collections import defaultdict
from datetime import datetime
from gantt.main import GanttGenerator
from pprint import pprint

#! ============ Define Commonly Used Keys =============
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

#! =================== Define Class ===================
class ParseData:
    '''
    This class is used to fetch the necessary data from User's Notion database.
    Mission Structure: Parent -> Child -> Bottom 
    '''
    def __init__(self, schedule_data, project):
        self.project = project
        self.schedule_data = schedule_data

    # ----- Get the corresponded project info based on trigger page ID -----
    def parse_start_and_end_dates(self):
        start_date = datetime.strptime(
            self.project[NOTION_PROPERTIES]["時間"]["date"]["start"],
            "%Y-%m-%d"
        )
        end_date = datetime.strptime(
            self.project[NOTION_PROPERTIES]["時間"]["date"]["end"],
            "%Y-%m-%d"
        )
        return start_date, end_date
    
    # ----- Get the bottom mission info that 所屬專案 contains trigger page ID -----
    def get_btm_mission(self):
        # filter the schedules for which the sub-items don't have relations
        btm_mission = [schedule for schedule in self.schedule_data if len(schedule[NOTION_PROPERTIES]["子任務"]["relation"]) == 0]
        
        # Number of total mission
        N = len(btm_mission)
        pprint(btm_mission)

        btm_mission_dict = defaultdict(dict)
        for i in range(N):
            node = i+1    # Serial node start with 1
            page_id = btm_mission[i][NOTION_ID]
            title = btm_mission[i][NOTION_PROPERTIES]["任務名稱"]["title"][0]["plain_text"]
            depend_id_list = btm_mission[i][NOTION_PROPERTIES]["前置任務"]["relation"]
            spend = btm_mission[i][NOTION_PROPERTIES]["預估所需時長(天)"]["number"]
        
            # ----- Load basic info to dict -----
            btm_mission_dict[node]["page_id"] = page_id
            btm_mission_dict[node]["title"] = title
            btm_mission_dict[node]["depend_id_list"] = depend_id_list
            btm_mission_dict[node]["spend"] = spend
        
        # ----- Replace "depend_id_list" with "depend_list" -----
        for i in range(N):
            node = i+1
            depend_list = []

            dependIdList_per_mission = btm_mission_dict[node]["depend_id_list"]

            if len(dependIdList_per_mission) == 0:
                btm_mission_dict[node]["depend_list"] = []  # update btm_mission_dict with empty array
            
            else:
                for dm in dependIdList_per_mission:    # "dm" stands for depend mission
                    matches = [k for k, v in btm_mission_dict.items() if v["page_id"] == dm["id"]]
                    if matches:
                        depend_list.append(matches[0])  # Append the first match
                    else:
                        print(f"Warning: No match found for id {dm['id']} in node {node}")

                # ----- Update depend list in btn_mission_dict -----    
                btm_mission_dict[node]["depend_list"] = depend_list
            
        return (N, btm_mission_dict)
    
    # ----- Get the Parent and Child mission info that 所屬專案 contains trigger page ID -----
    def get_parentChild_mission(self, btm_mission_dict):
        top_mission = [schedule for schedule in self.schedule_data if len(schedule[NOTION_PROPERTIES]["父任務"]["relation"]) == 0]
        
        # Number of Parent mission
        N_parent = len(top_mission)

        # Dict contains Parent and Child mission info
        nested_mission_dict = defaultdict(dict)
        print("========== top_mission ==========")
        # pprint(top_mission)
        for m in range(N_parent):

            page_id = top_mission[m][NOTION_ID]
            child_id_list = top_mission[m][NOTION_PROPERTIES]["子任務"]["relation"]
            
            # ----- Update parent info -----
            nested_mission_dict[m] = {
                "parent_page_id": page_id,
                "ES": "",
                "EF": ""
            }  

            # ----- Get Child mission for each Parent -----
            for i in range(len(child_id_list)):
                child_page_id = child_id_list[i]["id"]
                child_page = [schedule for schedule in self.schedule_data if schedule[NOTION_ID] == child_page_id][0]
                btm_id_list = child_page[NOTION_PROPERTIES]["子任務"]["relation"]
                
                # ----- Replace bottom mission id with node number -----
                btm_node_list = []
                for j in range(len(btm_id_list)):
                    btm_page_id = btm_id_list[j]["id"]
                    btm_page = [schedule for schedule in self.schedule_data if schedule[NOTION_ID] == btm_page_id][0]
                    btm_node_list.append([k for k, v in btm_mission_dict.items() if v["page_id"] == (btm_page[NOTION_ID])][0])
                
                # ----- Update Child info -----
                nested_mission_dict[m][i] = {
                    "child_page_id": child_page_id,
                    "btm_node": btm_node_list,
                    "ES": "",
                    "EF": ""
                }

        return nested_mission_dict

class UpdateData:
    '''
    This class is used to update the User's Notion database with the calculated dates and critical path.
    '''
    def __init__(self, userTriggered: dict[str, str]):
        self.notion = userTriggered["notion"]
    
    def update_btm_mission(self, btm_mission_dict, date_dict, critical_path):
            for node in date_dict.keys():
                page_id = btm_mission_dict[node]["page_id"]
                self.notion.pages.update(
                    page_id=page_id,
                    properties={"時間": {"date": {
                        "start": date_dict[node]["ES"],
                        "end": date_dict[node]["EF"]}
                    }}
                )
            # ----- Overlay critical path and mark with "$" -----
            for node in critical_path[1:-1]:
                page_id = btm_mission_dict[node]["page_id"]
                self.notion.pages.update(
                    page_id=page_id,
                    properties={"名稱": {
                            "title": [{
                            "text": {"content": "$" + btm_mission_dict[node]["title"]},
                            }]}}
                )
    
    def update_parentChild(self, nested_mission_dict):
        for p in range(len(nested_mission_dict)):
            page_id = nested_mission_dict[p]["parent_page_id"]
            self.notion.pages.update(
                page_id=page_id,
                properties={"時間": {"date": {
                    "start": nested_mission_dict[p]["ES"],
                    "end": nested_mission_dict[p]["EF"]}
                }}
            )
            for c in range(len(nested_mission_dict[p])-3):
                page_id = nested_mission_dict[p][c]["child_page_id"]
                self.notion.pages.update(
                page_id=page_id,
                properties={"時間": {"date": {
                    "start": nested_mission_dict[p][c]["ES"],
                    "end": nested_mission_dict[p][c]["EF"]}
                    }}
                )

def lifeos_system():
    
    # ===== Example User info =====
    user = {
        "email": "",
        "notion": None,
        "prj_db_id": "",
        "msn_db_id": "",
        "current_trigger": ""
    }
    # ===== Fetch Notion info =====
    fd = ParseData(user)
    start_date, end_date = fd.parse_start_and_end_dates()
    N, btm_mission_dict = fd.get_btm_mission()
    nested_mission_dict = fd.get_parentChild_mission(btm_mission_dict)

    # ===== Calling Gantt function =====
    gantt = GanttGenerator(start_date, end_date, N, btm_mission_dict, nested_mission_dict)
    output = gantt.run()
    print(output)

    # ===== Update Notion =====
    if output["success"] == True:
        res = output["result"]
        ud = UpdateData(user)
        ud.update_btm_mission(
            btm_mission_dict=res["btm_mission_dict"],
            date_dict=res["date_dict"],
            critical_path=res["critical_path"]
        )
        ud.update_parentChild(nested_mission_dict=res["nested_mission_dict"])
        #TODO: ddm change the notion '執行狀態' to 成功
    else:
        msg = output["error_msg"]
        #TODO: ddm UPDATE NOTION WITH ERROR MSG
    
    print("Process Done Successfully!")

# ========================
if __name__ == "__main__":
    lifeos_system()