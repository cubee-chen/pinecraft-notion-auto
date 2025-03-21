import asyncio
from pprint import pprint
from datetime import datetime, timezone

from db_manager import DBManager
from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache
from request_manager import RequestManager

if __name__ == "__main__":
    db_manager = DBManager()
    while True:
        command = input("> ")
        if command == "db_manager.delete_everything()":
            asyncio.run(db_manager.delete_everything())
