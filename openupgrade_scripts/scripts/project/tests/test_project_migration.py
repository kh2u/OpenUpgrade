# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestProjectMigration(TransactionCase):
    def _get_stage_tracking_date(self, record):
        """Get the date of the only tracking value of the stage of the record."""
        self.env.cr.execute(
            """
            SELECT v.create_date
            FROM mail_tracking_value v
            JOIN mail_message m ON m.id = v.mail_message_id
            WHERE m.model = %s AND m.res_id = %s AND v.field_id = (
                SELECT id FROM ir_model_fields WHERE model = %s AND name = 'stage_id'
            )
            """,
            (record._name, record.id, record._name),
        )
        rows = self.env.cr.fetchall()
        self.assertEqual(len(rows), 1)
        return rows[0][0]

    def test_project_allowed_internal_user_ids(self):
        """
        Test that the internal followers of a project with restricted visibility
        got access to it, and only them
        """
        user = self.env["res.users"].search([("login", "=", "ou_project_follower")])
        user_portal = self.env["res.users"].search(
            [("login", "=", "ou_project_portal_follower")]
        )
        project = self.env["project.project"].search(
            [("name", "=", "OU Project Followers")]
        )
        project_employees = self.env["project.project"].search(
            [("name", "=", "OU Project Employees")]
        )
        self.assertIn(user, project.allowed_internal_user_ids)
        self.assertNotIn(user_portal, project.allowed_internal_user_ids)
        self.assertNotIn(user, project_employees.allowed_internal_user_ids)

    def _get_access_modes(self, project_name):
        """Get the access mode of the collaborators of the project by name."""
        project = self.env["project.project"].search([("name", "=", project_name)])
        self.assertEqual(len(project), 1)
        return {
            collaborator.partner_id.name: collaborator.access_mode
            for collaborator in project.collaborator_ids
        }

    def test_project_collaborator_access_mode(self):
        """
        Test that the collaborators can still edit: the ones with limited access
        got `edit` and the others `advanced_edit`
        """
        access_modes = self._get_access_modes("OU Project Portal")
        self.assertEqual(access_modes["OU Collaborator Limited"], "edit")
        self.assertEqual(access_modes["OU Collaborator Full"], "advanced_edit")

    def test_project_portal_followers_collaborators(self):
        """
        Test that the portal users that accessed the project as followers, or
        through a follower of their company, became `view` collaborators, and
        nobody else
        """
        self.assertEqual(
            self._get_access_modes("OU Project Portal"),
            {
                "OU Collaborator Limited": "edit",
                "OU Collaborator Full": "advanced_edit",
                "OU Project Portal Follower": "view",
                "OU Project Portal Colleague": "view",
            },
        )
        # the project is not visible to portal users: nothing to preserve
        self.assertFalse(self._get_access_modes("OU Project Followers"))

    def test_project_collaborator_sharing_rule(self):
        """
        Test that the access rule of the project sharing was enabled, as there
        are collaborators
        """
        self.assertTrue(
            self.env.ref("project.project_task_rule_portal_project_sharing").active
        )

    def test_project_task_duration_tracking(self):
        """
        Test that the time spent in the previous stage was rebuilt from the
        tracking values, and that the date is the one of the stage change
        """
        task = self.env["project.task"].search([("name", "=", "OU Project Task")])
        stage_1 = self.env["project.task.type"].search(
            [("name", "=", "OU Project Stage 1")]
        )
        duration_tracking = task.duration_tracking
        self.assertEqual(duration_tracking["s"], task.stage_id.id)
        self.assertNotEqual(task.stage_id, stage_1)
        # created 2 days ago, moved to the next stage 1 day ago: 1 day in stage 1
        self.assertAlmostEqual(duration_tracking[str(stage_1.id)], 1440, delta=2)
        self.assertEqual(
            duration_tracking["d"],
            fields.Datetime.to_string(self._get_stage_tracking_date(task)),
        )

    def test_project_project_duration_tracking(self):
        """
        Test that the project got the history of its stages and the date of
        its last stage change, which is a new field
        """
        project = self.env["project.project"].search(
            [("name", "=", "OU Project Followers")]
        )
        stage_a = self.env["project.project.stage"].search(
            [("name", "=", "OU Project Stage A")]
        )
        stage_changed_on = self._get_stage_tracking_date(project)
        duration_tracking = project.duration_tracking
        self.assertEqual(duration_tracking["s"], project.stage_id.id)
        self.assertNotEqual(project.stage_id, stage_a)
        self.assertAlmostEqual(duration_tracking[str(stage_a.id)], 1440, delta=2)
        self.assertEqual(
            duration_tracking["d"], fields.Datetime.to_string(stage_changed_on)
        )
        self.assertEqual(
            project.date_last_stage_update, stage_changed_on.replace(microsecond=0)
        )
