from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache

# ============ Define Commonly Used Keys =============
NOTION_ID = "notion_id"
NOTION_PROPERTIES = "notion_properties"
NOTION_CONTENT = "notion_content"
LAST_EDITED_TIME = "last_edited_time"

# =================== Define Class ===================
class RequestManager:
    def __init__(self, notion_manager: NotionManager, cache: Cache, synced_document_manager: SyncedDocumentManager):
        self.notion_manager = notion_manager
        self.cache = cache
        self.synced_document_manager = synced_document_manager

    # =================== Classify and Disperse ===================
    def handle_user_requests_by_id(self, user_notion_id):
        pass

    def handle_project_requests_by_id(self, project_notion_id):
        pass

    # =================== Handle Requests ===================