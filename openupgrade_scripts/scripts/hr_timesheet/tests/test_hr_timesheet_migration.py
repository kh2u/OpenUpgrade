# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrTimesheetMigration(TransactionCase):
    def test_hr_timesheet_portal_rule(self):
        """
        Test that the portal timesheet rule was enabled, as there are
        collaborators
        """
        project = self.env["project.project"].search(
            [("name", "=", "OU Timesheet Project")]
        )
        self.assertEqual(
            project.collaborator_ids.partner_id.name, "OU Timesheet Portal"
        )
        self.assertTrue(
            self.env.ref("hr_timesheet.timesheet_line_rule_portal_user").active
        )

    def test_hr_timesheet_manager_rule(self):
        """
        Test that the rule that gives the project managers full access to the
        timesheets was disabled by this module
        """
        self.assertFalse(
            self.env.ref("project.account_analytic_line_rule_manager").active
        )

    def test_hr_timesheet_group_comment(self):
        """
        Test that the new note of the group was loaded and replaced its old
        translation
        """
        group = self.env.ref("hr_timesheet.group_hr_timesheet_user")
        self.assertEqual(
            group.with_context(lang="en_US").comment,
            "Can only manage their own timesheets.",
        )
        self.assertNotEqual(
            group.with_context(lang="fr_FR").comment, "OU Timesheet old note"
        )

    def test_hr_timesheet_task_remaining_hours(self):
        """
        Test that a task without allocated time in a project that has some got
        its time spent as negative remaining time, and that a subtask only
        looks at the allocated time of its parent
        """
        task = self.env["project.task"].search([("name", "=", "OU Timesheet Task")])
        child = self.env["project.task"].search([("name", "=", "OU Timesheet Subtask")])
        self.assertEqual(task.remaining_hours, -2.0)
        self.assertEqual(child.remaining_hours, 0.0)
