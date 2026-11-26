"""A6 College Timetable and Resource Scheduling System (standard-library only)."""

from __future__ import annotations

import csv
import heapq
import io
import argparse
import json
import mimetypes
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "timetable.db"
HOST = "127.0.0.1"
PORT = 8000

TABLES = {
    "faculty": ("faculty", ("name", "department", "email")),
    "subjects": ("subjects", ("code", "name", "faculty_id", "batch_id", "sessions_per_week")),
    "batches": ("batches", ("name", "student_count", "program")),
    "rooms": ("rooms", ("name", "capacity", "building")),
    "slots": ("slots", ("day", "start_time", "end_time")),
}


def connect_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_db():
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                student_count INTEGER NOT NULL DEFAULT 30 CHECK(student_count > 0),
                program TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 40 CHECK(capacity > 0),
                building TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                faculty_id INTEGER NOT NULL REFERENCES faculty(id) ON DELETE RESTRICT,
                batch_id INTEGER NOT NULL REFERENCES batches(id) ON DELETE RESTRICT,
                sessions_per_week INTEGER NOT NULL DEFAULT 1 CHECK(sessions_per_week BETWEEN 1 AND 10)
            );
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                occurrence_no INTEGER NOT NULL,
                slot_id INTEGER NOT NULL REFERENCES slots(id) ON DELETE RESTRICT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
                UNIQUE(subject_id, occurrence_no)
            );
            """
        )
        if db.execute("SELECT COUNT(*) FROM faculty").fetchone()[0] == 0:
            seed_demo_data(db)


def seed_demo_data(db):
    faculty = [
        ("Dr. Aditi Sharma", "Computer Science", "aditi@example.edu"),
        ("Prof. Ravi Mehta", "Computer Science", "ravi@example.edu"),
        ("Ms. Neha Verma", "Mathematics", "neha@example.edu"),
        ("Mr. Arjun Rao", "Electronics", "arjun@example.edu"),
        ("Dr. Sana Khan", "Computer Science", "sana@example.edu"),
        ("Ms. Kavya Iyer", "Communication", "kavya@example.edu"),
    ]
    db.executemany("INSERT INTO faculty(name, department, email) VALUES(?,?,?)", faculty)
    batches = [("A6-A", 36, "B.Tech CSE"), ("A6-B", 32, "B.Tech CSE"), ("A6-C", 28, "B.Tech CSE")]
    db.executemany("INSERT INTO batches(name, student_count, program) VALUES(?,?,?)", batches)
    rooms = [("Lab 1", 40, "Block A"), ("Room 204", 45, "Block B"), ("Room 105", 35, "Block A"), ("Room 301", 60, "Block C")]
    db.executemany("INSERT INTO rooms(name, capacity, building) VALUES(?,?,?)", rooms)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    times = [("09:00", "10:00"), ("10:15", "11:15"), ("11:30", "12:30"), ("13:30", "14:30"), ("14:45", "15:45"), ("16:00", "17:00")]
    db.executemany("INSERT INTO slots(day, start_time, end_time) VALUES(?,?,?)", [(d, s, e) for d in days for s, e in times])
    subject_rows = [
        ("CS601", "Data Structures", 1, 1, 2), ("CS602", "Database Systems", 2, 1, 2), ("MA601", "Discrete Mathematics", 3, 1, 2),
        ("CS611", "Algorithms", 1, 2, 2), ("EC601", "Computer Networks", 4, 2, 2), ("CS612", "Operating Systems", 5, 2, 2),
        ("CS621", "Web Technologies", 2, 3, 2), ("CS622", "Software Engineering", 5, 3, 2), ("EN601", "Technical Communication", 6, 3, 2),
    ]
    db.executemany("INSERT INTO subjects(code, name, faculty_id, batch_id, sessions_per_week) VALUES(?,?,?,?,?)", subject_rows)


def rows_as_dicts(db, query, params=()):
    return [dict(row) for row in db.execute(query, params).fetchall()]


def get_snapshot(db):
    faculty = rows_as_dicts(db, "SELECT * FROM faculty ORDER BY name")
    batches = rows_as_dicts(db, "SELECT * FROM batches ORDER BY name")
    rooms = rows_as_dicts(db, "SELECT * FROM rooms ORDER BY name")
    slots = rows_as_dicts(db, "SELECT * FROM slots ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 ELSE 6 END, start_time")
    subjects = rows_as_dicts(db, """SELECT s.*, f.name AS faculty_name, b.name AS batch_name, b.student_count
                                    FROM subjects s JOIN faculty f ON f.id=s.faculty_id JOIN batches b ON b.id=s.batch_id
                                    ORDER BY b.name, s.code""")
    schedule = rows_as_dicts(db, """SELECT sc.id, sc.subject_id, sc.occurrence_no, sc.slot_id, sc.room_id,
                                      s.code, s.name AS subject_name, s.faculty_id, f.name AS faculty_name,
                                      s.batch_id, b.name AS batch_name, r.name AS room_name, r.capacity,
                                      sl.day, sl.start_time, sl.end_time
                               FROM schedule sc JOIN subjects s ON s.id=sc.subject_id
                               JOIN faculty f ON f.id=s.faculty_id JOIN batches b ON b.id=s.batch_id
                               JOIN rooms r ON r.id=sc.room_id JOIN slots sl ON sl.id=sc.slot_id
                               ORDER BY b.name, sl.day, sl.start_time""")
    return {"faculty": faculty, "batches": batches, "rooms": rooms, "slots": slots, "subjects": subjects, "schedule": schedule}


def conflict_reason(db, subject_id, slot_id, room_id, skip_schedule_id=None):
    subject = db.execute("""SELECT s.*, b.student_count FROM subjects s JOIN batches b ON b.id=s.batch_id WHERE s.id=?""", (subject_id,)).fetchone()
    slot = db.execute("SELECT * FROM slots WHERE id=?", (slot_id,)).fetchone()
    room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not subject or not slot or not room:
        return "Choose a valid subject, time slot, and room."
    batch_name = db.execute("SELECT name FROM batches WHERE id=?", (subject["batch_id"],)).fetchone()[0]
    if room["capacity"] < subject["student_count"]:
        return f"{room['name']} seats {room['capacity']}, but {batch_name} has {subject['student_count']} students."
    query = """SELECT sc.id, s.faculty_id, s.batch_id, s.id AS subject_id, r.name AS room_name,
                      sc.room_id, sl.day, sl.start_time, sl.end_time
               FROM schedule sc JOIN subjects s ON s.id=sc.subject_id JOIN rooms r ON r.id=sc.room_id
               JOIN slots sl ON sl.id=sc.slot_id WHERE sl.day=?"""
    params = [slot["day"]]
    if skip_schedule_id is not None:
        query += " AND sc.id<>?"
        params.append(skip_schedule_id)
    for existing in db.execute(query, params):
        if not intervals_overlap(slot["start_time"], slot["end_time"], existing["start_time"], existing["end_time"]):
            continue
        if existing["faculty_id"] == subject["faculty_id"]:
            return "That faculty member already has a class in this time slot."
        if existing["batch_id"] == subject["batch_id"]:
            return "That student batch already has a class in this time slot."
        if existing["room_id"] == room_id:
            return "That classroom is already booked in this time slot."
    query_day = """SELECT s.id FROM schedule sc JOIN subjects s ON s.id=sc.subject_id JOIN slots sl ON sl.id=sc.slot_id
                   WHERE sl.day=? AND sc.subject_id=?"""
    params_day = [slot["day"], subject_id]
    if skip_schedule_id is not None:
        query_day += " AND sc.id<>?"
        params_day.append(skip_schedule_id)
    if db.execute(query_day, params_day).fetchone():
        return "This subject already has a session on that day."
    return None


def intervals_overlap(start_a, end_a, start_b, end_b):
    """Return whether two half-open HH:MM periods overlap."""
    def minutes(value):
        hours, mins = map(int, value.split(":"))
        return hours * 60 + mins
    return minutes(start_a) < minutes(end_b) and minutes(start_b) < minutes(end_a)


def validate_existing_schedule(db):
    """Keep resource edits from introducing conflicts into a generated schedule."""
    entries = db.execute("SELECT id, subject_id, slot_id, room_id FROM schedule ORDER BY id").fetchall()
    for entry in entries:
        reason = conflict_reason(db, entry["subject_id"], entry["slot_id"], entry["room_id"], entry["id"])
        if reason:
            raise ValueError(f"This change would make the current timetable invalid: {reason}")


def sessions_and_domains(db):
    subjects = db.execute("""SELECT s.*, b.student_count, b.name AS batch_name, f.name AS faculty_name
                            FROM subjects s JOIN batches b ON b.id=s.batch_id JOIN faculty f ON f.id=s.faculty_id
                            ORDER BY s.id""").fetchall()
    slots = db.execute("SELECT * FROM slots ORDER BY day, start_time").fetchall()
    slots_by_id = {slot["id"]: slot for slot in slots}
    rooms = db.execute("SELECT * FROM rooms ORDER BY capacity, name").fetchall()
    sessions = []
    for subject in subjects:
        for occurrence in range(1, subject["sessions_per_week"] + 1):
            sessions.append({"subject_id": subject["id"], "occurrence_no": occurrence, "faculty_id": subject["faculty_id"], "batch_id": subject["batch_id"], "student_count": subject["student_count"], "subject_code": subject["code"]})
    return sessions, slots, rooms


def generate_schedule(db, method="backtracking"):
    if method not in ("backtracking", "greedy"):
        raise ValueError("Choose the backtracking or greedy scheduler.")
    sessions, slots, rooms = sessions_and_domains(db)
    slots_by_id = {slot["id"]: slot for slot in slots}
    if not sessions:
        raise ValueError("Add at least one subject before generating a timetable.")
    if not slots or not rooms:
        raise ValueError("Add at least one time slot and classroom first.")
    graph = {i: set() for i in range(len(sessions))}
    for i, first in enumerate(sessions):
        for j in range(i + 1, len(sessions)):
            second = sessions[j]
            if first["faculty_id"] == second["faculty_id"] or first["batch_id"] == second["batch_id"]:
                graph[i].add(j)
                graph[j].add(i)
    order = sorted(graph, key=lambda i: (-len(graph[i]), sessions[i]["subject_code"], sessions[i]["occurrence_no"]))
    assigned = {}
    nodes = 0

    def candidates(index):
        session = sessions[index]
        valid_rooms = [room for room in rooms if room["capacity"] >= session["student_count"]]
        available = []
        for slot in slots:
            conflict = False
            for neighbor in graph[index]:
                other_slot = slots_by_id.get(assigned[neighbor]["slot_id"]) if neighbor in assigned else None
                if other_slot and other_slot["day"] == slot["day"] and intervals_overlap(
                    slot["start_time"], slot["end_time"], other_slot["start_time"], other_slot["end_time"]
                ):
                    conflict = True
                    break
            if conflict:
                continue
            # A subject is scheduled at most once per day.
            if any(sessions[other]["subject_id"] == session["subject_id"] and
                   slots_by_id[assigned[other]["slot_id"]]["day"] == slot["day"]
                   for other in assigned):
                continue
            used_rooms = {assigned[other]["room_id"] for other in range(len(sessions))
                          if other in assigned and slots_by_id[assigned[other]["slot_id"]]["day"] == slot["day"]
                          and intervals_overlap(slot["start_time"], slot["end_time"],
                                                slots_by_id[assigned[other]["slot_id"]]["start_time"],
                                                slots_by_id[assigned[other]["slot_id"]]["end_time"])}
            for room in valid_rooms:
                if room["id"] not in used_rooms:
                    available.append((slot["id"], room["id"]))
        return available

    if method == "greedy":
        for index in order:
            domain = candidates(index)
            if not domain:
                raise ValueError("No complete timetable fits the current rooms, slots, faculty, and batches. Add resources or reduce weekly sessions.")
            assigned[index] = {"slot_id": domain[0][0], "room_id": domain[0][1]}
            nodes += 1
    else:
        def solve(remaining):
            nonlocal nodes
            if not remaining:
                return True
            # Minimum Remaining Values: schedule the most constrained class first.
            choices = []
            for index in remaining:
                domain = candidates(index)
                if not domain:
                    return False
                # Min-heap is the priority queue for the MRV constraint heuristic.
                heapq.heappush(choices, (len(domain), -len(graph[index]), index, domain))
            _, _, best_index, best_domain = heapq.heappop(choices)
            best_domain.sort(key=lambda pair: (pair[0], pair[1]))
            next_remaining = [item for item in remaining if item != best_index]
            for slot_id, room_id in best_domain:
                nodes += 1
                if nodes > 250000:
                    return False
                assigned[best_index] = {"slot_id": slot_id, "room_id": room_id}
                if solve(next_remaining):
                    return True
                del assigned[best_index]
            return False
        if not solve(list(range(len(sessions)))):
            raise ValueError("Could not find a complete timetable with the current resources. Add time slots or rooms, or reduce weekly sessions, then try again.")

    db.execute("DELETE FROM schedule")
    db.executemany("INSERT INTO schedule(subject_id, occurrence_no, slot_id, room_id) VALUES(?,?,?,?)", [
        (session["subject_id"], session["occurrence_no"], assigned[i]["slot_id"], assigned[i]["room_id"])
        for i, session in enumerate(sessions)
    ])
    return {"scheduled_classes": len(sessions), "algorithm": method, "search_steps": nodes, "vertices": len(sessions), "conflict_edges": sum(len(v) for v in graph.values()) // 2}


def clean_entity(table, payload):
    cols = TABLES[table][1]
    values = {key: payload.get(key) for key in cols}
    required = {"name", "code", "faculty_id", "batch_id", "day", "start_time", "end_time"}
    for key, value in values.items():
        if key in required and (value is None or str(value).strip() == ""):
            raise ValueError(f"{key.replace('_', ' ').capitalize()} is required.")
    numeric = {"faculty_id", "batch_id", "sessions_per_week", "student_count", "capacity"}
    for key in numeric:
        if key in values and values[key] is not None:
            try:
                values[key] = int(values[key])
            except (TypeError, ValueError):
                raise ValueError(f"{key.replace('_', ' ').capitalize()} must be a whole number.")
    if values.get("sessions_per_week", 1) not in range(1, 11):
        raise ValueError("Sessions per week must be from 1 to 10.")
    for key in ("capacity", "student_count"):
        if key in values and values[key] is not None and values[key] < 1:
            raise ValueError(f"{key.replace('_', ' ').capitalize()} must be at least 1.")
    if table == "slots":
        if values["day"] not in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"):
            raise ValueError("Choose a valid day of the week.")
        try:
            start_minutes = int(values["start_time"][:2]) * 60 + int(values["start_time"][3:])
            end_minutes = int(values["end_time"][:2]) * 60 + int(values["end_time"][3:])
            if len(values["start_time"]) != 5 or len(values["end_time"]) != 5 or values["start_time"][2] != ":" or values["end_time"][2] != ":" or not (0 <= start_minutes < end_minutes <= 1440):
                raise ValueError("End time must be later than start time.")
        except (TypeError, ValueError, IndexError):
            raise ValueError("Enter a valid start and end time, with end time later than start time.")
    return values


def ensure_unique_slot(db, values, exclude_id=None):
    query = "SELECT id FROM slots WHERE day=? AND start_time=? AND end_time=?"
    params = [values["day"], values["start_time"], values["end_time"]]
    if exclude_id is not None:
        query += " AND id<>?"
        params.append(exclude_id)
    if db.execute(query, params).fetchone():
        raise ValueError("That exact time slot already exists for this day.")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "A6Timetable/1.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request is too large.")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/data":
            with connect_db() as db:
                return self.send_json(get_snapshot(db))
        if parsed.path == "/api/export.csv":
            with connect_db() as db:
                rows = get_snapshot(db)["schedule"]
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Batch", "Day", "Start", "End", "Subject code", "Subject", "Faculty", "Room", "Occurrence"])
            for row in rows:
                writer.writerow([row["batch_name"], row["day"], row["start_time"], row["end_time"], row["code"], row["subject_name"], row["faculty_name"], row["room_name"], row["occurrence_no"]])
            content = output.getvalue().encode("utf-8-sig")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="a6-college-timetable.csv"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            return self.wfile.write(content)
        if parsed.path == "/api/health":
            return self.send_json({"status": "ok"})
        path = "/index.html" if parsed.path == "/" else parsed.path
        file_path = (STATIC / path.lstrip("/")).resolve()
        if not file_path.is_relative_to(STATIC.resolve()) or not file_path.is_file():
            return self.send_json({"error": "Not found"}, 404)
        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith(("text/", "application/javascript")) else ""))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self.body_json()
            if path == "/api/generate":
                started = time.perf_counter()
                with connect_db() as db:
                    result = generate_schedule(db, body.get("method", "backtracking"))
                result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
                return self.send_json(result)
            table = path.removeprefix("/api/")
            if table not in TABLES:
                return self.send_json({"error": "Unknown resource"}, 404)
            values = clean_entity(table, body)
            columns = list(values)
            with connect_db() as db:
                if table == "slots":
                    ensure_unique_slot(db, values)
                cursor = db.execute(f"INSERT INTO {TABLES[table][0]} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [values[c] for c in columns])
                new_id = cursor.lastrowid
            return self.send_json({"id": new_id, "message": "Saved"}, 201)
        except (ValueError, json.JSONDecodeError, sqlite3.IntegrityError) as exc:
            return self.send_json({"error": str(exc) if isinstance(exc, ValueError) else "Please check the entered values and linked records."}, 400)
        except Exception as exc:
            return self.send_json({"error": "The request could not be completed.", "detail": str(exc)}, 500)

    def do_PUT(self):
        path_parts = urlparse(self.path).path.strip("/").split("/")
        if len(path_parts) != 3 or path_parts[0] != "api" or path_parts[1] not in TABLES:
            return self.send_json({"error": "Unknown resource"}, 404)
        table, entity_id = path_parts[1], path_parts[2]
        try:
            values = clean_entity(table, self.body_json())
            columns = list(values)
            with connect_db() as db:
                if table == "slots":
                    ensure_unique_slot(db, values, int(entity_id))
                cursor = db.execute(f"UPDATE {TABLES[table][0]} SET " + ",".join(f"{col}=?" for col in columns) + " WHERE id=?", [values[c] for c in columns] + [int(entity_id)])
                if not cursor.rowcount:
                    return self.send_json({"error": "Record not found"}, 404)
                validate_existing_schedule(db)
            return self.send_json({"message": "Updated"})
        except (ValueError, json.JSONDecodeError, sqlite3.IntegrityError) as exc:
            return self.send_json({"error": str(exc) if isinstance(exc, ValueError) else "Please check the entered values and linked records."}, 400)

    def do_DELETE(self):
        path_parts = urlparse(self.path).path.strip("/").split("/")
        try:
            if len(path_parts) == 3 and path_parts[:2] == ["api", "schedule"]:
                with connect_db() as db:
                    cursor = db.execute("DELETE FROM schedule WHERE id=?", (int(path_parts[2]),))
                if cursor.rowcount == 0:
                    return self.send_json({"error": "Class not found"}, 404)
                return self.send_json({"message": "Class removed"})
            if len(path_parts) != 3 or path_parts[0] != "api" or path_parts[1] not in TABLES:
                return self.send_json({"error": "Unknown resource"}, 404)
            table = path_parts[1]
            with connect_db() as db:
                cursor = db.execute(f"DELETE FROM {TABLES[table][0]} WHERE id=?", (int(path_parts[2]),))
                if not cursor.rowcount:
                    return self.send_json({"error": "Record not found"}, 404)
            return self.send_json({"message": "Deleted"})
        except (ValueError, sqlite3.IntegrityError):
            return self.send_json({"error": "This record is in use. Remove its linked subjects or timetable entries first."}, 409)

    def do_PATCH(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "schedule"]:
            return self.send_json({"error": "Unknown resource"}, 404)
        try:
            schedule_id = int(parts[2])
            body = self.body_json()
            slot_id, room_id = int(body["slot_id"]), int(body["room_id"])
            with connect_db() as db:
                row = db.execute("SELECT subject_id FROM schedule WHERE id=?", (schedule_id,)).fetchone()
                if not row:
                    return self.send_json({"error": "Class not found"}, 404)
                reason = conflict_reason(db, row["subject_id"], slot_id, room_id, schedule_id)
                if reason:
                    return self.send_json({"error": reason}, 409)
                db.execute("UPDATE schedule SET slot_id=?, room_id=? WHERE id=?", (slot_id, room_id, schedule_id))
            return self.send_json({"message": "Class updated"})
        except (KeyError, ValueError, sqlite3.IntegrityError):
            return self.send_json({"error": "Choose a valid time slot and room."}, 400)


def phase1_demo():
    initialize_db()
    with connect_db() as db:
        result = generate_schedule(db, "backtracking")
        snapshot = get_snapshot(db)
    print("A6 Phase 1 — backend and DSA demonstration")
    print(f"Database: {DB_PATH}")
    print(f"Class meetings: {result['scheduled_classes']} | conflict graph: {result['vertices']} vertices, {result['conflict_edges']} edges")
    print(f"Backtracking search steps: {result['search_steps']}")
    print("The schedule was written to SQLite. Example assigned classes:")
    for row in snapshot["schedule"][:8]:
        print(f"  {row['batch_name']} · {row['day']} {row['start_time']}-{row['end_time']} · {row['code']} · {row['room_name']}")
    print("Complexity: graph construction O(V^2); backtracking worst case O((S × R)^V), with a priority queue for the MRV heuristic.")


def main():
    parser = argparse.ArgumentParser(description="A6 College Timetable and Resource Scheduling System")
    parser.add_argument("--phase1", action="store_true", help="run a backend-only database and DSA demonstration")
    args = parser.parse_args()
    if args.phase1:
        phase1_demo()
        return
    initialize_db()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"A6 Timetable System is ready at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

