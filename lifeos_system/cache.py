from pprint import pprint

# =================== Act as Storage for Local Variables ===================
class Cache:
    def __init__(self):
        self.user_id_to_notion_id = {}
        self.notion_id_to_schedule_id = {}
    
    def print(self):
        print("'user_id_to_notion_id':")
        pprint(self.user_id_to_notion_id)
        print("'notion_id_to_schedule_id':")
        pprint(self.notion_id_to_schedule_id)
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