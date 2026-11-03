# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
env = locals().get("env")

# a portal user that is a collaborator of a shared project: this enables the
# portal timesheet rule in 19.0
partner_portal = env["res.partner"].create({"name": "OU Timesheet Portal"})
env["res.users"].with_context(no_reset_password=True).create(
    {
        "name": "OU Timesheet Portal",
        "login": "ou_timesheet_portal",
        "partner_id": partner_portal.id,
        "group_ids": [(6, 0, [env.ref("base.group_portal").id])],
    }
)
project = env["project.project"].create(
    {
        "name": "OU Timesheet Project",
        "privacy_visibility": "portal",
        "allow_timesheets": True,
    }
)
env["project.collaborator"].create(
    {
        "project_id": project.id,
        "partner_id": partner_portal.id,
        "limited_access": False,
    }
)

# a task without allocated time in a project that has some, with 2 hours of
# timesheets, and a subtask of another task without allocated time, which only
# looks at its parent
employee = env["hr.employee"].create({"name": "OU Timesheet Employee"})
project_allocated = env["project.project"].create(
    {"name": "OU Timesheet Allocated", "allow_timesheets": True, "allocated_hours": 10}
)
task, parent = env["project.task"].create(
    [
        {"name": "OU Timesheet Task", "project_id": project_allocated.id},
        {"name": "OU Timesheet Parent", "project_id": project_allocated.id},
    ]
)
child = env["project.task"].create(
    {
        "name": "OU Timesheet Subtask",
        "project_id": project_allocated.id,
        "parent_id": parent.id,
    }
)
env["account.analytic.line"].create(
    [
        {
            "name": "OU Timesheet line",
            "project_id": project_allocated.id,
            "task_id": record.id,
            "employee_id": employee.id,
            "unit_amount": hours,
        }
        for record, hours in ((task, 2.0), (child, 1.0))
    ]
)

# a translation of a group note that is updated in 20.0
env.ref("hr_timesheet.group_hr_timesheet_user").with_context(
    lang="fr_FR"
).comment = "OU Timesheet old note"

env.cr.commit()
