"""Seed Employee Management System with demo data."""
from db import (
    init_db,
    create_department, create_employee,
    create_leave_request, update_leave_status,
    process_payroll, read_audit_log,
)

def seed():
    init_db()

    print("\n── Departments ──")
    d1 = create_department("Engineering",    2_000_000)
    d2 = create_department("Human Resources",  800_000)
    d3 = create_department("Finance",        1_500_000)
    d4 = create_department("Marketing",        900_000)
    print(f"  Created: {d1}, {d2}, {d3}, {d4}")

    print("\n── Employees ──")
    e1 = create_employee("Maria",  "Santos",   "maria@company.com",   "Senior Engineer",    d1, 85_000, "2022-03-15")
    e2 = create_employee("Juan",   "Dela Cruz","juan@company.com",    "HR Manager",         d2, 70_000, "2021-06-01")
    e3 = create_employee("Anna",   "Reyes",    "anna@company.com",    "Financial Analyst",  d3, 65_000, "2023-01-10")
    e4 = create_employee("Carlo",  "Bautista", "carlo@company.com",   "Marketing Lead",     d4, 72_000, "2022-09-20")
    e5 = create_employee("Liza",   "Flores",   "liza@company.com",    "Junior Engineer",    d1, 45_000, "2024-02-01")
    print(f"  Created: {e1}, {e2}, {e3}, {e4}, {e5}")

    print("\n── Leave Requests ──")
    l1 = create_leave_request(e1, "vacation",  "2025-08-01", "2025-08-07", "Family trip")
    l2 = create_leave_request(e3, "sick",      "2025-07-20", "2025-07-22", "Flu")
    print(f"  Leave requests: {l1}, {l2}")
    update_leave_status(l2, "approved")    # e3 → on_leave

    print("\n── Payroll ──")
    p1 = process_payroll(e1, "2025-07", bonus=5000, deductions=2000)
    p2 = process_payroll(e2, "2025-07", bonus=3000, deductions=1500)
    p3 = process_payroll(e4, "2025-07", bonus=4000, deductions=1800)
    print(f"  Payroll records: {p1}, {p2}, {p3}")

    print("\n── Duplicate payroll rollback demo ──")
    try:
        process_payroll(e1, "2025-07")  # already processed
    except ValueError as ex:
        print(f"  Expected rollback: {ex}")

    print("\n── Audit Log (last 10) ──")
    for row in read_audit_log(10):
        print(f"  [{row['ts']}] {row['table_name']}.{row['operation']} id={row['record_id']}  {row['note']}")

if __name__ == "__main__":
    seed()