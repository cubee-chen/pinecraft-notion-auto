import asyncio
from pprint import pprint
from datetime import datetime, timezone

from db_manager import DBManager
from notion_manager import NotionManager
from synced_document import SyncedDocumentManager
from cache import Cache
from request_manager import RequestManager
import json

async def fetch_crms(db_manager):
    f = db_manager.db["crms"].find({})
    arr = []
    for x in f:
        arr.append(str(x))
    with open("crms.json", "w") as file:
        file.write(json.dumps(arr, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    db_manager = DBManager()
    while True:
        command = input("> ")
        if command == "db_manager.delete_everything()":
            asyncio.run(db_manager.delete_everything())
        if command == "fetch_crms()":
            asyncio.run(fetch_crms(db_manager))
