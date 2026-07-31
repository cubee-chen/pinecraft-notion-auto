# Algorithm Overview

This system is designed as a reconciliation engine that keeps Notion pages, user-facing schedule databases, and MongoDB in eventual consistency. It is not a one-shot ETL job. Instead, the code runs a perpetual control loop that continuously observes external state, classifies divergence, and applies the minimum corrective action needed to restore the desired invariant.

The core invariant is simple:

- Notion is the source of truth for live edits.
- MongoDB is the durable canonical store for synced schedule documents.
- The cache is a fast local index used to avoid repeated cross-system lookups.
- Every tracked schedule page should converge toward the newest version, regardless of whether the change originated in Notion or in the database layer.

## System Model

The repository is split into four collaborating components:

- `Driver` orchestrates the control plane and owns the polling loop.
- `NotionManager` is the integration layer and handles API calls, page fetches, database queries, and write-backs.
- `SyncedDocumentManager` is the sync-state manager. It tracks which Notion pages are attached to which canonical schedule records and performs version arbitration.
- `Cache` is a read-optimized in-memory index of users, projects, and ID mappings.

From a distributed-systems perspective, the system behaves like a bounded reconciliation loop with optimistic synchronization:

- The driver polls for changes instead of subscribing to push events.
- Each page is re-evaluated on every cycle, which gives the system a self-healing property.
- Version comparison is timestamp-driven, so the sync path is mostly stateless beyond the remembered `last_edited_time`.
- All corrective actions are idempotent at the workflow level, because repeated sweeps should eventually produce the same converged state.

## Data Shapes

The data model is standardized around a small set of normalized document envelopes:

- `notion_id`: the Notion page or database identifier.
- `last_edited_time`: the timestamp used for version arbitration.
- `notion_properties`: the property payload returned by Notion.
- `notion_content`: the block content under a page.

At runtime, the code is focused on three major entity types:

- Users
- Projects
- Schedules

Schedules are the operational unit of sync. Users and projects mostly act as control surfaces and ownership anchors.

## End-to-End Control Flow

The runtime pipeline is built in two phases: bootstrap and steady-state reconciliation.

### 1. Bootstrap Phase

The startup path is a full-state warm-up and establishes a clean baseline.

1. Fetch all users and projects from Notion.
2. Read the child database blocks from each page to discover linked schedule databases.
3. Fetch all project schedules from every project homepage.
4. Load the results into the cache.
5. Persist the initial user/project snapshot into MongoDB.
6. Clone project schedules into user schedule databases.
7. Register every schedule page in `SyncedDocumentManager` so later sweeps can track it.

In practice, this is a cold-start snapshot sync. It establishes the baseline from which all later deltas are computed.

### 2. Steady-State Reconciliation Phase

After bootstrap, the driver enters a polling loop that keeps the system convergent.

1. Re-fetch user and project metadata from Notion.
2. Compare the fresh metadata against the cached snapshot.
3. Detect newly created or updated users/projects.
4. For newly created entities, fetch their full content and child databases, then seed the cache and MongoDB.
5. For updated projects, dispatch request handlers if the status fields ask for algorithm execution.
6. Detect newly linked schedules inside existing projects and replicate them to user schedule databases.
7. Run schedule version checks for every synced page.
8. Resolve divergence by either writing Notion changes into MongoDB or restoring MongoDB state back into Notion.

This is a classic read-compare-write reconciliation loop. The goal is not to lock state across systems. The goal is to converge state after each observation window.

## Cache Algorithm

`Cache` is treated as a lightweight indexing layer, not as a durable store.

It maintains:

- An in-memory list of user records.
- An in-memory list of project records.
- Reverse indices from `notion_id` to list position.
- Mapping tables between person IDs, notion IDs, schedule IDs, class schedule IDs, and when-to-meet IDs.

The cache algorithm has two jobs that matter operationally.

### Snapshot Replacement

`refresh_user_data()` and `refresh_project_data()` replace the full cached snapshot. A hard refresh strategy is used here.

### Delta Detection

`compare_and_update_user_data()` and `compare_and_update_project_data()` perform a shallow form of change detection:

- If a record is not present, it is treated as created.
- If the `notion_properties` payload differs, it is treated as updated.
- Regardless of whether the record is new or updated, the cached entry is overwritten with the latest object.

This behaves like a simple last-write-wins cache with a structural diff on properties, which is enough for the sync model.

## Sync-State Algorithm

`SyncedDocumentManager` is the coordination layer for document versioning.

It stores a mapping from an instance Notion page to:

- the canonical schedule Notion ID,
- the `SyncedDocument` object,
- a boolean that indicates whether the instance is a user-facing page.

It also stores a separate schedule list so the manager can answer whether a canonical schedule record is already tracked without re-querying the database.

### Link Creation

`create_instance_link()` establishes the relationship between a schedule record and one or more page instances.

There are two behaviors relied on here:

- If the instance already exists, the method is a no-op.
- If the schedule is already known, the new instance shares the same `SyncedDocument` object.

That means multiple Notion pages can fan out from the same canonical schedule record while still sharing one version state. In practice, this is pointer aliasing over a shared source of truth.

### Version Arbitration

`check_version_by_notion_id()` delegates to `SyncedDocument.check_version()`.

The version state machine is:

- `NOT_TRACKED`: the page is not part of sync.
- `UP_TO_DATE`: the incoming timestamp matches the stored timestamp.
- `AHEAD`: Notion is newer than the stored version.
- `BEHIND`: the stored version is newer than the incoming Notion page.

In distributed-systems language, this is a coarse-grained monotonic timestamp comparison. Vector clocks are not introduced, and concurrent conflicting edits are not resolved beyond timestamp precedence.

### Write Path

`save_version_by_notion_id()` writes the latest page content into MongoDB.

`get_latest_version_by_notion_id()` fetches the canonical record from MongoDB and uses it as the recovery image when Notion is behind.

## Version-Control Semantics

The schedule sync path behaves like a bidirectional anti-entropy protocol with timestamp ordering, which is the simplest design that still gives convergence.

### When Notion Is Ahead

If the incoming Notion page has a later `last_edited_time` than the stored record:

- the new page is fetched in full,
- the canonical schedule ID is normalized back onto the payload,
- user schedule fields are remapped back into project schedule shape when needed,
- the latest payload is persisted to MongoDB.

This is the forward replication path. It promotes the freshest write into the durable store.

### When the Database Is Ahead

If MongoDB has the fresher version:

- the latest database snapshot is loaded,
- the appropriate Notion page is updated,
- the page is rewritten to match the canonical record.

This is the repair path. It restores the external system to the durable canonical state.

### Convergence Property

The loop repeats until the system stops observing pages in the `AHEAD` state.

That gives the algorithm a convergence guarantee under normal conditions:

- if updates stop, the system stabilizes,
- if updates continue, the system eventually applies the freshest observed state,
- if a page is not tracked, it is safely ignored instead of being forced into the sync pipeline.

## Request Dispatch Algorithm

The request manager is designed to behave like a small workflow engine triggered by status fields in Notion.

Two project-level status fields are used as command signals:

- `甘特圖演算法`
- `會議排程演算法`

When either field transitions to `執行請求`, the driver invokes the corresponding workflow handler.

This is the lightweight control-plane pattern used here:

- Notion acts as the operator interface.
- Status fields act as declarative job requests.
- The code responds by materializing the requested computation.

## Gantt Workflow Algorithm

The Gantt pipeline is the dependency-aware scheduling pass used for project plans.

### Inputs Read

- The project page.
- All schedule pages under the project homepage.
- The parsed task graph and date constraints.

### Steps Executed

1. Mark the project status as `執行中...` to signal that the job has started.
2. Fetch all schedules under the project.
3. Parse the schedule data into a structured model.
4. Extract start and end dates.
5. Extract bottom-level tasks.
6. Recover the parent-child task hierarchy.
7. Run the Gantt generator to compute the schedule plan.
8. Serialize the result for observability.
9. Convert the computed schedule output into partial property updates.
10. Apply the updates to each schedule page in parallel.
11. Mark the project as `執行完成` if the job succeeds.
12. Write an error message to the project if the job fails.

### System Interpretation

From an SWE perspective, this is implemented as a compute-then-commit workflow:

- compute phase: derive the plan from task dependencies and temporal constraints,
- commit phase: fan out updates to the affected Notion pages,
- completion phase: update the control flag to show job status.

`asyncio.gather()` gives the update phase a parallel write fan-out, which fits because the pages are independent write targets.

## Meeting Workflow Algorithm

The meeting pipeline is the availability aggregation job used to produce a normalized time-slot table.

### Inputs Read

- The project page.
- The list of project members.
- Each member’s class schedule database.
- Each member’s personal schedule database.

### Steps Executed

1. Mark the project as `執行中...`.
2. Read the members field from the project page.
3. Map each member’s person ID back to the corresponding Notion page ID.
4. Resolve the class schedule database and personal schedule database for each user.
5. Drop users who do not have the required schedule mappings.
6. Run the meeting-time algorithm on the surviving participant set.
7. Delete all existing when-to-meet rows in the project database.
8. Reorder the database property names so the table columns match the output schema.
9. Insert every computed time slot as a new row.
10. Mark the project as `執行完成`.

### System Interpretation

This is intentionally made to behave like a batch aggregation job with a full table rebuild.

- The old result set is invalidated.
- The new result set is recomputed from the latest participant state.
- The target table is repopulated from scratch.

That is a straightforward rebuild strategy. Correctness and simplicity are favored over incremental row-level merging.

## Failure Modes and Recovery Strategy

The algorithm is intentionally conservative.

- Missing mappings are treated as skips rather than hard failures.
- Unknown pages are tagged as not tracked.
- If a workflow fails, the project receives an error message instead of silently diverging.
- If a schedule cannot be linked to a user database, the system drops that branch rather than poisoning the whole job.

That keeps the control loop resilient in the face of partial data, which matters in loosely coupled integrations.

## Distributed-Systems Summary

At a higher level, three common patterns are combined:

- Polling-based reconciliation for change detection.
- Last-write-wins version arbitration using timestamps.
- Workflow materialization from declarative state fields in Notion.

The result is a practical eventually consistent sync engine:

- Notion remains the operator-facing interface.
- MongoDB stores the canonical document state.
- The cache accelerates lookups and reduces API chatter.
- The driver continuously reconciles divergence until the observed systems converge.

In short, this is not just a sync script. It is a small distributed control system with a reconciliation loop, canonical storage, and job dispatch built on top of Notion.
- The new result set is recomputed from the latest participant state.
- The target table is repopulated from scratch.

That is a straightforward rebuild strategy. It favors correctness and simplicity over incremental row-level merging.

## Failure Modes and Recovery Strategy

The algorithm is intentionally conservative.

- Missing mappings are treated as skips rather than hard failures.
- Unknown pages are tagged as not tracked.
- If a workflow fails, the project receives an error message instead of silently diverging.
- If a schedule cannot be linked to a user database, the system drops that branch rather than poisoning the whole job.

This keeps the control loop resilient in the face of partial data, which is important in loosely coupled integrations.

## Distributed-Systems Summary

At a higher level, the algorithm combines three common patterns:

- **Polling-based reconciliation** for change detection.
- **Last-write-wins version arbitration** using timestamps.
- **Workflow materialization** from declarative state fields in Notion.

The result is a practical eventually consistent sync engine:

- Notion remains the operator-facing interface.
- MongoDB stores the canonical document state.
- The cache accelerates lookups and reduces API chatter.
- The driver continuously reconciles divergence until the observed systems converge.

In short, this is not just a sync script. It is a small distributed control system with a reconciliation loop, canonical storage, and job dispatch built on top of Notion.