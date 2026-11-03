# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
env = locals().get("env")

users = env["res.users"].with_context(no_reset_password=True)
Version, Department = env["hr.version"], env["hr.department"]
company_b = env["res.company"].create({"name": "OU HR B"})
shanghai = env["resource.calendar"].create({"name": "OU HR CN", "tz": "Asia/Shanghai"})


def employee(name, **vals):
    return env["hr.employee"].create({"name": f"OU HR {name}", **vals})


def job(name, **vals):
    env["hr.job"].create({"name": f"OU HR {name}", "company_id": False, **vals})


def ct(xmlid):
    return env.ref(f"hr.contract_type_{xmlid}").id


# working hours win over the employee's timezone, some versions are fully flexible
e1 = employee("E1", tz="Europe/Paris", resource_calendar_id=shanghai.id)
e2 = employee("E2", tz="America/New_York", resource_calendar_id=False)
e3 = employee("E3", company_id=company_b.id, resource_calendar_id=False)
e1.version_id.write({"contract_type_id": ct("temporary"), "employee_type": "student"})
e2.version_id.sex = "other"
e3.version_id.write({"contract_type_id": ct("permanent"), "employee_type": "worker"})

# a departure and notes copied to both versions, the second is after the departure
e5 = employee("E5", date_version="2026-01-01", contract_date_start="2026-01-01")
e5.version_id.contract_date_end = "2026-12-31"
version_2 = Version.create({"employee_id": e5.id, "date_version": "2026-09-20"})
e5.version_ids.write(
    {
        "departure_date": "2026-09-15",
        "departure_reason_id": env.ref("hr.departure_resigned").id,
        "departure_description": "Left",
        "additional_note": "N1",
    }
)
template = Version.create({"name": "OU HR Template"})
version_2.write({"additional_note": "N2", "contract_template_id": template.id})

# jobs without company: one conflicting with a job of the main company, one in company B
department = Department.create({"name": "OU HR D1"})
department_b = Department.create({"name": "OU HR DB", "company_id": company_b.id})
user_1 = users.create({"name": "OU HR U1", "login": "ou_hr_u1", "create_employee": 1})
job("Dup", department_id=department.id, company_id=1)
job("Dup", department_id=department.id)
job("J1", department_id=department_b.id, user_id=user_1.id)

# a plan with a coach, and a bank account that internal users may not see
plan = env["mail.activity.plan"].create({"name": "OU HR", "res_model": "hr.employee"})
env["mail.activity.plan.template"].create(
    {
        "plan_id": plan.id,
        "responsible_type": "coach",
        "activity_type_id": env.ref("mail.mail_activity_data_todo").id,
    }
)
e1.work_contact_id.bank_ids = [(0, 0, {"acc_number": "OU-HR-BANK"})]
users.create({"name": "OU HR User", "login": "ou_hr_user"})
env.cr.commit()
