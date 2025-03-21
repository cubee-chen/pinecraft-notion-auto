# Naming Conventions

- `raw_X_metadata`: Raw object fetched from Notion, containing `"results": []`
- `X_metadata`: Object containing `NOTION_ID`, `LAST_EDITED_TIME`, and `NOTION_PROPERTIES`
- `X_data`: Object containing `NOTION_ID`, `LAST_EDITED_TIME`, `NOTION_PROPERTIES`, and `NOTION_CONTENT`

# Driver.py Functions Overview

## Core Purpose
`driver.py` is a synchronization engine that keeps Notion databases in sync across user and project pages. It periodically fetches data from Notion, detects changes, and ensures all related pages stay updated.

## System Components
- **Driver Class**: Main controller that orchestrates synchronization operations
- **NotionManager**: Handles Notion API interactions
- **SyncedDocumentManager**: Tracks document versions and sync status
- **Cache**: Maintains local copies of data for comparison
- **RequestManager**: Processes update requests

## Key Functions

### Startup Functions
1. `get_all_users_and_projects()`: Fetches all user and project data from Notion
2. `extract_child_db_ids()`: Finds child database IDs within Notion pages
3. `get_all_schedules_from_project()`: Retrieves schedule data from projects
4. `renew_all_schedules_in_user()`: Updates user schedules with the latest project schedules

### Driver Functions
1. `sweep_all_schedules()`: Synchronizes schedule data by:
   - Checking version status (ahead/behind/up-to-date)
   - Updating database for ahead versions
   - Updating Notion for behind versions
   
2. `sweep_all_users_and_projects()`: Handles user and project updates:
   - Detects created/updated users and projects
   - Processes update requests
   - Syncs new schedules in existing projects

### Control Functions
1. `startup()`: Initializes system by fetching all data and populating caches
2. `driver()`: Main execution loop that performs sweeps and synchronization
3. `main()`: Runs the startup and then enters the driver loop
4. `run()`: Entry point that executes the async main function

## Synchronization Logic
The system maintains version control with four states:
- **UP_TO_DATE**: No action needed
- **AHEAD**: Notion version is newer than DB (save to DB)
- **BEHIND**: DB version is newer than Notion (update Notion)
- **NOT_TRACKED**: Page isn't in version control system


# NotionManager.py

This file defines a `NotionManager` class that serves as the primary interface between a web application and the Notion API. It handles synchronization, data retrieval, and modification operations for users, projects, and schedules.

## Core Functionality

- **API Communication**: Establishes connection to Notion using the AsyncClient and authentication token
- **Data Retrieval**: Fetches user, project, and schedule data from Notion databases
- **Synchronization**: Manages the flow of schedule data between project databases and user databases
- **Data Conversion**: Transforms data between different formats required by users and projects

## Key Methods

- **Fetching Operations**:
  - `fetch_all_user_metadata()` / `fetch_all_project_metadata()`: Bulk retrieval of user and project information
  - `fetch_user_content()` / `fetch_project_content()`: Detailed content retrieval for specific entities
  - `fetch_schedule_by_notion_id()` / `fetch_schedule_by_parent_project()`: Schedule-related retrieval methods

- **Management Operations**:
  - `insert_schedules_to_user_schedule_db()`: Copies project schedules to relevant user databases
  - `create_user_schedule()` / `update_user_schedule()` / `update_project_schedule()`: CRUD operations for schedules
  - `delete_user_schedules_by_project_notion_id()`: Removes outdated schedules from user databases

- **Utility Functions**:
  - Data conversion methods for transforming between project and user schedule formats
  - Time conversion utilities for Notion timestamps
  - Helper methods for extracting and formatting text content

The class integrates with `Cache` and `SyncedDocumentManager` to maintain data consistency and optimize performance when interfacing with the Notion API.

# SyncedDocument.py

This file implements a synchronization system between Notion documents and a MongoDB database, acting as middleware to manage document versions. It contains two main classes:

## Core Components

### SyncedDocumentManager Class
- **Central Coordinator**: Manages mappings between instance IDs and schedule documents
- **Version Tracking**: Tracks sync status with constants (NOT_TRACKED, UP_TO_DATE, AHEAD, BEHIND)
- **Link Management**: Creates and maintains relationships between documents

### SyncedDocument Class
- **Version Control**: Handles the comparison between Notion documents and database versions
- **Persistence**: Interfaces with DBManager to save and retrieve document versions

## Key Methods

- **Tracking and Identification**:
  - `create_instance_link()`: Establishes connections between documents
  - `instance_notion_id_is_synced()` / `schedule_notion_id_is_synced()`: Verifies if IDs are being tracked

- **Version Management**:
  - `check_version_by_notion_id()`: Determines if Notion or database has the newer version
  - `get_latest_version_by_notion_id()`: Retrieves the most recent document
  - `save_version_by_notion_id()`: Persists updated documents to the database

- **Synchronization**:
  - `sync_project_schedule()`: Coordinates project schedule updates
  - `check_version()`: Compares timestamps to determine version status

# DBManager.py

This file defines a `DBManager` class that handles interactions with a MongoDB database for a web service that integrates with Notion. Here's what it does:

## Core Functionality

- **Database Connectivity**: Establishes and maintains a connection to MongoDB
- **Data Persistence**: Provides methods to update and retrieve user, project, and schedule data
- **Data Validation**: Ensures data integrity before storage with validation methods

## Key Methods

- **Setup and Configuration**:
  - Loads environment variables for database connection
  - Establishes connections to collections for users, projects, and schedules

- **Data Operations**:
  - `update_users_and_projects()`: Bulk updates users and projects with optional content dropping
  - `update_user_by_notion_id()` / `update_project_by_notion_id()` / `update_schedule_by_notion_id()`: Entity-specific update methods
  - `get_user_by_notion_id()` / `get_schedule_by_notion_id()`: Retrieve specific records by Notion ID

- **Validation**:
  - `data_validation()`: Verifies required fields exist in database entries
  - `schedule_property_validation()`: Ensures schedule properties contain essential fields


# Cache.py

This file defines a `Cache` class that serves as a local storage mechanism for user and project data, with a focus on managing interactions with Notion. Here's what it does:

## Core Functionality

- **Data Storage**: Maintains collections of user and project data, along with index dictionaries for efficient lookup
- **Mapping Services**: Provides conversion between different ID systems (user IDs, Notion IDs, schedule IDs)
- **Data Synchronization**: Compares incoming data with cached data to identify created or updated records

## Key Methods

- **Data Management**:
  - `refresh_user_data()` / `refresh_project_data()`: Complete replacement of stored data
  - `compare_and_update_user_data()` / `compare_and_update_project_data()`: Smart updates that track changes
  - `get_user_data()` / `get_project_data()`: Data retrieval methods

- **Lookup Services**:
  - `get_user_by_notion_id()` / `get_project_by_notion_id()`: Object retrieval by Notion ID
  - `get_user_id_to_notion_id()` / `update_user_id_to_notion_id()`: User ID mapping functions
  - `get_notion_id_to_schedule_id()` / `update_notion_id_to_schedule_id()`: Schedule ID mapping functions

