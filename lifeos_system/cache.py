from pprint import pprint
import json

# =================== Define Commonly Used Keys ===================
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

# =================== Act as Storage for Local Variables ===================
class Cache:
    def __init__(self):
        self.user_data = []
        self.project_data = []
        self.user_id_to_notion_id = {}
        self.notion_id_to_schedule_id = {}
    
    def print(self):
        print("'user_id_to_notion_id':")
        pprint(self.user_id_to_notion_id)
        print("'notion_id_to_schedule_id':")
        pprint(self.notion_id_to_schedule_id)
        print("'user_data':")
        pprint(self.user_data)
        print("'project_data':")
        pprint(self.project_data)

    # save user_data -> hard save
    def refresh_user_data(self, user_data):
        self.user_data = user_data

    # compare and update user_data -> returns the user notion_id that have difference
    def compare_and_update_user_data(self, user_data):
        changed_notion_ids = []
        old_user_notion_id = [user[NOTION_ID] for user in self.user_data]
        for user in user_data:
            # Check if there are new users
            if user[NOTION_ID] not in old_user_notion_id:
                self.user_data.append(user)
                changed_notion_ids.append(user[NOTION_ID])
                continue

            # Check if property has changed
            saved_user = self.user_data[old_user_notion_id.index(user[NOTION_ID])]
            saved_dict = json.dumps(saved_user[NOTION_PROPERTIES], sort_keys=True)
            incoming_dict = json.dumps(user[NOTION_PROPERTIES], sort_keys=True)
            
            # Properties Changed
            if saved_dict != incoming_dict:
                changed_notion_ids.append(user[NOTION_ID])
                saved_user[NOTION_PROPERTIES] = user[NOTION_PROPERTIES]

            # Don't care about notion content

        return changed_notion_ids

    # get user_data
    def get_user_data(self):
        return self.user_data
    
    # hard save project_data
    def refresh_project_data(self, project_data):
        self.project_data = project_data

    # compare and update project_data -> returns the project notion_id that have difference
    def compare_and_update_project_data(self, project_data):
        changed_notion_ids = []
        old_project_notion_id = [project[NOTION_ID] for project in self.project_data]
        for project in project_data:
            # Check if there are new projects
            if project[NOTION_ID] not in old_project_notion_id:
                self.project_data.append(project)
                changed_notion_ids.append(project[NOTION_ID])
                continue

            # Check if property has changed
            saved_project = self.project_data[old_project_notion_id.index(project[NOTION_ID])]
            saved_dict = json.dumps(saved_project[NOTION_PROPERTIES], sort_keys=True)
            incoming_dict = json.dumps(project[NOTION_PROPERTIES], sort_keys=True)
            
            # Properties Changed
            if saved_dict != incoming_dict:
                changed_notion_ids.append(project[NOTION_ID])
                saved_project[NOTION_PROPERTIES] = project[NOTION_PROPERTIES]

            # Don't care about notion content

        return changed_notion_ids

    # get project_data
    def get_project_data(self):
        return self.project_data

    # user_id -> notion_id cache
    def get_user_id_to_notion_id(self, user_id):
        if user_id not in self.user_id_to_notion_id:
            return None
        return self.user_id_to_notion_id[user_id]
    def update_user_id_to_notion_id(self, user_id, notion_id):
        self.user_id_to_notion_id[user_id] = notion_id

    # notion_id -> schedule_id (notion_id) cache
    def get_notion_id_to_schedule_id(self, notion_id):
        if notion_id not in self.notion_id_to_schedule_id:
            return None
        return self.notion_id_to_schedule_id[notion_id]
    def update_notion_id_to_schedule_id(self, notion_id, schedule_id):
        self.notion_id_to_schedule_id[notion_id] = schedule_id