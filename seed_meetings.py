import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

# Table banao (agar pehle se nahi hai). Purana data safe rahega.
cur.execute(
    """CREATE TABLE IF NOT EXISTS scrum_meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sprint_id INTEGER NOT NULL,
        meeting_type TEXT NOT NULL,
        meeting_date TEXT NOT NULL,
        notes TEXT NOT NULL,
        follow_up TEXT,
        FOREIGN KEY (sprint_id) REFERENCES sprints (id)
    )"""
)

# Sirf meetings ka purana data hatao
cur.execute("DELETE FROM scrum_meetings")
cur.execute("DELETE FROM sqlite_sequence WHERE name = 'scrum_meetings'")

sprint_ids = {row[0]: row[1] for row in cur.execute("SELECT name, id FROM sprints")}
if "Sprint 1" not in sprint_ids or "Sprint 2" not in sprint_ids:
    print("Pehle 'python3 seed_demo.py' chalao, phir ye script chalao.")
    conn.commit()
    conn.close()
    raise SystemExit

meetings = [
    (
        "Sprint 1", "Daily Scrum", "2026-09-29",
        "Yesterday: finalized the project idea and database tables. Today: start the login page and dashboard.",
        "Blocker: not sure how sessions work in Flask. Asked a senior for help.",
    ),
    (
        "Sprint 1", "Daily Scrum", "2026-10-01",
        "Login page is done. Working on dashboard cards and the project module.",
        "No blockers.",
    ),
    (
        "Sprint 1", "Sprint Review", "2026-10-04",
        "Demonstrated login, dashboard and project create, edit and delete to the guide. All 3 stories were completed (13 story points).",
        "Feedback: make the dashboard more attractive and show progress information.",
    ),
    (
        "Sprint 1", "Sprint Retrospective", "2026-10-04",
        "Went well: pair programming on the login code saved time, and tasks were split clearly.",
        "Improve: write tests earlier and update the board every day.",
    ),
    (
        "Sprint 2", "Daily Scrum", "2026-10-06",
        "Yesterday: story form completed. Today: sprint form and task form.",
        "Blocker: Bootstrap CDN not loading on the college WiFi. Using a mobile hotspot.",
    ),
    (
        "Sprint 2", "Daily Scrum", "2026-10-08",
        "Kanban status update works and is saved in the database. Next: progress bar and tests.",
        "No blockers.",
    ),
]
for sprint_name, meeting_type, meeting_date, notes, follow_up in meetings:
    cur.execute(
        "INSERT INTO scrum_meetings (sprint_id, meeting_type, meeting_date, notes, follow_up) "
        "VALUES (?, ?, ?, ?, ?)",
        (sprint_ids[sprint_name], meeting_type, meeting_date, notes, follow_up),
    )

conn.commit()
conn.close()
print("Scrum meetings ready: " + str(len(meetings)) + " meetings.")