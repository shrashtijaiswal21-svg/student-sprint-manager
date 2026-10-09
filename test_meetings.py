import os
import sqlite3
import tempfile
import unittest

from app import app

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class MeetingTests(unittest.TestCase):
    def setUp(self):
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
        os.close(self.db_fd)
        os.remove(self.db_path)
        app.config["DATABASE"] = "database.db"

    def query(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows

    def login_and_create_sprint(self):
        self.client.post("/login", data={"username": "admin", "password": "admin123"})
        self.client.post(
            "/projects/add",
            data={
                "name": "Test Project",
                "description": "Testing",
                "start_date": "2026-10-01",
                "end_date": "2026-10-30",
            },
        )
        self.client.post(
            "/sprints/add",
            data={
                "project_id": "1",
                "name": "Sprint 1",
                "goal": "Test goal",
                "start_date": "2026-10-07",
                "end_date": "2026-10-14",
                "status": "Planned",
            },
        )
        return self.query("SELECT id FROM sprints")[0][0]

    def meeting_data(self, sprint_id, meeting_type, notes):
        return {
            "sprint_id": str(sprint_id),
            "meeting_type": meeting_type,
            "meeting_date": "2026-10-08",
            "notes": notes,
            "follow_up": "No blockers",
        }

    def test_meetings_page_requires_login(self):
        response = self.client.get("/scrum-meetings")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_add_meeting(self):
        sprint_id = self.login_and_create_sprint()
        response = self.client.post(
            "/scrum-meetings/add",
            data=self.meeting_data(sprint_id, "Daily Scrum", "Worked on login"),
            follow_redirects=True,
        )
        self.assertIn(b"Scrum meeting saved successfully.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM scrum_meetings")), 1)

    def test_invalid_meeting_type_is_rejected(self):
        sprint_id = self.login_and_create_sprint()
        response = self.client.post(
            "/scrum-meetings/add",
            data=self.meeting_data(sprint_id, "Coffee Break", "Chatting"),
            follow_redirects=True,
        )
        self.assertIn(b"Please choose a valid meeting type.", response.data)
        self.assertEqual(len(self.query("SELECT * FROM scrum_meetings")), 0)

    def test_filter_by_meeting_type(self):
        sprint_id = self.login_and_create_sprint()
        self.client.post(
            "/scrum-meetings/add",
            data=self.meeting_data(sprint_id, "Daily Scrum", "UNIQUE-DAILY-NOTE"),
        )
        self.client.post(
            "/scrum-meetings/add",
            data=self.meeting_data(sprint_id, "Sprint Review", "UNIQUE-REVIEW-NOTE"),
        )
        response = self.client.get("/scrum-meetings", query_string={"type": "Sprint Review"})
        self.assertIn(b"UNIQUE-REVIEW-NOTE", response.data)
        self.assertNotIn(b"UNIQUE-DAILY-NOTE", response.data)


if __name__ == "__main__":
    unittest.main()