# Classflow — A6 Timetable Studio

An end-to-end college timetable and resource scheduling application for the A6 project. It creates a weekly timetable while preventing faculty, student-batch, classroom, and subject-per-day conflicts.

## Project team

- Himanshu Kumar Singh
- Dipanshu
- Aman Raj

Suggested contribution split (update this to reflect the work your team actually completes):

- **Himanshu Kumar Singh:** graph model, constraint checks, and backtracking scheduler.
- **Dipanshu:** SQLite schema, backend routes, and data/resource management.
- **Aman Raj:** frontend views, timetable editing, CSV export, and project presentation.

All team members should review the complete workflow and be ready to explain the scheduler and their own contribution during evaluation.

## Features

- Manage faculty, subjects, student batches, classrooms, and weekly time slots.
- Generate a timetable with a graph-coloring and backtracking scheduler.
- Compare the backtracking scheduler with a greedy scheduler.
- Edit a class's time and classroom; the server rejects conflicting changes.
- View the timetable by batch in a weekly grid or list.
- Export the generated timetable as CSV.
- Store project data in a local SQLite database.
- Start with sample campus data, then edit it for your own institute.

## Technology

- **Frontend:** HTML, CSS, and JavaScript
- **Backend:** Python 3.9+ standard library HTTP server
- **Database:** SQLite (`sqlite3`, included with Python)
- **External packages:** None

## Run on Windows

1. Install Python 3.9 or newer.
2. Open PowerShell in this project folder.
3. Start the app:

   ```powershell
   py app.py
   ```

4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser.
5. Select a batch and choose **Generate timetable**. The first run creates the sample data and `data/timetable.db` automatically.

For a **Phase 1 backend-only demonstration**, run `py app.py --phase1`. This creates the sample SQLite data if needed, generates the timetable, and prints the graph and search summary in PowerShell without starting the web interface.

Stop the local server with **Ctrl+C** in its PowerShell window. The database remains in `data/timetable.db` between runs. To restart with fresh sample records, stop the server and remove that database file; it will be recreated next time the app starts.

## Phase 1 demonstration: backend, database, and DSA

Before demonstrating the interface, explain these implementation points from `app.py`:

1. SQLite stores faculty, batches, rooms, slots, subjects, and generated class meetings. Foreign keys connect subjects to faculty and batches, and schedule entries to subjects, rooms, and slots.
2. Each weekly class meeting is a graph vertex. Two vertices share a conflict edge when they use the same faculty member or student batch.
3. The backtracking scheduler assigns a time slot and suitable classroom to each meeting. It checks graph neighbors, overlapping time ranges, room availability, room capacity, and the rule that one subject cannot meet twice on the same day.
4. A **priority queue (min-heap)** implements the **Minimum Remaining Values (MRV)** heuristic: at each recursion step, it selects the unassigned class with the fewest currently available choices. When a choice leaves a class with no valid option, it backtracks.
5. The greedy option visits the most connected classes first and accepts the first available time and room. It is useful for comparison but can fail where backtracking finds a solution.

### Complexity to explain

Let `V` be weekly class meetings, `E` be conflict edges, `S` be available time slots, and `R` be eligible rooms.

- The current conflict graph builder compares meeting pairs: **O(V²)** time and **O(V + E)** graph storage.
- Backtracking has **O((S × R)^V)** worst-case search time and **O(V + E)** assignment/graph space, plus a recursion stack up to **O(V)**. Rebuilding the MRV priority queue adds at most **O(V log V)** ordering work per search node. MRV and early conflict checks improve common cases but do not change the worst case.
- The greedy scheduler does not revisit an assigned class. Its candidate checks are bounded by the meetings and available slot-room pairs (up to **O(V² × S × R)** with the current implementation); its assignment/graph storage is **O(V + E)**.
- A manual schedule edit checks the classes already assigned to the selected slot, then checks same-subject/day duplication. This is **O(V)** in the current implementation.

Useful live demonstration: create or edit one class, try assigning another class from the same batch or faculty to the same slot, and show that the app rejects the conflicting assignment.

## Phase 2 demonstration: full application

1. Open **Resources** and review faculty, subjects, batches, classrooms, and time slots.
2. Generate the timetable from the **Timetable** page.
3. Filter by batch, then click a class to move it to a different time or room.
4. Show the conflict message by attempting an invalid change.
5. Open **Algorithms**, run the backtracking or greedy scheduler, and explain the displayed vertex, edge, search-step, and runtime values.
6. Export the finished timetable with **Export CSV**.

## Database and source layout

```text
A6_Timetable_System/
├── app.py                  # HTTP API, SQLite setup, DSA scheduler
├── README.md               # Project and evaluation guide
├── update_github.ps1       # One-step GitHub upload/update helper
├── Upload to GitHub.bat    # Double-click shortcut for Windows
├── static/
│   ├── index.html           # App views
│   ├── styles.css           # Responsive interface styling
│   └── app.js               # Frontend behavior and API calls
└── data/                    # Created on first run; local SQLite database
```

The `data/` directory is excluded from Git so the repository contains source code while each team member can create their own local database.

## GitHub submission

### First upload

1. Sign in to GitHub and create a new, **empty** repository for the team. For example, name it `A6-Timetable-System`. Leave the GitHub options to create a README, `.gitignore`, or license unchecked; those files are already in this project.
2. Double-click **Upload to GitHub.bat** in this project folder. If Windows asks, allow it to open PowerShell. You can also run the command below from PowerShell in this folder:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\update_github.ps1
   ```

4. The helper asks for the repository URL once. Paste the HTTPS URL from GitHub, such as `https://github.com/your-team/A6-Timetable-System.git`. If Git needs your commit name or email, enter the name and email associated with your GitHub account. Complete GitHub sign-in if prompted.

### Future updates

After changing project files, double-click **Upload to GitHub.bat** again. Enter a short summary when asked; press Enter to use the default summary. The helper stages the project, saves a commit, and uploads it to GitHub. It skips the local SQLite database automatically.

If you prefer a visual app, GitHub Desktop can also add this project folder as an existing repository, publish it once, then use **Commit to main** and **Push origin** for later updates.

Make regular updates as each team member contributes. Share the same repository with all three team members so they can review the source and commit their contributions.

