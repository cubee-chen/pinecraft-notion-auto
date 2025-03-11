# Data structure to store and index the SyncedDocument
class SyncedDocumentManager:
    def __init__(self):
        self.map = {}
        self.task_list = []

    # Create SyncedDocument if not exist, update link if exist
    def create_document_link(self, task_notion_id, parent_notion_id):
        if parent_notion_id in self.map:
            return True
        if task_notion_id in self.task_list:
            # Task already exist in the mapping
            #! Maybe we can resort to better search methods in the future
            synced_document = None
            for notion_id in self.map:
                if self.map[notion_id]["task_notion_id"] == task_notion_id:
                    synced_document = self.map[notion_id]["synced_document"]
            if not synced_document:
                raise KeyError("No Synced Document Exist!")
            self.map[parent_notion_id] = {
                "task_notion_id": task_notion_id,
                "synced_document": synced_document
            }
        else:
            # Task doesn't exist in the mapping
            self.task_list.append(task_notion_id)
            synced_document = SyncedDocument() #! Consider passing arguments in the future
            self.map[parent_notion_id] = {
                "task_notion_id": task_notion_id,
                "synced_document": synced_document
            }
        return True

# Perform the version control program
class SyncedDocument:
    def __init__(self):
        self.last_updated = 0
        
    def check_version(self, last_updated):
        if self.last_updated == last_updated:
            # Notion is currently at the same version with DB
            return None
        elif self.last_updated > last_updated:
            # Notion is ahead of DB
            self.last_updated = last_updated
            return True
        else:
            # Notion is behind DB
            # Fetch content from DB
            content = []
            return content

    def save_version(self, content):
        # Save content to DB
        return None