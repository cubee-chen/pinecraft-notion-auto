# Data structure to store and index the TrackedDocument
class TrackedDocumentManager:
    def __init__(self):
        pass

# Perform the version control program
class TrackedDocument:
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