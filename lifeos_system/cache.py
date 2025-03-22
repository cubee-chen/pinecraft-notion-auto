from pprint import pprint
import json

#! =================== Define Commonly Used Keys ===================
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

#! =================== Act as Storage for Local Variables ===================
class Cache:
    def __init__(self):
        # Plain Data (Private)
        self.__user_data = []
        self.__project_data = []
        # Reverse Mapping (Private)
        self.__user_index_dict = {}
        self.__project_index_dict = {}
        # Conversion (Private)
        self.__person_id_to_notion_id = {}
        self.__notion_id_to_schedule_id = {}
        self.__notion_id_to_class_schedule_id = {}

    #! =================== Functions ===================
    def print(self):
        print("'user_id_to_notion_id':")
        pprint(self.__person_id_to_notion_id)
        print("'notion_id_to_schedule_id':")
        pprint(self.__notion_id_to_schedule_id)
        print("'user_data':")
        pprint(self.__user_data)
        print("'project_data':")
        pprint(self.__project_data)

    #! =================== Index Dict ===================
    # Maintain the quality of index dict (Hidden Method)
    def __refresh_user_index_dict(self):
        self.__user_index_dict = {}
        for i in range(len(self.__user_data)):
            user = self.__user_data[i]
            self.__user_index_dict[user[NOTION_ID]] = i
    
    # Maintain the quality of index dict (Hidden Method)
    def __refresh_project_index_dict(self):
        self.__project_index_dict = {}
        for i in range(len(self.__project_data)):
            project = self.__project_data[i]
            self.__project_index_dict[project[NOTION_ID]] = i

    #! =================== User and Project Data =================== 
    # save user_data -> hard save
    def refresh_user_data(self, user_data):
        self.__user_data = user_data
        self.__refresh_user_index_dict()

    # compare and update user_data -> returns the user notion_id that have difference
    def compare_and_update_user_data(self, user_data):
        updated_users = []
        created_users = []
        old_user_notion_id = [user[NOTION_ID] for user in self.__user_data]
        for user in user_data:
            # Check if there are new users
            if user[NOTION_ID] not in old_user_notion_id:
                self.__user_data.append(user)
                created_users.append(user)
                continue

            # Check if property has changed
            saved_user = self.__user_data[old_user_notion_id.index(user[NOTION_ID])]
            saved_dict = json.dumps(saved_user[NOTION_PROPERTIES], sort_keys=True)
            incoming_dict = json.dumps(user[NOTION_PROPERTIES], sort_keys=True)
            
            # Properties Changed
            if saved_dict != incoming_dict:
                updated_users.append(user)

            # Hard Refresh All (For DB Ids, Updated Time etc.)
            self.__user_data[old_user_notion_id.index(user[NOTION_ID])] = user

        self.__refresh_user_index_dict()
        return created_users, updated_users

    # get user_data
    def get_user_data(self):
        return self.__user_data
    
    # hard save project_data
    def refresh_project_data(self, project_data):
        self.__project_data = project_data
        self.__refresh_project_index_dict()

    # compare and update project_data -> returns the project notion_id that have difference
    def compare_and_update_project_data(self, project_data):
        updated_projects = []
        created_projects = []
        old_project_notion_id = [project[NOTION_ID] for project in self.__project_data]
        for project in project_data:
            # Check if there are new projects
            if project[NOTION_ID] not in old_project_notion_id:
                self.__project_data.append(project)
                created_projects.append(project)
                continue

            # Check if property has changed
            saved_project = self.__project_data[old_project_notion_id.index(project[NOTION_ID])]
            saved_dict = json.dumps(saved_project[NOTION_PROPERTIES], sort_keys=True)
            incoming_dict = json.dumps(project[NOTION_PROPERTIES], sort_keys=True)
            
            # Properties Changed
            if saved_dict != incoming_dict:
                updated_projects.append(project)

            # Hard Refresh All (For DB Ids, Updated Time etc.)
            self.__project_data[old_project_notion_id.index(project[NOTION_ID])] = project

        self.__refresh_project_index_dict()
        return created_projects, updated_projects

    # get project_data
    def get_project_data(self):
        return self.__project_data

    #! =================== Mappings ===================
    # notion_id -> user object
    def get_user_by_notion_id(self, notion_id):
        if notion_id not in self.__user_index_dict:
            self.__refresh_user_index_dict()
            if notion_id not in self.__user_index_dict:
                #! Error: User not Saved in Cache
                return None
        return self.__user_data[self.__user_index_dict[notion_id]]
    
    # notion_id -> project object
    def get_project_by_notion_id(self, notion_id):
        if notion_id not in self.project_index_dict:
            self.__refresh_project_index_dict()
            if notion_id not in self.project_index_dict:
                #! Error: User not Saved in Cache
                return None
        return self.__project_data[self.project_index_dict[notion_id]]

    # user_id -> notion_id cache
    def get_person_id_to_notion_id(self, person_id):
        if person_id not in self.__person_id_to_notion_id:
            return None
        return self.__person_id_to_notion_id[person_id]
    def update_person_id_to_notion_id(self, person_id, notion_id):
        self.__person_id_to_notion_id[person_id] = notion_id
    
    #! Brute Force
    def get_notion_id_to_person_id(self, notion_id):
        for user_id in self.__person_id_to_notion_id:
            if self.__person_id_to_notion_id[user_id] == notion_id:
                return user_id
        return None

    # notion_id -> schedule_id (notion_id) cache
    def get_notion_id_to_schedule_id(self, notion_id):
        if notion_id not in self.__notion_id_to_schedule_id:
            return None
        return self.__notion_id_to_schedule_id[notion_id]
    def update_notion_id_to_schedule_id(self, notion_id, schedule_id):
        self.__notion_id_to_schedule_id[notion_id] = schedule_id

    # notion_id -> class_schedule_id (notion_id) cache
    def get_notion_id_to_class_schedule_id(self, notion_id):
        if notion_id not in self.__notion_id_to_class_schedule_id:
            return None
        return self.__notion_id_to_class_schedule_id[notion_id]
    def update_notion_id_to_class_schedule_id(self, notion_id, class_schedule_id):
        self.__notion_id_to_class_schedule_id[notion_id] = class_schedule_id