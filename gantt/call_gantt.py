from collections import defaultdict
from datetime import datetime

class FetchData:
    '''
    This class is used to fetch the necessary data from User's Notion database.
    Mission Structure: Parent -> Child -> Bottom 
    '''
    def __init__(self, userTriggered: dict[str, str]):
        self.email = userTriggered["email"]
        self.notion = userTriggered["notion"]
        self.prj_db_id = userTriggered["prj_db_id"]
        self.msn_db_id = userTriggered["msn_db_id"]
        self.current_trigger = userTriggered["current_trigger"]

    # ----- Get the corresponded project info based on trigger page ID -----
    def get_project_info(self, trigger: str):
        page = self.notion.pages.retrieve(page_id=trigger)
        start_date = datetime.strptime(
            page["properties"]["時間"]["date"]["start"],
            "%Y-%m-%d"
        )
        end_date = datetime.strptime(
            page["properties"]["時間"]["date"]["end"],
            "%Y-%m-%d"
        )
        return start_date, end_date
    
    # ----- Get the bottom mission info that 所屬專案 contains trigger page ID -----
    def get_btm_mission(self):
        btm_mission = self.notion.databases.query(
            database_id=self.msn_db_id,
            filter={
                "and": [
                {"property": "子任務",
                    "relation": {
                        "is_empty": True
                    }},
                {"property": "所屬專案",
                    "relation": {
                        "contains": self.current_trigger
                    }}
                ]
            }
        )
        # Number of total mission
        N = len(btm_mission["results"])

        btm_mission_dict = defaultdict(dict)
        for i in range(N):
            node = i+1    # Serial node start with 1
            page_id = btm_mission["results"][i]["id"]
            page = self.notion.pages.retrieve(page_id=page_id)
            title = page["properties"]["名稱"]["title"][0]["plain_text"]
            depend_id_list = page["properties"]["前置任務"]["relation"]
            spend = page["properties"]["預估所需時長（天）"]["number"]
        
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
        top_mission = self.notion.databases.query(
            database_id=self.msn_db_id,
            filter={
                "and": [
                {"property": "父任務",
                    "relation": {
                        "is_empty": True
                    }},
                {"property": "所屬專案",
                    "relation": {
                        "contains": self.current_trigger
                    }}
                ]
            }
        )
        
        # Number of Parent mission
        N_parent = len(top_mission["results"])

        # Dict contains Parent and Child mission info
        nested_mission_dict = defaultdict(dict)
        for m in range(N_parent):

            page_id = top_mission["results"][m]["id"]
            page = self.notion.pages.retrieve(page_id=page_id)
            child_id_list = page["properties"]["子任務"]["relation"]
            
            # ----- Update parent info -----
            nested_mission_dict[m] = {
                "parent_page_id": page_id,
                "ES": "",
                "EF": ""
            }  

            # ----- Get Child mission for each Parent -----
            for i in range(len(child_id_list)):
                child_page_id = child_id_list[i]["id"]
                child_page = self.notion.pages.retrieve(page_id=child_page_id)
                btm_id_list = child_page["properties"]["子任務"]["relation"]
                
                # ----- Replace bottom mission id with node number -----
                btm_node_list = []
                for j in range(len(btm_id_list)):
                    btm_page = self.notion.pages.retrieve(page_id=btm_id_list[j]["id"])
                    btm_node_list.append([k for k, v in btm_mission_dict.items() if v["page_id"] == (btm_page["id"])][0])
                
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
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(sys.path[0]), 'gantt'))
    from gantt.main import GanttGenerator
    from notion_client import Client

    # ===== Example User info =====
    CUBEE_NOTION_TOKEN = "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"
    user = {
        "email": "cubee0405@gmail.com",
        "notion": Client(auth=CUBEE_NOTION_TOKEN),
        "prj_db_id": "17f37075d466819b9abdc563f49ea37c",
        "msn_db_id": "17f37075d4668154aac8d63dc3d48669",
        "current_trigger": "19437075d46680bca9c9d25b69b7a9b7"
    }
    # ===== Fetch Notion info =====
    fd = FetchData(user)
    start_date, end_date = fd.get_project_info(fd.current_trigger)
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