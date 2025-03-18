from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache


# =================== Define Class ===================
class RequestManager:
    def __init__(self, notion_manager: NotionManager, cache: Cache, synced_document_manager: SyncedDocumentManager):
        self.notion_manager = notion_manager
        self.cache = cache
        self.synced_document_manager = synced_document_manager

    # =================== Classify and Disperse ===================
    def handle_user_requests(self, user):
        pass

    def handle_project_requests(self, project):
        pass

    # =================== Handle Requests ===================