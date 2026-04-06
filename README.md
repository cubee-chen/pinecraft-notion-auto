# LifeOS Automation System

## Intro
LifeOS Automation System is a Python service that synchronizes Notion workspaces with MongoDB and keeps project schedules consistent across user and project databases. It also executes scheduling workflows from Notion-driven triggers, including Gantt planning and meeting-time coordination. The project is designed to reduce manual operations and make team planning reproducible at scale.

## Team Members
- 張鈞傑 Jun-Jie (Justin) Chang
- 陳宇禎 Cubee Chen
- 蔡仁揚 Jen-Yang (Yang) Tsai
- 吳柏均 Po-Chun Wu
- 陳秉宏 Bing-Hong Chen
- 林祐萱 Yo-Xuan Lin
- 停彭蓮香 Tina Ting

## Project Overview

### Mission
Build a practical, automation-first operations layer on top of Notion so teams can manage projects with less manual effort, fewer synchronization errors, and clearer execution status.

### Details
- Product type: Notion automation engine for team operations and template workflows.
- Operating model: codebase-first workflow with environment-based configuration for deployment.
- Delivery model: single product service that can support multiple template and workflow scenarios.
- Governance focus:
  - stable synchronization behavior
  - data consistency between Notion and MongoDB
  - secure handling of environment variables and API credentials
- Presentation: [pitch_presentation.pdf](pitch_presentation.pdf)

### Lean Canvas

| Block | Summary |
| --- | --- |
| Problem | Teams lose time due to fragmented planning, duplicated updates, and inconsistent schedule data. |
| Customer Segments | Student teams, project-based groups, creators, and operators using Notion as a planning hub. |
| Unique Value Proposition | Notion-native automation that keeps data synchronized and executes planning algorithms with minimal manual work. |
| Solution | Async synchronization, version tracking, request-driven algorithm execution, and structured persistence in MongoDB. |
| Channels | Product website, Notion template users, direct team onboarding, and integration-driven adoption. |
| Revenue Streams | Productized automation support, template-linked workflows, and future value-added modules. |
| Cost Structure | Cloud runtime, database hosting, domain and operations tools, and maintenance/development effort. |
| Key Metrics | Sync success rate, trigger-to-completion latency, user schedule consistency, and active workflow usage. |
| Unfair Advantage | Deep Notion workflow understanding plus algorithm integration and reusable sync architecture. |

### Product Scope
- Synchronize user and project metadata from Notion.
- Replicate schedules between project and user databases.
- Detect and resolve version differences between Notion and database state.
- Execute algorithm requests from Notion status fields.
- Persist canonical records in MongoDB for auditability and recovery.

## Tech Details

### Stack
- Python 3.10+
- notion-client
- pymongo
- dotenv
- pandas (used by meeting workflow)
- asyncio-based orchestration

### System Architecture
- Root-level module layout (post-cleanup): core modules live at repository root.
- Driver layer:
  - startup orchestration
  - periodic sweeping and sync control
- Integration layer:
  - Notion API manager for fetch, update, and page/database operations
- Persistence layer:
  - MongoDB manager for users, projects, and schedules
- Sync state layer:
  - cache and synced-document manager for mappings and version checks
- Request execution layer:
  - algorithm dispatch and result write-back

### Core Functions
- Full workspace fetch and cache warm-up.
- Child database ID extraction and mapping.
- User/project/schedule change detection.
- Bi-directional sync for ahead/behind versions.
- Project request handling for algorithm execution status.
- Admin-user fetch support for external integration endpoints.

### Algorithms
- Gantt scheduling:
  - Parses dependency structures and date constraints.
  - Computes critical execution outputs.
  - Writes updates back to Notion schedule pages.
- Meeting scheduling:
  - Aggregates participant availability signals.
  - Produces candidate meeting slots.
  - Updates Notion meeting tables with structured results.

### Data and Versioning Model
- Version states include:
  - UP_TO_DATE
  - AHEAD
  - BEHIND
  - NOT_TRACKED
- Canonical fields include:
  - notion_id
  - last_edited_time
  - notion_properties
  - notion_content

### Environment Configuration
Copy the example file and set values in local deployment:

```bash
cp .env.example .env
```

Required variables:

```env
ADMIN_TOKEN=
ADMIN_API_URL=
MONGO_URI=
NOTION_TOKEN=
USER_NOTION=
PROJECT_NOTION=
```

### Run

```bash
python3 -m pip install -r requirements.txt
python3 driver.py
```

Windows helper:

```bat
execute.bat
```

### Repository Structure

```text
pinecraft-notion-auto/
  admin.py
  docs.md
  driver.py
  notion_manager.py
  db_manager.py
  synced_document.py
  cache.py
  request_manager.py
  execute.bat
  gantt/
  gantt_output.json
  meeting/
  requirements.txt
  .env.example
```
