# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def project_collaborator_portal_timesheet_rule(env):
    """The access of portal users to the timesheets of the projects shared with
    them is disabled by default, and Odoo enables it when the first collaborator
    is created. The collaborators of the migrated database already exist, and
    this module creates the new `ir.access` disabled. Project already enabled
    its own rule, but this module was not loaded yet to extend that method, so
    enable the rules again now that it is."""
    collaborator = env["project.collaborator"]
    if collaborator.search([], limit=1):
        collaborator._toggle_project_sharing_portal_rules(True)


def project_task_remaining_hours(env):
    """In 19.0 a task without allocated time had no remaining time. In 20.0 it
    gets the negative time spent when its parent task (or its project, if it
    has no parent) has allocated time, so that the time spent on it counts as
    overtime. The stored value is only recomputed when one of its dependencies
    changes, so tasks that exist already would keep showing 0 while new ones in
    the same situation show a negative value: apply the new rule to them."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE project_task pt
        SET remaining_hours = 0.0 - pt.effective_hours - pt.subtask_effective_hours
        WHERE COALESCE(pt.allocated_hours, 0) = 0
            AND COALESCE(
                CASE WHEN pt.parent_id IS NOT NULL THEN (
                    SELECT parent.allocated_hours
                    FROM project_task parent
                    WHERE parent.id = pt.parent_id
                ) ELSE (
                    SELECT project.allocated_hours
                    FROM project_project project
                    WHERE project.id = pt.project_id
                ) END, 0) > 0
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    project_task_remaining_hours(env)
    openupgrade.load_data(env, "hr_timesheet", "20.0.1.0/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr,
        "hr_timesheet",
        [
            "group_hr_timesheet_approver",
            "group_hr_timesheet_user",
            "group_timesheet_manager",
        ],
        ["comment"],
    )
    project_collaborator_portal_timesheet_rule(env)
