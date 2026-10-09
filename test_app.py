import os
import sqlite3
import tempfile
import unittest

from app import app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SprintManagerTests(unittest.TestCase):
    def setUp(self):
        # Har test se pehle: temporary database banao
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        app.config["DATABASE"] = self.db_path
        app.config["TESTING"] = True

        conn = sqlite3.connect(self.db_path)
        with open(os.path.join(BASE_DIR, "schema.sql")) as f:
            conn.executescript(f.read())
        conn.execute(
            "INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)",
            ("admin", "admin123", "Admin User"),
        )
        conn.commit()
        conn.close()

        self.client = app.test_client()

    def tearDown(self):
        # Har test ke baad: temporary database hata do
        os.close(self.db_fd)
        os.remove(self.db_path)
        app.config["DATABASE"] = "database.db"

    # ---------- Helper functions ----------
    def query(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def login(self):
        return self.client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )

    def create_project(self):
        self.client.post(
            "/projects/add",
            data={
                "name": "Test Project",
                "description": "A project for testing",
                "start_date": "2026-10-01",
                "end_date": "2026-10-30",
            },
            follow_redirects=True,
        )
        return self.query("SELECT id FROM projects")[0][0]

    def create_story(self, project_id):
        self.client.post(
            "/stories/add",
            data={
                "project_id": str(project_id),
                "title": "Create Task",
                "description": "As a student, I want to create a task so that I can track my work.",
                "priority": "High",
                "story_points": "3",
            },
            follow_redirects=True,
        )
        return self.query("SELECT id FROM stories")[0][0]

    def sprint_data(self, project_id, name, status):
        return {
            "project_id": str(project_id),
            "name": name,
            "goal": "Develop basic application",
            "start_date": "2026-10-07",
            "end_date": "2026-10-14",
            "status": status,
        }

    def create_task(self, story_id):
        self.client.post(
            "/tasks/add",
            data={
                "story_id": str(story_id),
                "title": "Design login page",
                "assigned_to": "1",
                "priority": "Medium",
                "status": "TO DO",
            },
            follow_redirects=True,
        )
        return self.query("SELECT id FROM tasks")[0][0]

    # ---------- Login tests ----------
    def test_login_page_loads(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Username", response.data)

    def test_login_success(self):
        response = self.login()
        self.assertIn(b"Welcome, Admin User", response.data)

    def test_login_wrong_password(self):
        response = self.client.post(
            "/login",
            data={"username": "admin", "password": "wrong"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid username or password.", response.data)

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    # ---------- Project, Story, Sprint tests ----------
    def test_create_project(self):
        self.login()
        response = self.client.post(
            "/projects/add",
            data={
                "name": "Test Project",
                "description": "Testing",
                "start_date": "2026-10-01",
                "end_date": "2026-10-30",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Project created successfully.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM projects")), 1)

    def test_create_story(self):
        self.login()
        project_id = self.create_project()
        response = self.client.post(
            "/stories/add",
            data={
                "project_id": str(project_id),
                "title": "User Login",
                "description": "As a student, I want to log in so that I can access my projects.",
                "priority": "High",
                "story_points": "3",
            },
            follow_redirects=True,
        )
        self.assertIn(b"User story created successfully.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM stories")), 1)

    def test_create_sprint(self):
        self.login()
        project_id = self.create_project()
        response = self.client.post(
            "/sprints/add",
            data=self.sprint_data(project_id, "Sprint 1", "Active"),
            follow_redirects=True,
        )
        self.assertIn(b"Sprint created successfully.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM sprints")), 1)

    def test_only_one_active_sprint(self):
        self.login()
        project_id = self.create_project()
        self.client.post(
            "/sprints/add",
            data=self.sprint_data(project_id, "Sprint 1", "Active"),
            follow_redirects=True,
        )
        response = self.client.post(
            "/sprints/add",
            data=self.sprint_data(project_id, "Sprint 2", "Active"),
            follow_redirects=True,
        )
        self.assertIn(b"already has an Active sprint", response.data)
        self.assertEqual(len(self.query("SELECT * FROM sprints")), 1)

    # ---------- Task and Kanban tests ----------
    def test_create_task(self):
        self.login()
        project_id = self.create_project()
        story_id = self.create_story(project_id)
        response = self.client.post(
            "/tasks/add",
            data={
                "story_id": str(story_id),
                "title": "Design login page",
                "assigned_to": "1",
                "priority": "Medium",
                "status": "TO DO",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Task created successfully.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM tasks")), 1)

    def test_task_status_update(self):
        self.login()
        project_id = self.create_project()
        story_id = self.create_story(project_id)
        task_id = self.create_task(story_id)

        response = self.client.post(
            "/tasks/" + str(task_id) + "/status",
            data={"status": "DONE", "sprint_id": "all"},
            follow_redirects=True,
        )
        self.assertIn(b"Task moved to DONE.", response.data)
        saved_status = self.query("SELECT status FROM tasks WHERE id = ?", (task_id,))[0][0]
        self.assertEqual(saved_status, "DONE")

    def test_kanban_page_loads(self):
        self.login()
        response = self.client.get("/kanban?sprint_id=all")
        self.assertEqual(response.status_code, 200)
        for column in [b"TO DO", b"IN PROGRESS", b"TESTING", b"DONE"]:
            self.assertIn(column, response.data)

    # ---------- Weekly action item tests ----------
    def test_create_action_item(self):
        self.login()
        project_id = self.create_project()
        response = self.client.post(
            "/action-items/add",
            data={
                "project_id": str(project_id),
                "week_number": "1",
                "description": "Create database",
                "assigned_to": "1",
                "status": "Done",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Action item created successfully.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM action_items")), 1)

    def test_action_item_invalid_week(self):
        self.login()
        project_id = self.create_project()
        response = self.client.post(
            "/action-items/add",
            data={
                "project_id": str(project_id),
                "week_number": "0",
                "description": "Create database",
                "assigned_to": "1",
                "status": "Done",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Week number must be between 1 and 52.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM action_items")), 0)


if __name__ == "__main__":
    unittest.main()