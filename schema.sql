DROP TABLE IF EXISTS scrum_meetings;
DROP TABLE IF EXISTS action_items;
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS stories;
DROP TABLE IF EXISTS sprints;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    full_name TEXT NOT NULL
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    start_date TEXT,
    end_date TEXT,
    owner_id INTEGER NOT NULL,
    FOREIGN KEY (owner_id) REFERENCES users (id)
);

CREATE TABLE sprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    goal TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'Planned',
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

CREATE TABLE stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    sprint_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium',
    story_points INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (project_id) REFERENCES projects (id),
    FOREIGN KEY (sprint_id) REFERENCES sprints (id)
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    assigned_to INTEGER,
    priority TEXT NOT NULL DEFAULT 'Medium',
    status TEXT NOT NULL DEFAULT 'TO DO',
    FOREIGN KEY (story_id) REFERENCES stories (id),
    FOREIGN KEY (assigned_to) REFERENCES users (id)
);

CREATE TABLE action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    week_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    assigned_to INTEGER,
    status TEXT NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (project_id) REFERENCES projects (id),
    FOREIGN KEY (assigned_to) REFERENCES users (id)
);

CREATE TABLE scrum_meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_id INTEGER NOT NULL,
    meeting_type TEXT NOT NULL,
    meeting_date TEXT NOT NULL,
    notes TEXT NOT NULL,
    follow_up TEXT,
    FOREIGN KEY (sprint_id) REFERENCES sprints (id)
);