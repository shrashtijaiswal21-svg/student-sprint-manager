# Student Task & Sprint Management System

![Run tests](https://github.com/shrashtijaiswal21-svg/student-sprint-manager/actions/workflows/tests.yml/badge.svg)

A small web application that helps student project teams manage their college project work using **Agile (Scrum + XP)**.

Built with **Python Flask, SQLite, HTML, CSS and Bootstrap**.

## Features

- Login and logout
- Dashboard with project summary, progress bar and upcoming deadline warnings
- Project management (create, view, edit, delete)
- User stories (Product Backlog) with priority and story points
- Sprint management with sprint goal, dates and **Sprint Backlog**
- Task management with assignee, priority and status
- **Kanban board** (TO DO, IN PROGRESS, TESTING, DONE) with status saved in the database
- Weekly action items grouped by week
- Scrum meetings: Daily Scrum, Sprint Review and Sprint Retrospective notes

## How to run

```bash
git clone https://github.com/shrashtijaiswal21-svg/student-sprint-manager.git
cd student-sprint-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python3 init_db.py          # creates database.db with the tables
python3 seed_demo.py        # adds demo project, sprints, stories, tasks, action items
python3 seed_meetings.py    # adds demo Scrum meetings

python3 app.py
```

Open http://127.0.0.1:5000 in your browser.

Demo login: `admin` / `admin123`

Note: on macOS, port 5000 can be used by AirPlay Receiver. If the page shows a 403 error, turn off AirPlay Receiver in System Settings or change the port in `app.py`.

## Run the tests

```bash
python3 -m unittest discover -v
```

The tests also run automatically on every push using GitHub Actions (see the badge above).

## Agile practices used

| Practice | Where in the project |
|---|---|
| Product Backlog | User Stories page |
| Sprint Planning and Sprint Backlog | Sprints page, Backlog button |
| User Stories, Story Points, Priority | Story form and list |
| Kanban Board | Kanban page |
| Weekly Action Items | Action Items page |
| Daily Scrum, Sprint Review, Sprint Retrospective | Meetings page |
| Test Driven Development (TDD) | `test_progress.py`, `test_deadlines.py` (tests written before the code) |
| Refactoring | `calculate_progress()` extracted from the Kanban view |
| Continuous Integration | GitHub Actions workflow in `.github/workflows/tests.yml` |
| Small Releases | Git tags `v1.0`, `v1.1` |

## Project structure

```
student-sprint-manager/
├── app.py               # Flask routes and logic
├── schema.sql           # database tables
├── init_db.py           # creates the database
├── seed_demo.py         # demo data
├── seed_meetings.py     # demo Scrum meetings
├── templates/           # HTML pages
├── static/style.css     # custom styles
├── test_*.py            # unit tests
└── .github/workflows/   # CI workflow
```

## Future scope

- Password hashing and role-based access (Product Owner, Scrum Master, Team Member)
- Email or in-app notifications for upcoming deadlines and overdue tasks
- Drag and drop Kanban board
- Burndown chart and sprint velocity report
- Task due dates and automatic workload-based task suggestions