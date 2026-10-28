# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date

env = locals().get("env")

Attendance = env["hr.attendance"]
main_company = env.ref("base.main_company")
default_ruleset = env.ref("hr_attendance.hr_attendance_default_ruleset")
# the lunch break of the default schedule (12:00-13:00) is deducted from worked hours
calendar = env["resource.calendar"].create({"name": "OU Attendance", "tz": "UTC"})

# the main company wants its overtime approved by a manager, and the employee has the
# default rule set, which is the only way to get overtime in 19.0
main_company.attendance_overtime_validation = "by_manager"
env.ref("hr_attendance.hr_attendance_overtime_employee_schedule_rule").write(
    {"employer_tolerance": 0.25, "employee_tolerance": 0.1}
)
employee = env["hr.employee"].create(
    {
        "name": "OU Attendance Employee",
        "company_id": main_company.id,
        "resource_calendar_id": calendar.id,
        "tz": "UTC",
    }
)
# the version has to be older than the attendances, else they have no expected hours
employee.version_id.write(
    {"ruleset_id": default_ruleset.id, "date_version": date(2026, 9, 1)}
)

# closed attendance with overtime to approve, regular closed one, open one
attendance_overtime = Attendance.create(
    {
        "employee_id": employee.id,
        "check_in": "2026-10-05 08:00:00",
        "check_out": "2026-10-05 19:00:00",
    }
)
attendance_regular = Attendance.create(
    {
        "employee_id": employee.id,
        "check_in": "2026-10-12 08:00:00",
        "check_out": "2026-10-12 17:00:00",
    }
)
Attendance.create({"employee_id": employee.id, "check_in": "2026-10-19 08:00:00"})
assert attendance_overtime.overtime_status == "to_approve", (
    attendance_overtime.overtime_status
)
assert attendance_overtime.worked_hours == 10.0, attendance_overtime.worked_hours
assert not attendance_regular.overtime_status, attendance_regular.overtime_status
assert attendance_regular.worked_hours == 8.0, attendance_regular.worked_hours
assert attendance_regular.date.weekday() == 0, attendance_regular.date

# a company without validation in another country, which has its own time type
company_be = env["res.company"].create(
    {"name": "OU Attendance BE", "country_id": env.ref("base.be").id}
)
employee_be = env["hr.employee"].create(
    {
        "name": "OU Attendance BE Employee",
        "company_id": company_be.id,
        "resource_calendar_id": calendar.id,
        "tz": "UTC",
    }
)
Attendance.create(
    {
        "employee_id": employee_be.id,
        "check_in": "2026-10-05 08:00:00",
        "check_out": "2026-10-05 19:00:00",
    }
)
Attendance.create({"employee_id": employee_be.id, "check_in": "2026-10-19 08:00:00"})

env.cr.commit()
