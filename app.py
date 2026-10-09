from functools import wraps
import sqlite3
from datetime import date

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, abort
)

app = Flask(__name__)
app.secret_key = "sprint-manager-secret-key"
app.config["DATABASE"] = "database.db"

PRIORITIES = ["High", "Medium", "Low"]
STORY_POINTS = [1, 2, 3, 5, 8, 13]
SPRINT_STATUSES = ["Planned", "Active", "Completed"]
TASK_STATUSES = ["TO DO", "IN PROGRESS", "TESTING", "DONE"]
ACTION_STATUSES = ["Pending", "In Progress", "Done"]
STATUS_COLORS = {
    "TO DO": "secondary",
    "IN PROGRESS": "primary",
    "TESTING": "info",
    "DONE": "success",
}


# ---------- Database connection ----------
def get_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


# ---------- Login check ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------- Login / Logout ----------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        db.close()

        if user:
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------- Dashboard ----------
# ---------- Dashboard ----------
def days_until(date_text, today=None):
    """Aaj se is date (YYYY-MM-DD) tak kitne din bache hain. Date nikal gayi ho to negative."""
    if today is None:
        today = date.today()
    return (date.fromisoformat(date_text) - today).days


def deadline_label(days_left):
    """Deadline ke liye (message, color) return karta hai."""
    if days_left < 0:
        late = abs(days_left)
        return ("Overdue by " + str(late) + (" day" if late == 1 else " days"), "danger")
    if days_left == 0:
        return ("Ends today", "danger")
    unit = " day" if days_left == 1 else " days"
    color = "warning" if days_left <= 3 else "success"
    return ("Ends in " + str(days_left) + unit, color)


def get_deadlines():
    """Dashboard ke liye: chal rahe sprints aur projects ki deadlines."""
    db = get_db()
    sprint_rows = db.execute(
        """SELECT sprints.id, sprints.name, sprints.end_date,
                  projects.name AS project_name,
                  (SELECT COUNT(*) FROM tasks
                   JOIN stories ON tasks.story_id = stories.id
                   WHERE stories.sprint_id = sprints.id AND tasks.status != 'DONE') AS pending
           FROM sprints JOIN projects ON sprints.project_id = projects.id
           WHERE sprints.status != 'Completed'"""
    ).fetchall()
    project_rows = db.execute("SELECT id, name, end_date FROM projects").fetchall()
    db.close()

    items = []
    for row in sprint_rows:
        if row["end_date"]:
            left = days_until(row["end_date"])
            label, color = deadline_label(left)
            items.append(
                {
                    "kind": "Sprint",
                    "name": row["name"] + " (" + row["project_name"] + ")",
                    "end_date": row["end_date"],
                    "label": label,
                    "color": color,
                    "days_left": left,
                    "pending": row["pending"],
                }
            )
    for row in project_rows:
        if row["end_date"]:
            left = days_until(row["end_date"])
            label, color = deadline_label(left)
            items.append(
                {
                    "kind": "Project",
                    "name": row["name"],
                    "end_date": row["end_date"],
                    "label": label,
                    "color": color,
                    "days_left": left,
                    "pending": None,
                }
            )
    items.sort(key=lambda item: item["days_left"])
    return items


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    total_projects = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    pending_tasks = db.execute(
        "SELECT COUNT(*) FROM tasks WHERE status != 'DONE'"
    ).fetchone()[0]
    completed_tasks = db.execute(
        "SELECT COUNT(*) FROM tasks WHERE status = 'DONE'"
    ).fetchone()[0]
    active_sprint = db.execute(
        "SELECT name FROM sprints WHERE status = 'Active' LIMIT 1"
    ).fetchone()
    db.close()

    return render_template(
        "dashboard.html",
        total_projects=total_projects,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        active_sprint=active_sprint["name"] if active_sprint else "None",
        deadlines=get_deadlines(),
    )

# ---------- Projects ----------
def get_project_or_404(project_id):
    db = get_db()
    project = db.execute(
        """SELECT projects.*, users.full_name AS owner_name
           FROM projects JOIN users ON projects.owner_id = users.id
           WHERE projects.id = ?""",
        (project_id,),
    ).fetchone()
    db.close()
    if project is None:
        abort(404)
    return project


@app.route("/projects")
@login_required
def projects():
    db = get_db()
    all_projects = db.execute(
        """SELECT projects.*, users.full_name AS owner_name
           FROM projects JOIN users ON projects.owner_id = users.id
           ORDER BY projects.id DESC"""
    ).fetchall()
    db.close()
    return render_template("projects.html", projects=all_projects)


@app.route("/projects/add", methods=["GET", "POST"])
@login_required
def add_project():
    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form["description"].strip()
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        if not name:
            flash("Project name is required.", "danger")
        elif start_date and end_date and end_date < start_date:
            flash("End date cannot be before start date.", "danger")
        else:
            db = get_db()
            db.execute(
                """INSERT INTO projects (name, description, start_date, end_date, owner_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, description, start_date, end_date, session["user_id"]),
            )
            db.commit()
            db.close()
            flash("Project created successfully.", "success")
            return redirect(url_for("projects"))

    return render_template("project_form.html", project=None)


@app.route("/projects/<int:project_id>")
@login_required
def view_project(project_id):
    project = get_project_or_404(project_id)
    return render_template("project_detail.html", project=project)


@app.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = get_project_or_404(project_id)

    if request.method == "POST":
        name = request.form["name"].strip()
        description = request.form["description"].strip()
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        if not name:
            flash("Project name is required.", "danger")
        elif start_date and end_date and end_date < start_date:
            flash("End date cannot be before start date.", "danger")
        else:
            db = get_db()
            db.execute(
                """UPDATE projects
                   SET name = ?, description = ?, start_date = ?, end_date = ?
                   WHERE id = ?""",
                (name, description, start_date, end_date, project_id),
            )
            db.commit()
            db.close()
            flash("Project updated successfully.", "success")
            return redirect(url_for("projects"))

    return render_template("project_form.html", project=project)


@app.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    get_project_or_404(project_id)
    db = get_db()
    db.execute("DELETE FROM action_items WHERE project_id = ?", (project_id,))
    db.execute(
        "DELETE FROM tasks WHERE story_id IN (SELECT id FROM stories WHERE project_id = ?)",
        (project_id,),
    )
    db.execute("DELETE FROM stories WHERE project_id = ?", (project_id,))
    db.execute(
        "DELETE FROM scrum_meetings WHERE sprint_id IN (SELECT id FROM sprints WHERE project_id = ?)",
        (project_id,),
    )
    db.execute("DELETE FROM sprints WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    db.close()
    flash("Project deleted.", "info")
    return redirect(url_for("projects"))


# ---------- User Stories (Product Backlog) ----------
def get_story_or_404(story_id):
    db = get_db()
    story = db.execute(
        """SELECT stories.*, projects.name AS project_name
           FROM stories JOIN projects ON stories.project_id = projects.id
           WHERE stories.id = ?""",
        (story_id,),
    ).fetchone()
    db.close()
    if story is None:
        abort(404)
    return story


def validate_story_form(form):
    """Form check karta hai. Error message return karta hai, sab sahi ho to None."""
    if not form["title"].strip():
        return "Story title is required."
    if not form["description"].strip():
        return "Description is required. Use: As a [user], I want [functionality], so that [benefit]."
    if form["priority"] not in PRIORITIES:
        return "Please choose a valid priority."
    if not form["story_points"].isdigit() or int(form["story_points"]) not in STORY_POINTS:
        return "Please choose valid story points."
    return None


@app.route("/stories")
@login_required
def stories():
    db = get_db()
    all_stories = db.execute(
        """SELECT stories.*, projects.name AS project_name
           FROM stories JOIN projects ON stories.project_id = projects.id
           ORDER BY CASE stories.priority
                        WHEN 'High' THEN 1
                        WHEN 'Medium' THEN 2
                        ELSE 3
                    END,
                    stories.id"""
    ).fetchall()
    db.close()
    return render_template("stories.html", stories=all_stories)


@app.route("/stories/add", methods=["GET", "POST"])
@login_required
def add_story():
    db = get_db()
    all_projects = db.execute("SELECT id, name FROM projects ORDER BY name").fetchall()
    db.close()

    if not all_projects:
        flash("Please create a project first.", "warning")
        return redirect(url_for("projects"))

    if request.method == "POST":
        error = validate_story_form(request.form)
        project_ids = [str(p["id"]) for p in all_projects]
        if error is None and request.form.get("project_id") not in project_ids:
            error = "Please choose a project."

        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute(
                """INSERT INTO stories (project_id, title, description, priority, story_points)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    int(request.form["project_id"]),
                    request.form["title"].strip(),
                    request.form["description"].strip(),
                    request.form["priority"],
                    int(request.form["story_points"]),
                ),
            )
            db.commit()
            db.close()
            flash("User story created successfully.", "success")
            return redirect(url_for("stories"))

    return render_template(
        "story_form.html",
        story=None,
        projects=all_projects,
        priorities=PRIORITIES,
        story_points=STORY_POINTS,
    )


@app.route("/stories/<int:story_id>/edit", methods=["GET", "POST"])
@login_required
def edit_story(story_id):
    story = get_story_or_404(story_id)

    if request.method == "POST":
        error = validate_story_form(request.form)
        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute(
                """UPDATE stories
                   SET title = ?, description = ?, priority = ?, story_points = ?
                   WHERE id = ?""",
                (
                    request.form["title"].strip(),
                    request.form["description"].strip(),
                    request.form["priority"],
                    int(request.form["story_points"]),
                    story_id,
                ),
            )
            db.commit()
            db.close()
            flash("User story updated successfully.", "success")
            return redirect(url_for("stories"))

    return render_template(
        "story_form.html",
        story=story,
        projects=[],
        priorities=PRIORITIES,
        story_points=STORY_POINTS,
    )


@app.route("/stories/<int:story_id>/delete", methods=["POST"])
@login_required
def delete_story(story_id):
    get_story_or_404(story_id)
    db = get_db()
    db.execute("DELETE FROM tasks WHERE story_id = ?", (story_id,))
    db.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    db.commit()
    db.close()
    flash("User story deleted.", "info")
    return redirect(url_for("stories"))


# ---------- Sprints ----------
def get_sprint_or_404(sprint_id):
    db = get_db()
    sprint = db.execute(
        """SELECT sprints.*, projects.name AS project_name
           FROM sprints JOIN projects ON sprints.project_id = projects.id
           WHERE sprints.id = ?""",
        (sprint_id,),
    ).fetchone()
    db.close()
    if sprint is None:
        abort(404)
    return sprint


def validate_sprint_form(form, project_id, sprint_id=None):
    """Error message return karta hai, sab sahi ho to None."""
    if not form["name"].strip():
        return "Sprint name is required."
    if not form["goal"].strip():
        return "Sprint goal is required."
    start_date = form["start_date"]
    end_date = form["end_date"]
    if not start_date or not end_date:
        return "Start date and end date are required."
    if end_date < start_date:
        return "End date cannot be before start date."
    if form["status"] not in SPRINT_STATUSES:
        return "Please choose a valid status."
    if form["status"] == "Active":
        # Ek project mein ek hi Active sprint ho sakta hai
        db = get_db()
        other_active = db.execute(
            "SELECT id FROM sprints WHERE project_id = ? AND status = 'Active' AND id != ?",
            (project_id, sprint_id or 0),
        ).fetchone()
        db.close()
        if other_active:
            return "This project already has an Active sprint. Complete it first."
    return None


@app.route("/sprints")
@login_required
def sprints():
    db = get_db()
    all_sprints = db.execute(
        """SELECT sprints.*, projects.name AS project_name,
                  (SELECT COUNT(*) FROM stories WHERE stories.sprint_id = sprints.id) AS story_count,
                  (SELECT COALESCE(SUM(story_points), 0) FROM stories
                   WHERE stories.sprint_id = sprints.id) AS total_points
           FROM sprints JOIN projects ON sprints.project_id = projects.id
           ORDER BY sprints.id DESC"""
    ).fetchall()
    db.close()
    return render_template("sprints.html", sprints=all_sprints)


@app.route("/sprints/add", methods=["GET", "POST"])
@login_required
def add_sprint():
    db = get_db()
    all_projects = db.execute("SELECT id, name FROM projects ORDER BY name").fetchall()
    db.close()

    if not all_projects:
        flash("Please create a project first.", "warning")
        return redirect(url_for("projects"))

    if request.method == "POST":
        project_ids = [str(p["id"]) for p in all_projects]
        project_id = request.form.get("project_id")

        if project_id not in project_ids:
            flash("Please choose a project.", "danger")
        else:
            error = validate_sprint_form(request.form, int(project_id))
            if error:
                flash(error, "danger")
            else:
                db = get_db()
                db.execute(
                    """INSERT INTO sprints (project_id, name, goal, start_date, end_date, status)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        int(project_id),
                        request.form["name"].strip(),
                        request.form["goal"].strip(),
                        request.form["start_date"],
                        request.form["end_date"],
                        request.form["status"],
                    ),
                )
                db.commit()
                db.close()
                flash("Sprint created successfully.", "success")
                return redirect(url_for("sprints"))

    return render_template(
        "sprint_form.html",
        sprint=None,
        projects=all_projects,
        statuses=SPRINT_STATUSES,
    )


@app.route("/sprints/<int:sprint_id>")
@login_required
def view_sprint(sprint_id):
    sprint = get_sprint_or_404(sprint_id)
    db = get_db()
    # Sprint Backlog: is sprint ki stories
    sprint_stories = db.execute(
        """SELECT * FROM stories WHERE sprint_id = ?
           ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, id""",
        (sprint_id,),
    ).fetchall()
    # Product Backlog mein bachi hui stories (isi project ki, kisi sprint mein nahi)
    available_stories = db.execute(
        """SELECT * FROM stories WHERE project_id = ? AND sprint_id IS NULL
           ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, id""",
        (sprint["project_id"],),
    ).fetchall()
    db.close()
    total_points = sum(s["story_points"] for s in sprint_stories)
    return render_template(
        "sprint_detail.html",
        sprint=sprint,
        sprint_stories=sprint_stories,
        available_stories=available_stories,
        total_points=total_points,
    )


@app.route("/sprints/<int:sprint_id>/edit", methods=["GET", "POST"])
@login_required
def edit_sprint(sprint_id):
    sprint = get_sprint_or_404(sprint_id)

    if request.method == "POST":
        error = validate_sprint_form(request.form, sprint["project_id"], sprint_id)
        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute(
                """UPDATE sprints
                   SET name = ?, goal = ?, start_date = ?, end_date = ?, status = ?
                   WHERE id = ?""",
                (
                    request.form["name"].strip(),
                    request.form["goal"].strip(),
                    request.form["start_date"],
                    request.form["end_date"],
                    request.form["status"],
                    sprint_id,
                ),
            )
            db.commit()
            db.close()
            flash("Sprint updated successfully.", "success")
            return redirect(url_for("sprints"))

    return render_template(
        "sprint_form.html",
        sprint=sprint,
        projects=[],
        statuses=SPRINT_STATUSES,
    )


@app.route("/sprints/<int:sprint_id>/delete", methods=["POST"])
@login_required
def delete_sprint(sprint_id):
    get_sprint_or_404(sprint_id)
    db = get_db()
    # Stories delete nahi hongi, bas wapas Product Backlog mein chali jayengi
    db.execute("UPDATE stories SET sprint_id = NULL WHERE sprint_id = ?", (sprint_id,))
    db.execute("DELETE FROM scrum_meetings WHERE sprint_id = ?", (sprint_id,))
    db.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))
    db.commit()
    db.close()
    flash("Sprint deleted. Its stories are back in the Product Backlog.", "info")
    return redirect(url_for("sprints"))


@app.route("/sprints/<int:sprint_id>/add-story", methods=["POST"])
@login_required
def add_story_to_sprint(sprint_id):
    sprint = get_sprint_or_404(sprint_id)
    story_id = request.form.get("story_id", "")

    db = get_db()
    story = None
    if story_id.isdigit():
        story = db.execute(
            "SELECT id FROM stories WHERE id = ? AND project_id = ? AND sprint_id IS NULL",
            (int(story_id), sprint["project_id"]),
        ).fetchone()

    if story is None:
        db.close()
        flash("Please choose a valid story.", "danger")
    else:
        db.execute("UPDATE stories SET sprint_id = ? WHERE id = ?", (sprint_id, story["id"]))
        db.commit()
        db.close()
        flash("Story added to sprint backlog.", "success")
    return redirect(url_for("view_sprint", sprint_id=sprint_id))


@app.route("/sprints/<int:sprint_id>/remove-story/<int:story_id>", methods=["POST"])
@login_required
def remove_story_from_sprint(sprint_id, story_id):
    get_sprint_or_404(sprint_id)
    db = get_db()
    db.execute(
        "UPDATE stories SET sprint_id = NULL WHERE id = ? AND sprint_id = ?",
        (story_id, sprint_id),
    )
    db.commit()
    db.close()
    flash("Story removed from sprint backlog.", "info")
    return redirect(url_for("view_sprint", sprint_id=sprint_id))


# ---------- Tasks ----------
def get_task_or_404(task_id):
    db = get_db()
    task = db.execute(
        """SELECT tasks.*, stories.title AS story_title, stories.project_id AS project_id
           FROM tasks JOIN stories ON tasks.story_id = stories.id
           WHERE tasks.id = ?""",
        (task_id,),
    ).fetchone()
    db.close()
    if task is None:
        abort(404)
    return task


def get_all_users():
    db = get_db()
    users = db.execute("SELECT id, full_name FROM users ORDER BY full_name").fetchall()
    db.close()
    return users


def get_all_stories():
    db = get_db()
    all_stories = db.execute(
        """SELECT stories.id, stories.title, projects.name AS project_name
           FROM stories JOIN projects ON stories.project_id = projects.id
           ORDER BY stories.id"""
    ).fetchall()
    db.close()
    return all_stories


def validate_task_form(form, user_ids):
    """Error message return karta hai, sab sahi ho to None."""
    if not form["title"].strip():
        return "Task title is required."
    if form["priority"] not in PRIORITIES:
        return "Please choose a valid priority."
    if form["status"] not in TASK_STATUSES:
        return "Please choose a valid status."
    if form["assigned_to"] and form["assigned_to"] not in user_ids:
        return "Please choose a valid team member."
    return None


@app.route("/tasks")
@login_required
def tasks():
    db = get_db()
    all_tasks = db.execute(
        """SELECT tasks.*, stories.title AS story_title, users.full_name AS assignee_name
           FROM tasks
           JOIN stories ON tasks.story_id = stories.id
           LEFT JOIN users ON tasks.assigned_to = users.id
           ORDER BY tasks.id DESC"""
    ).fetchall()
    db.close()
    return render_template("tasks.html", tasks=all_tasks)


@app.route("/tasks/add", methods=["GET", "POST"])
@login_required
def add_task():
    all_stories = get_all_stories()
    users = get_all_users()

    if not all_stories:
        flash("Please create a user story first.", "warning")
        return redirect(url_for("stories"))

    if request.method == "POST":
        user_ids = [str(u["id"]) for u in users]
        story_ids = [str(s["id"]) for s in all_stories]
        error = validate_task_form(request.form, user_ids)
        if error is None and request.form.get("story_id") not in story_ids:
            error = "Please choose a user story."

        if error:
            flash(error, "danger")
        else:
            assigned_to = request.form["assigned_to"]
            db = get_db()
            db.execute(
                """INSERT INTO tasks (story_id, title, assigned_to, priority, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    int(request.form["story_id"]),
                    request.form["title"].strip(),
                    int(assigned_to) if assigned_to else None,
                    request.form["priority"],
                    request.form["status"],
                ),
            )
            db.commit()
            db.close()
            flash("Task created successfully.", "success")
            return redirect(url_for("tasks"))

    return render_template(
        "task_form.html",
        task=None,
        stories=all_stories,
        users=users,
        priorities=PRIORITIES,
        statuses=TASK_STATUSES,
    )


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = get_task_or_404(task_id)
    users = get_all_users()

    if request.method == "POST":
        user_ids = [str(u["id"]) for u in users]
        error = validate_task_form(request.form, user_ids)

        if error:
            flash(error, "danger")
        else:
            assigned_to = request.form["assigned_to"]
            db = get_db()
            db.execute(
                """UPDATE tasks
                   SET title = ?, assigned_to = ?, priority = ?, status = ?
                   WHERE id = ?""",
                (
                    request.form["title"].strip(),
                    int(assigned_to) if assigned_to else None,
                    request.form["priority"],
                    request.form["status"],
                    task_id,
                ),
            )
            db.commit()
            db.close()
            flash("Task updated successfully.", "success")
            return redirect(url_for("tasks"))

    return render_template(
        "task_form.html",
        task=task,
        stories=[],
        users=users,
        priorities=PRIORITIES,
        statuses=TASK_STATUSES,
    )


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    get_task_or_404(task_id)
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    db.close()
    flash("Task deleted.", "info")
    return redirect(url_for("tasks"))


# ---------- Kanban Board ----------
def calculate_progress(done, total):
    """Kitne percent kaam DONE hai (0 se 100 tak)."""
    if total == 0:
        return 0
    return int(done * 100 / total)
@app.route("/kanban")
@login_required
def kanban():
    db = get_db()
    all_sprints = db.execute(
        """SELECT sprints.id, sprints.name, sprints.status, projects.name AS project_name
           FROM sprints JOIN projects ON sprints.project_id = projects.id
           ORDER BY sprints.id DESC"""
    ).fetchall()

    # Konsa sprint dikhana hai: URL se, ya Active sprint, ya sab tasks
    sprint_param = request.args.get("sprint_id")
    if sprint_param is None:
        active = db.execute(
            "SELECT id FROM sprints WHERE status = 'Active' ORDER BY id LIMIT 1"
        ).fetchone()
        selected = active["id"] if active else "all"
    elif sprint_param.isdigit():
        selected = int(sprint_param)
    else:
        selected = "all"

    query = """SELECT tasks.*, stories.title AS story_title,
                      users.full_name AS assignee_name
               FROM tasks
               JOIN stories ON tasks.story_id = stories.id
               LEFT JOIN users ON tasks.assigned_to = users.id"""
    if selected == "all":
        board_tasks = db.execute(query + " ORDER BY tasks.id").fetchall()
    else:
        board_tasks = db.execute(
            query + " WHERE stories.sprint_id = ? ORDER BY tasks.id", (selected,)
        ).fetchall()
    db.close()

    # Har status ka alag column banao
    columns = []
    for status in TASK_STATUSES:
        columns.append(
            {
                "status": status,
                "color": STATUS_COLORS[status],
                "tasks": [t for t in board_tasks if t["status"] == status],
            }
        )

    total = len(board_tasks)
    done = len([t for t in board_tasks if t["status"] == "DONE"])
    percent = calculate_progress(done, total)

    return render_template(
        "kanban.html",
        columns=columns,
        sprints=all_sprints,
        selected=selected,
        statuses=TASK_STATUSES,
        total=total,
        done=done,
        percent=percent,
    )


@app.route("/tasks/<int:task_id>/status", methods=["POST"])
@login_required
def update_task_status(task_id):
    get_task_or_404(task_id)
    new_status = request.form.get("status", "")
    sprint_id = request.form.get("sprint_id", "all")

    if new_status not in TASK_STATUSES:
        flash("Invalid status.", "danger")
    else:
        db = get_db()
        db.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        db.commit()
        db.close()
        flash("Task moved to " + new_status + ".", "success")

    return redirect(url_for("kanban", sprint_id=sprint_id))


# ---------- Weekly Action Items ----------
def get_action_item_or_404(item_id):
    db = get_db()
    item = db.execute(
        """SELECT action_items.*, projects.name AS project_name
           FROM action_items JOIN projects ON action_items.project_id = projects.id
           WHERE action_items.id = ?""",
        (item_id,),
    ).fetchone()
    db.close()
    if item is None:
        abort(404)
    return item


def validate_action_item_form(form, user_ids):
    """Error message return karta hai, sab sahi ho to None."""
    week = form.get("week_number", "")
    if not week.isdigit() or int(week) < 1 or int(week) > 52:
        return "Week number must be between 1 and 52."
    if not form["description"].strip():
        return "Description is required."
    if form["status"] not in ACTION_STATUSES:
        return "Please choose a valid status."
    if form["assigned_to"] and form["assigned_to"] not in user_ids:
        return "Please choose a valid team member."
    return None


@app.route("/action-items")
@login_required
def action_items():
    db = get_db()
    all_items = db.execute(
        """SELECT action_items.*, projects.name AS project_name,
                  users.full_name AS assignee_name
           FROM action_items
           JOIN projects ON action_items.project_id = projects.id
           LEFT JOIN users ON action_items.assigned_to = users.id
           ORDER BY action_items.week_number, action_items.id"""
    ).fetchall()
    db.close()

    # Items ko week ke hisaab se group karo
    weeks = {}
    for item in all_items:
        weeks.setdefault(item["week_number"], []).append(item)

    return render_template("action_items.html", weeks=weeks)


@app.route("/action-items/add", methods=["GET", "POST"])
@login_required
def add_action_item():
    db = get_db()
    all_projects = db.execute("SELECT id, name FROM projects ORDER BY name").fetchall()
    db.close()
    users = get_all_users()

    if not all_projects:
        flash("Please create a project first.", "warning")
        return redirect(url_for("projects"))

    if request.method == "POST":
        user_ids = [str(u["id"]) for u in users]
        project_ids = [str(p["id"]) for p in all_projects]
        error = validate_action_item_form(request.form, user_ids)
        if error is None and request.form.get("project_id") not in project_ids:
            error = "Please choose a project."

        if error:
            flash(error, "danger")
        else:
            assigned_to = request.form["assigned_to"]
            db = get_db()
            db.execute(
                """INSERT INTO action_items
                   (project_id, week_number, description, assigned_to, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    int(request.form["project_id"]),
                    int(request.form["week_number"]),
                    request.form["description"].strip(),
                    int(assigned_to) if assigned_to else None,
                    request.form["status"],
                ),
            )
            db.commit()
            db.close()
            flash("Action item created successfully.", "success")
            return redirect(url_for("action_items"))

    return render_template(
        "action_item_form.html",
        item=None,
        projects=all_projects,
        users=users,
        statuses=ACTION_STATUSES,
    )


@app.route("/action-items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_action_item(item_id):
    item = get_action_item_or_404(item_id)
    users = get_all_users()

    if request.method == "POST":
        user_ids = [str(u["id"]) for u in users]
        error = validate_action_item_form(request.form, user_ids)

        if error:
            flash(error, "danger")
        else:
            assigned_to = request.form["assigned_to"]
            db = get_db()
            db.execute(
                """UPDATE action_items
                   SET week_number = ?, description = ?, assigned_to = ?, status = ?
                   WHERE id = ?""",
                (
                    int(request.form["week_number"]),
                    request.form["description"].strip(),
                    int(assigned_to) if assigned_to else None,
                    request.form["status"],
                    item_id,
                ),
            )
            db.commit()
            db.close()
            flash("Action item updated successfully.", "success")
            return redirect(url_for("action_items"))

    return render_template(
        "action_item_form.html",
        item=item,
        projects=[],
        users=users,
        statuses=ACTION_STATUSES,
    )


@app.route("/action-items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_action_item(item_id):
    get_action_item_or_404(item_id)
    db = get_db()
    db.execute("DELETE FROM action_items WHERE id = ?", (item_id,))
    db.commit()
    db.close()
    flash("Action item deleted.", "info")
    return redirect(url_for("action_items"))

# ---------- Scrum Meetings ----------
MEETING_TYPES = ["Daily Scrum", "Sprint Review", "Sprint Retrospective"]
MEETING_COLORS = {
    "Daily Scrum": "primary",
    "Sprint Review": "success",
    "Sprint Retrospective": "warning",
}


def get_meeting_or_404(meeting_id):
    db = get_db()
    meeting = db.execute(
        """SELECT scrum_meetings.*, sprints.name AS sprint_name
           FROM scrum_meetings JOIN sprints ON scrum_meetings.sprint_id = sprints.id
           WHERE scrum_meetings.id = ?""",
        (meeting_id,),
    ).fetchone()
    db.close()
    if meeting is None:
        abort(404)
    return meeting


def get_sprints_for_select():
    db = get_db()
    rows = db.execute(
        """SELECT sprints.id, sprints.name, sprints.status, projects.name AS project_name
           FROM sprints JOIN projects ON sprints.project_id = projects.id
           ORDER BY sprints.id DESC"""
    ).fetchall()
    db.close()
    return rows


def validate_meeting_form(form):
    """Error message return karta hai, sab sahi ho to None."""
    if form["meeting_type"] not in MEETING_TYPES:
        return "Please choose a valid meeting type."
    if not form["meeting_date"]:
        return "Meeting date is required."
    if not form["notes"].strip():
        return "Discussion notes are required."
    return None


@app.route("/scrum-meetings")
@login_required
def scrum_meetings():
    selected_type = request.args.get("type", "all")
    db = get_db()
    query = """SELECT scrum_meetings.*, sprints.name AS sprint_name
               FROM scrum_meetings JOIN sprints ON scrum_meetings.sprint_id = sprints.id"""
    order = " ORDER BY scrum_meetings.meeting_date DESC, scrum_meetings.id DESC"

    if selected_type in MEETING_TYPES:
        meetings = db.execute(
            query + " WHERE scrum_meetings.meeting_type = ?" + order, (selected_type,)
        ).fetchall()
    else:
        selected_type = "all"
        meetings = db.execute(query + order).fetchall()

    counts = {}
    for meeting_type in MEETING_TYPES:
        counts[meeting_type] = db.execute(
            "SELECT COUNT(*) FROM scrum_meetings WHERE meeting_type = ?", (meeting_type,)
        ).fetchone()[0]
    db.close()

    return render_template(
        "scrum_meetings.html",
        meetings=meetings,
        selected_type=selected_type,
        meeting_types=MEETING_TYPES,
        colors=MEETING_COLORS,
        counts=counts,
    )


@app.route("/scrum-meetings/add", methods=["GET", "POST"])
@login_required
def add_meeting():
    sprints_list = get_sprints_for_select()
    if not sprints_list:
        flash("Please create a sprint first.", "warning")
        return redirect(url_for("sprints"))

    if request.method == "POST":
        sprint_ids = [str(s["id"]) for s in sprints_list]
        error = validate_meeting_form(request.form)
        if error is None and request.form.get("sprint_id") not in sprint_ids:
            error = "Please choose a sprint."

        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute(
                """INSERT INTO scrum_meetings (sprint_id, meeting_type, meeting_date, notes, follow_up)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    int(request.form["sprint_id"]),
                    request.form["meeting_type"],
                    request.form["meeting_date"],
                    request.form["notes"].strip(),
                    request.form["follow_up"].strip(),
                ),
            )
            db.commit()
            db.close()
            flash("Scrum meeting saved successfully.", "success")
            return redirect(url_for("scrum_meetings"))

    return render_template(
        "meeting_form.html",
        meeting=None,
        sprints=sprints_list,
        meeting_types=MEETING_TYPES,
        default_type=request.args.get("type", ""),
    )


@app.route("/scrum-meetings/<int:meeting_id>/edit", methods=["GET", "POST"])
@login_required
def edit_meeting(meeting_id):
    meeting = get_meeting_or_404(meeting_id)

    if request.method == "POST":
        error = validate_meeting_form(request.form)
        if error:
            flash(error, "danger")
        else:
            db = get_db()
            db.execute(
                """UPDATE scrum_meetings
                   SET meeting_type = ?, meeting_date = ?, notes = ?, follow_up = ?
                   WHERE id = ?""",
                (
                    request.form["meeting_type"],
                    request.form["meeting_date"],
                    request.form["notes"].strip(),
                    request.form["follow_up"].strip(),
                    meeting_id,
                ),
            )
            db.commit()
            db.close()
            flash("Scrum meeting updated successfully.", "success")
            return redirect(url_for("scrum_meetings"))

    return render_template(
        "meeting_form.html",
        meeting=meeting,
        sprints=[],
        meeting_types=MEETING_TYPES,
        default_type="",
    )


@app.route("/scrum-meetings/<int:meeting_id>/delete", methods=["POST"])
@login_required
def delete_meeting(meeting_id):
    get_meeting_or_404(meeting_id)
    db = get_db()
    db.execute("DELETE FROM scrum_meetings WHERE id = ?", (meeting_id,))
    db.commit()
    db.close()
    flash("Scrum meeting deleted.", "info")
    return redirect(url_for("scrum_meetings"))
if __name__ == "__main__":
    app.run(debug=True)