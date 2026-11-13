from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "database"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "study_tracker.db"

app = FastAPI(title="Student Productivity Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


class TaskInput(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    task: str = Field(min_length=1, max_length=300)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                task TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
        """)


init_db()


def as_dict(row):
    return {
        "id": row["id"],
        "subject": row["subject"],
        "task": row["task"],
        "completed": bool(row["completed"])
    }


@app.get("/")
def home():
    return {"message": "Student Productivity Tracker is running"}


@app.get("/tasks")
def get_tasks():
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY id DESC"
        ).fetchall()

    return [as_dict(row) for row in rows]


@app.post("/tasks")
def add_task(data: TaskInput):
    subject = data.subject.strip()
    task = data.task.strip()

    if not subject or not task:
        raise HTTPException(400, "Enter subject and task")

    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks(subject, task) VALUES (?, ?)",
            (subject, task)
        )

        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return as_dict(row)


@app.put("/tasks/{task_id}")
def edit_task(task_id: int, data: TaskInput):
    subject = data.subject.strip()
    task = data.task.strip()

    if not subject or not task:
        raise HTTPException(400, "Enter subject and task")

    with connect() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET subject=?, task=? WHERE id=?",
            (subject, task, task_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Task not found")

        row = conn.execute(
            "SELECT * FROM tasks WHERE id=?",
            (task_id,)
        ).fetchone()

    return as_dict(row)


@app.put("/tasks/{task_id}/complete")
def toggle_complete(task_id: int):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id=?",
            (task_id,)
        ).fetchone()

        if row is None:
            raise HTTPException(404, "Task not found")

        new_status = 0 if row["completed"] else 1

        conn.execute(
            "UPDATE tasks SET completed=? WHERE id=?",
            (new_status, task_id)
        )

        updated = conn.execute(
            "SELECT * FROM tasks WHERE id=?",
            (task_id,)
        ).fetchone()

    return as_dict(updated)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    with connect() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id=?",
            (task_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(404, "Task not found")

    return {"message": "Task deleted successfully"}