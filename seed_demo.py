import sqlite3

# Yahan apni team ke asli naam likh sakte ho (sirf right side wale naam badlo)
TEAM = {
    "admin": "Shrashti Jaiswal",
    "member1": "Member One",
    "member2": "Member Two",
    "member3": "Member Three",
}

conn = sqlite3.connect("database.db")
cur = conn.cursor()

# Purana project data hatao (users nahi hatenge)
for table in ["action_items", "tasks", "stories", "sprints", "projects"]:
    cur.execute("DELETE FROM " + table)
cur.execute(
    "DELETE FROM sqlite_sequence WHERE name IN "
    "('action_items', 'tasks', 'stories', 'sprints', 'projects')"
)

# Team members
for username, full_name in TEAM.items():
    password = "admin123" if username == "admin" else "member123"
    cur.execute(
        "INSERT OR IGNORE INTO users (username, password, full_name) VALUES (?, ?, ?)",
        (username, password, full_name),
    )
    cur.execute("UPDATE users SET full_name = ? WHERE username = ?", (full_name, username))
uid = {row[0]: row[1] for row in cur.execute("SELECT username, id FROM users")}

# Project
cur.execute(
    "INSERT INTO projects (name, description, start_date, end_date, owner_id) VALUES (?, ?, ?, ?, ?)",
    (
        "Student Task & Sprint Management System",
        "A web app that helps student teams manage college projects using Agile and Scrum.",
        "2026-09-28",
        "2026-10-31",
        uid["admin"],
    ),
)
project_id = cur.lastrowid

# Sprints
sprints = [
    ("Sprint 1", "Build login, dashboard and project management", "2026-09-28", "2026-10-04", "Completed"),
    ("Sprint 2", "Build stories, sprints, tasks and Kanban board", "2026-10-05", "2026-10-11", "Active"),
    ("Sprint 3", "Add weekly action items, scrum notes and final polish", "2026-10-12", "2026-10-18", "Planned"),
]
sprint_ids = []
for name, goal, start, end, status in sprints:
    cur.execute(
        "INSERT INTO sprints (project_id, name, goal, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, name, goal, start, end, status),
    )
    sprint_ids.append(cur.lastrowid)

# User stories (last number = konse sprint mein hai: 0 = Sprint 1, 1 = Sprint 2, 2 = Sprint 3, None = Product Backlog)
stories = [
    ("User Login", "As a student, I want to log in with my username and password so that my project data stays private.", "High", 3, 0),
    ("Dashboard", "As a team member, I want a dashboard with a project summary so that I can see progress at a glance.", "High", 5, 0),
    ("Manage Projects", "As a student, I want to create and manage projects so that I can organize my college work.", "High", 5, 0),
    ("Manage User Stories", "As a product owner, I want to write user stories with priority and points so that the team knows what to build first.", "High", 5, 1),
    ("Sprint Planning", "As a scrum master, I want to create sprints and add stories to them so that the team can plan its work.", "High", 8, 1),
    ("Task Management", "As a team member, I want to create and assign tasks so that everyone knows their responsibility.", "Medium", 5, 1),
    ("Kanban Board", "As a team member, I want to see tasks on a board so that I can track progress easily.", "High", 8, 1),
    ("Weekly Action Items", "As a team lead, I want to record weekly action items so that follow-ups are not forgotten.", "Medium", 3, 2),
    ("Scrum Meeting Notes", "As a scrum master, I want to record review and retrospective notes so that we can improve every sprint.", "Medium", 5, None),
    ("Project Report", "As a teacher, I want to see a project report so that I can evaluate the team's work.", "Low", 5, None),
]
story_ids = []
for title, description, priority, points, sprint_index in stories:
    sprint_id = sprint_ids[sprint_index] if sprint_index is not None else None
    cur.execute(
        "INSERT INTO stories (project_id, sprint_id, title, description, priority, story_points) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, sprint_id, title, description, priority, points),
    )
    story_ids.append(cur.lastrowid)

# Tasks (pehla number = story number: 1 = User Login, 2 = Dashboard, ...)
tasks = [
    (1, "Design login page", "member1", "Medium", "DONE"),
    (1, "Write login code", "admin", "High", "DONE"),
    (2, "Create dashboard cards", "member2", "Medium", "DONE"),
    (3, "Build project create, edit, delete", "member3", "High", "DONE"),
    (4, "Create story form", "member1", "High", "DONE"),
    (4, "Add priority and story points", "member1", "Medium", "DONE"),
    (5, "Build sprint form", "member2", "High", "TESTING"),
    (5, "Create sprint backlog page", "admin", "High", "IN PROGRESS"),
    (6, "Create task form", "member3", "Medium", "DONE"),
    (6, "Assign tasks to members", "member3", "Medium", "TESTING"),
    (7, "Design Kanban columns", "member2", "High", "IN PROGRESS"),
    (7, "Save task status in database", "admin", "High", "TO DO"),
    (7, "Add progress bar", "member1", "Low", "TO DO"),
    (8, "Design action items page", "member2", "Medium", "TO DO"),
]
for story_no, title, username, priority, status in tasks:
    cur.execute(
        "INSERT INTO tasks (story_id, title, assigned_to, priority, status) VALUES (?, ?, ?, ?, ?)",
        (story_ids[story_no - 1], title, uid[username], priority, status),
    )

# Weekly action items
action_items = [
    (1, "Finalize project idea and user stories", "admin", "Done"),
    (1, "Create database tables", "member1", "Done"),
    (1, "Create login and dashboard", "member2", "Done"),
    (2, "Build project and story modules", "member3", "Done"),
    (2, "Build sprint planning and sprint backlog", "member2", "Done"),
    (2, "Create task module and Kanban board", "member1", "In Progress"),
    (3, "Write unit tests and fix bugs", "member3", "In Progress"),
    (3, "Prepare report and presentation", "admin", "Pending"),
]
for week, description, username, status in action_items:
    cur.execute(
        "INSERT INTO action_items (project_id, week_number, description, assigned_to, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, week, description, uid[username], status),
    )

conn.commit()
conn.close()
print("Demo data ready: 1 project, 3 sprints, 10 stories, 14 tasks, 8 action items.")