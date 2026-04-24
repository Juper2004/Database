from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

from db import (
    init_db,
    create_department, read_departments, update_department, delete_department,
    create_employee,   read_employees,   update_employee,   delete_employee,
    create_leave_request, read_leave_requests, update_leave_status, delete_leave_request,
    process_payroll,  read_payroll,  update_payroll_status, delete_payroll,
    read_audit_log,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Employee Management System", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Schemas ──────────────────────────────────────────────────────────────────

class DeptIn(BaseModel):
    name: str
    budget: float

class DeptUpdate(BaseModel):
    name: Optional[str] = None
    budget: Optional[float] = None

class EmployeeIn(BaseModel):
    first_name: str
    last_name: str
    email: str
    position: str
    department_id: int
    salary: float
    hire_date: Optional[str] = None

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    position: Optional[str] = None
    department_id: Optional[int] = None
    salary: Optional[float] = None
    status: Optional[str] = None

class LeaveIn(BaseModel):
    employee_id: int
    leave_type: str
    start_date: str
    end_date: str
    reason: Optional[str] = ""

class LeaveStatusUpdate(BaseModel):
    status: str

class PayrollIn(BaseModel):
    employee_id: int
    period: str
    bonus: Optional[float] = 0
    deductions: Optional[float] = 0

class PayrollStatusUpdate(BaseModel):
    status: str

# ── Departments ───────────────────────────────────────────────────────────────
@app.get("/departments")
def list_departments():
    return [dict(r) for r in read_departments()]

@app.post("/departments", status_code=201)
def add_department(body: DeptIn):
    try:
        did = create_department(body.name, body.budget)
        return {"id": did}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.put("/departments/{did}")
def edit_department(did: int, body: DeptUpdate):
    try:
        update_department(did, body.name, body.budget)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.delete("/departments/{did}")
def remove_department(did: int):
    try:
        delete_department(did)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

# ── Employees ─────────────────────────────────────────────────────────────────
@app.get("/employees")
def list_employees():
    return [dict(r) for r in read_employees()]

@app.post("/employees", status_code=201)
def add_employee(body: EmployeeIn):
    try:
        eid = create_employee(body.first_name, body.last_name, body.email,
                              body.position, body.department_id, body.salary, body.hire_date)
        return {"id": eid}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.put("/employees/{eid}")
def edit_employee(eid: int, body: EmployeeUpdate):
    try:
        update_employee(eid, **body.dict(exclude_none=True))
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.delete("/employees/{eid}")
def remove_employee(eid: int):
    try:
        delete_employee(eid)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

# ── Leave Requests ────────────────────────────────────────────────────────────
@app.get("/leaves")
def list_leaves():
    return [dict(r) for r in read_leave_requests()]

@app.post("/leaves", status_code=201)
def add_leave(body: LeaveIn):
    try:
        lid = create_leave_request(body.employee_id, body.leave_type,
                                   body.start_date, body.end_date, body.reason)
        return {"id": lid}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.put("/leaves/{lid}/status")
def change_leave_status(lid: int, body: LeaveStatusUpdate):
    try:
        update_leave_status(lid, body.status)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.delete("/leaves/{lid}")
def remove_leave(lid: int):
    try:
        delete_leave_request(lid)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

# ── Payroll ───────────────────────────────────────────────────────────────────
@app.get("/payroll")
def list_payroll():
    return [dict(r) for r in read_payroll()]

@app.post("/payroll", status_code=201)
def run_payroll(body: PayrollIn):
    try:
        pid = process_payroll(body.employee_id, body.period, body.bonus, body.deductions)
        return {"id": pid}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.put("/payroll/{pid}/status")
def change_payroll_status(pid: int, body: PayrollStatusUpdate):
    try:
        update_payroll_status(pid, body.status)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.delete("/payroll/{pid}")
def remove_payroll(pid: int):
    try:
        delete_payroll(pid)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, str(e))

# ── Audit ─────────────────────────────────────────────────────────────────────
@app.get("/audit")
def audit(limit: int = 40):
    return [dict(r) for r in read_audit_log(limit)]

@app.get("/")
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

@app.get("/hr.jpg")
def logo():
    return FileResponse("hr.jpg")
