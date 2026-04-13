import sqlite3
import contextlib

DB_PATH = "ems.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextlib.contextmanager
def transaction():
    """Context manager — wraps all operations in a single atomic transaction."""
    conn = get_connection()
    try:
        conn.execute("BEGIN")
        yield conn
        conn.commit()
        print("[TXN] ✅ Transaction committed.")
    except Exception as exc:
        conn.rollback()
        print(f"[TXN] ❌ Transaction rolled back → {exc}")
        raise
    finally:
        conn.close()


# ─── Schema ──────────────────────────────────────────────────────────────────

def init_db():
    with transaction() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS departments (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                budget     REAL NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS employees (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name    TEXT NOT NULL,
                last_name     TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                position      TEXT NOT NULL,
                department_id INTEGER REFERENCES departments(id),
                salary        REAL NOT NULL CHECK(salary >= 0),
                status        TEXT NOT NULL DEFAULT 'active'
                                   CHECK(status IN ('active','on_leave','resigned','terminated')),
                hire_date     TEXT DEFAULT (date('now')),
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS leave_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                leave_type  TEXT NOT NULL CHECK(leave_type IN ('vacation','sick','emergency','unpaid')),
                start_date  TEXT NOT NULL,
                end_date    TEXT NOT NULL,
                reason      TEXT,
                status      TEXT NOT NULL DEFAULT 'pending'
                                 CHECK(status IN ('pending','approved','rejected')),
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS payroll (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                period      TEXT NOT NULL,
                base_salary REAL NOT NULL,
                bonus       REAL NOT NULL DEFAULT 0,
                deductions  REAL NOT NULL DEFAULT 0,
                net_pay     REAL NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending'
                                 CHECK(status IN ('pending','processed','released')),
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                operation  TEXT NOT NULL,
                record_id  INTEGER,
                note       TEXT,
                ts         TEXT DEFAULT (datetime('now'))
            );
        """)
    print("[DB] Schema initialised.")


# ─── Audit ───────────────────────────────────────────────────────────────────

def _audit(conn, table, op, record_id, note=""):
    conn.execute(
        "INSERT INTO audit_log(table_name, operation, record_id, note) VALUES(?,?,?,?)",
        (table, op, record_id, note),
    )


# ─── DEPARTMENTS ─────────────────────────────────────────────────────────────

def create_department(name: str, budget: float) -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO departments(name, budget) VALUES(?,?)", (name, budget)
        )
        _audit(conn, "departments", "INSERT", cur.lastrowid, f"Dept: {name}")
        return cur.lastrowid


def read_departments():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM departments ORDER BY id").fetchall()
    conn.close()
    return rows


def update_department(dept_id: int, name: str = None, budget: float = None):
    with transaction() as conn:
        if name:   conn.execute("UPDATE departments SET name=?   WHERE id=?", (name,   dept_id))
        if budget is not None:
                   conn.execute("UPDATE departments SET budget=? WHERE id=?", (budget, dept_id))
        _audit(conn, "departments", "UPDATE", dept_id)


def delete_department(dept_id: int):
    with transaction() as conn:
        conn.execute("DELETE FROM departments WHERE id=?", (dept_id,))
        _audit(conn, "departments", "DELETE", dept_id)


# ─── EMPLOYEES ───────────────────────────────────────────────────────────────

def create_employee(first_name, last_name, email, position, department_id, salary, hire_date=None) -> int:
    with transaction() as conn:
        # Guard: validate department exists before insert to give a clear error
        if not department_id or not isinstance(department_id, int) or department_id <= 0:
            raise ValueError(f"Invalid department_id: {department_id!r}. Must be a positive integer.")
        dept = conn.execute("SELECT id FROM departments WHERE id=?", (department_id,)).fetchone()
        if not dept:
            raise ValueError(f"Department with id={department_id} does not exist.")
        cur = conn.execute(
            """INSERT INTO employees(first_name, last_name, email, position, department_id, salary, hire_date)
               VALUES(?,?,?,?,?,?,COALESCE(?, date('now')))""",
            (first_name, last_name, email, position, department_id, salary, hire_date),
        )
        _audit(conn, "employees", "INSERT", cur.lastrowid,
               f"New employee: {first_name} {last_name} — {position}")
        return cur.lastrowid


def read_employees():
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.*, d.name AS department_name
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY e.id
    """).fetchall()
    conn.close()
    return rows


def update_employee(emp_id: int, **kwargs):
    allowed = {"first_name","last_name","email","position","department_id","salary","status"}
    with transaction() as conn:
        # Guard: if department_id is being updated, verify it exists
        if "department_id" in kwargs and kwargs["department_id"] is not None:
            dept_id = kwargs["department_id"]
            if not isinstance(dept_id, int) or dept_id <= 0:
                raise ValueError(f"Invalid department_id: {dept_id!r}.")
            dept = conn.execute("SELECT id FROM departments WHERE id=?", (dept_id,)).fetchone()
            if not dept:
                raise ValueError(f"Department with id={dept_id} does not exist.")
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                conn.execute(f"UPDATE employees SET {k}=? WHERE id=?", (v, emp_id))
        _audit(conn, "employees", "UPDATE", emp_id, ", ".join(f"{k}={v}" for k,v in kwargs.items()))


def delete_employee(emp_id: int):
    with transaction() as conn:
        conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        _audit(conn, "employees", "DELETE", emp_id)


# ─── LEAVE REQUESTS ──────────────────────────────────────────────────────────

def create_leave_request(employee_id, leave_type, start_date, end_date, reason="") -> int:
    with transaction() as conn:
        # Verify employee is active
        emp = conn.execute(
            "SELECT status FROM employees WHERE id=?", (employee_id,)
        ).fetchone()
        if not emp:
            raise ValueError(f"Employee {employee_id} not found.")
        if emp["status"] != "active":
            raise ValueError(f"Employee is not active (status: {emp['status']}).")

        cur = conn.execute(
            """INSERT INTO leave_requests(employee_id, leave_type, start_date, end_date, reason)
               VALUES(?,?,?,?,?)""",
            (employee_id, leave_type, start_date, end_date, reason),
        )
        _audit(conn, "leave_requests", "INSERT", cur.lastrowid,
               f"Emp #{employee_id} — {leave_type} {start_date}→{end_date}")
        return cur.lastrowid


def read_leave_requests():
    conn = get_connection()
    rows = conn.execute("""
        SELECT l.*, e.first_name || ' ' || e.last_name AS employee_name
        FROM leave_requests l
        JOIN employees e ON l.employee_id = e.id
        ORDER BY l.id DESC
    """).fetchall()
    conn.close()
    return rows


def update_leave_status(leave_id: int, status: str):
    with transaction() as conn:
        leave = conn.execute("SELECT * FROM leave_requests WHERE id=?", (leave_id,)).fetchone()
        if not leave:
            raise ValueError(f"Leave request {leave_id} not found.")

        conn.execute("UPDATE leave_requests SET status=? WHERE id=?", (status, leave_id))

        # If approved → set employee status to on_leave
        if status == "approved":
            conn.execute(
                "UPDATE employees SET status='on_leave' WHERE id=?",
                (leave["employee_id"],)
            )
            _audit(conn, "employees", "UPDATE", leave["employee_id"], "Status → on_leave (leave approved)")

        _audit(conn, "leave_requests", "UPDATE", leave_id, f"Status → {status}")


def delete_leave_request(leave_id: int):
    with transaction() as conn:
        conn.execute("DELETE FROM leave_requests WHERE id=?", (leave_id,))
        _audit(conn, "leave_requests", "DELETE", leave_id)


# ─── PAYROLL ─────────────────────────────────────────────────────────────────

def process_payroll(employee_id: int, period: str, bonus: float = 0, deductions: float = 0) -> int:
    """
    Atomic payroll run: reads salary, computes net, inserts record.
    Raises if employee not found or already processed for that period.
    """
    with transaction() as conn:
        emp = conn.execute(
            "SELECT * FROM employees WHERE id=?", (employee_id,)
        ).fetchone()
        if not emp:
            raise ValueError(f"Employee {employee_id} not found.")

        existing = conn.execute(
            "SELECT id FROM payroll WHERE employee_id=? AND period=?",
            (employee_id, period)
        ).fetchone()
        if existing:
            raise ValueError(f"Payroll already processed for employee {employee_id} in {period}.")

        base = emp["salary"]
        net  = round(base + bonus - deductions, 2)

        cur = conn.execute(
            """INSERT INTO payroll(employee_id, period, base_salary, bonus, deductions, net_pay)
               VALUES(?,?,?,?,?,?)""",
            (employee_id, period, base, bonus, deductions, net),
        )
        _audit(conn, "payroll", "INSERT", cur.lastrowid,
               f"Emp #{employee_id} | {period} | Net ₱{net:,.2f}")
        return cur.lastrowid


def read_payroll():
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.*, e.first_name || ' ' || e.last_name AS employee_name
        FROM payroll p
        JOIN employees e ON p.employee_id = e.id
        ORDER BY p.id DESC
    """).fetchall()
    conn.close()
    return rows


def update_payroll_status(payroll_id: int, status: str):
    with transaction() as conn:
        conn.execute("UPDATE payroll SET status=? WHERE id=?", (status, payroll_id))
        _audit(conn, "payroll", "UPDATE", payroll_id, f"Status → {status}")


def delete_payroll(payroll_id: int):
    with transaction() as conn:
        conn.execute("DELETE FROM payroll WHERE id=?", (payroll_id,))
        _audit(conn, "payroll", "DELETE", payroll_id)


# ─── AUDIT LOG ───────────────────────────────────────────────────────────────

def read_audit_log(limit=30):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows