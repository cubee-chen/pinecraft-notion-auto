import os
import requests
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta
from pprint import pprint
from notion_client import Client
import asyncio
# ===================================
class Graph:
    '''
    This class is used for Modified Topological Sort.
    '''
    def __init__(self, vertices):
        self.V = vertices
        self.graph = defaultdict(list)
    
    def addEdge(self, u, v):
        self.graph[u].append(v)
    
    def allPaths(self, start, end):
        # ----- Return a list of all paths from start to end -----
        result = []
        path = []
        self._dfsPaths(start, end, path, result)
        return result
    
    def _dfsPaths(self, current, end, path, result):
        path.append(current)
        
        # ----- If we reached the target, record the path -----
        if current == end:
            result.append(path.copy())
        else:
            # Continue DFS for all adjacent nodes.
            for nxt in self.graph[current]:
                self._dfsPaths(nxt, end, path, result)

        # Backtrack
        path.pop()

class AsyncPollUserLogic:
    def __init__(self, user: dict[str, str]):
        self.email = user["email"]
        self.notion = Client(auth=user["notionToken"])
        self.prj_db_id = user["prj_db_id"]
        self.msn_db_id = user["msn_db_id"]
        self.previous_triggers: set[str] = set()

    async def _get_trigger_pages(self) -> set[str]:

        response = await asyncio.to_thread(
            self.notion.databases.query,
            database_id=self.prj_db_id,
            filter={
                "property": "執行演算法",
                "status": {"equals": "開始執行"}
            }
        )
        pages = response.get("results", [])

        return {page["id"] for page in pages}
    
    async def poll_user(self) -> tuple[bool, set[str]]:
        try:
            current_triggers = await self._get_trigger_pages()
        except Exception as e:
            print(f"[{self.email}] Error polling triggers: {e}")
            return (False, set())
        
        # ----- If the trigger state has not changed, do nothing -----
        if current_triggers == self.previous_triggers:
            print(f"[{self.email}] No trigger change (current: {current_triggers}).")
            return (False, set())
        
        # Update our stored trigger state.
        self.previous_triggers = current_triggers

        # ----- If there is at least one trigger, process the algorithm -----
        if current_triggers:
            print(f"[{self.email}] Trigger change detected: {current_triggers}. Launching process...")
            return (True, current_triggers)
        else:
            print(f"[{self.email}] No active triggers found.")
            return (False, set())

class AsyncPollUserManager:
    def __init__(self, users: list[dict[str, str]]):
        # Create a dict mapping email to poller instance.
        self.pollers = {user["email"]: AsyncPollUserLogic(user) for user in users}

    def update_users(self, new_users: list[dict[str, str]]):
        # Add new pollers for users not already present.
        for user in new_users:
            if user["email"] not in self.pollers:
                self.pollers[user["email"]] = AsyncPollUserLogic(user)

    async def poll_all(self):
        tasks = [poller.poll_user() for poller in self.pollers.values()]
        results = await asyncio.gather(*tasks)
        for poller, (triggered, current_triggers) in zip(self.pollers.values(), results):
            if triggered:
                for trigger in current_triggers:  # For each trigger, launch the algorithm.
                    await asyncio.to_thread(
                        main_algorithm,
                        {
                            "email": poller.email,
                            "notion": poller.notion,
                            "prj_db_id": poller.prj_db_id,
                            "msn_db_id": poller.msn_db_id,
                            "current_triggers": {trigger}  # pass the single trigger in a set
                        }
                    )

# ===================================
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
        # Store all current trigger page IDs as a list:
        self.current_triggers = list(userTriggered["current_triggers"])

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

    # ----- finally make the trigger status to "執行完成" -----
    def update_trigger_property(self, current_trigger) -> None:
        try:
            self.notion.pages.update(
                page_id=current_trigger,
                properties={
                    "執行演算法": {
                        "status": {"name": "執行完成"}
                    }
                }
            )
            print(f"Updated trigger for page {current_trigger} to '執行完成'.")
        except Exception as e:
            print(f"Error updating trigger for page {current_trigger}: {e}")

# ===================================
def fetch_all_users() -> list[dict]:

    # ----- Load environment variables -----
    load_dotenv()
    admin_token = os.getenv("ADMIN_TOKEN")
    api_url = os.getenv("ADMIN_API_URL")

    # ----- Fetch all users -----
    full_url = f"{api_url}/api/admin/users"
    headers = {
        "Authorization": f"Bearer {admin_token}",
    }
    response = requests.get(full_url, headers=headers)

    if response.ok:
        try:
            users = response.json()
        except ValueError as e:
            print(f"JSON decode error: {e}. Response text: {response.text}")
            return []
    else:
        print(f"Error fetching users: {response.status_code} {response.text}")
        return []
    
    # ----- Filter users and store their info into "auth_users" -----
    auth_users = []
    i = 0
    for user in users:
        purchased_list = user["purchasedTemplates"]
        db_ids = user["notionInfo"]

        # Only when user has purchase "專案管理" template and has input their notion database IDs
        # can they access and execute the algorithm.
        if (("專案管理" in db_ids) and ("專案管理" in purchased_list)):
            prj_db_id, msn_db_id = db_ids["專案管理"]["prj_db_id"], db_ids["專案管理"]["msn_db_id"]

            user_info_temp = {}    # temporary dict to store user info
            user_info_temp["email"] = user["email"]
            user_info_temp["notionToken"] = user["notionToken"]
            user_info_temp["prj_db_id"] = prj_db_id
            user_info_temp["msn_db_id"] = msn_db_id
            
            auth_users.append(user_info_temp)
            i += 1

    return auth_users

def main_algorithm(user: dict) -> None:
    # ====================================
    #  Fetching Data                    
    # ====================================
    fd = FetchData(user)   # Initialize FetchData class

    # ----- Loop over each trigger in the list -----
    for trigger in fd.current_triggers:
        print(f"[{user['email']}] Processing trigger: {trigger}")

        fd.current_trigger = trigger
        start_date, end_date = fd.get_project_info(trigger)
        N, btm_mission_dict = fd.get_btm_mission()
        nested_mission_dict = fd.get_parentChild_mission(btm_mission_dict)

        # pprint(btm_mission_dict)
        # pprint(nested_mission_dict)

        # ====================================
        #  Algorithm              
        # ====================================
        
        # ----- Initialize Graph -----
        start_node = 0
        end_node = N+1
        g = Graph(N+2)   
        Num_depend_used = []

        # ----- Add Edges -----
        for i in range(N):
            i += 1
            depend_list = btm_mission_dict[i]["depend_list"]

            # Add start edge
            if len(depend_list) == 0:
                g.addEdge(start_node, i)
            # Add middle edge
            else:
                for j in range(len(depend_list)):
                    g.addEdge(depend_list[j], i)
                    Num_depend_used.append(depend_list[j])

        #　Add end edge
        miss_num = [x for x in range(1, N+1) if x not in Num_depend_used]
        for i in range(len(miss_num)):
            g.addEdge(miss_num[i], end_node)

        # Get all paths
        all_paths = g.allPaths(start_node, end_node)
            
        # ----- identify critical path -----
        critical_spend = 0
        
        for path in all_paths:
            path = path[1:-1] # omit start and end node
            
            total_spend = 0
            for node in path:
                total_spend += btm_mission_dict[node]["spend"]
                
            if total_spend > critical_spend:
                critical_spend = total_spend
                critical_path = path

                # Add start and end node back to critical path since we omitted them earlier.
                critical_path.insert(0, start_node)
                critical_path.append(end_node)

        # Move critical path to the end of all_paths, so that it will overwrite other paths at the end.
        all_paths.remove(critical_path)
        all_paths.append(critical_path)

        # print(f"critical_path:{critical_path}")

        # ====================================
        #  Calculating ES & EF with propogation
        #  Store Bottom mission in "date_dict"
        #  Store Parent and Child in "nested_mission_dict"       
        # ====================================

        date_dict = defaultdict(dict)
        # ----- Calculate ES & EF for bottom mission -----
        for path in all_paths:
            path = path[1:-1] # omit start and end node

            # forward propagation
            current_start = start_date
            for node in path:            
                ES = current_start
                EF = ES + timedelta(days=btm_mission_dict[node]["spend"])
                current_start = EF
                date_dict[node]["ES"] = ES.strftime("%Y-%m-%d")
                date_dict[node]["EF"] = EF.strftime("%Y-%m-%d")

            # backward propagation
            current_end = end_date
            for node in reversed(path):
                LF = current_end
                LS = LF - timedelta(days=btm_mission_dict[node]["spend"])
                current_end = LS
                date_dict[node]["LS"] = LS.strftime("%Y-%m-%d")
                date_dict[node]["LF"] = LF.strftime("%Y-%m-%d")
                
            #print("path", path, "propogation done successfully")

        # pprint(date_dict)

        # ----- Calculate ES & EF for Parent and Child mission -----
        for p in range(len(nested_mission_dict)):
            for c in range(len(nested_mission_dict[p])-3): # omit 'ES', 'EF', 'parent_page_id'
                btm_list = nested_mission_dict[p][c]["btm_node"]
                smallest_c_es = min(date_dict[node]["ES"] for node in btm_list)
                largest_c_ef = max(date_dict[node]["EF"] for node in btm_list)

                nested_mission_dict[p][c]["ES"] = smallest_c_es
                nested_mission_dict[p][c]["EF"] = largest_c_ef
            
            child_list = [child for child in nested_mission_dict[p]][3:]
            smallest_p_es = min(nested_mission_dict[p][child]["ES"] for child in child_list)
            largest_p_ef = max(nested_mission_dict[p][child]["EF"] for child in child_list)
            nested_mission_dict[p]["ES"] = smallest_p_es
            nested_mission_dict[p]["EF"] = largest_p_ef

        # pprint(nested_mission_dict)

        # ====================================
        #  Updating data back to notion              
        # ====================================
        ud = UpdateData(user)
        ud.update_btm_mission(btm_mission_dict, date_dict, critical_path)
        ud.update_parentChild(nested_mission_dict)
        ud.update_trigger_property(fd.current_trigger)
        
        print(f"[{user['email']}] Finished processing algorithm for trigger {trigger}.")

async def main_async() -> None:
    # ----- Initalize -----
    users = fetch_all_users()
    manager = AsyncPollUserManager(users)

    # ----- Parameters -----
    update_interval =5  # seconds
    last_update = datetime.now()

    # ----- Main loop -----
    while True:
        # Periodically re-fetch new registered users from User database.
        now = datetime.now()
        if (now - last_update).total_seconds() > update_interval:
            new_users = fetch_all_users()
            manager.update_users(new_users)
            last_update = now

        await manager.poll_all()
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main_async())
    

