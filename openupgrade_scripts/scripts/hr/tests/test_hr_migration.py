# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrMigration(TransactionCase):
    def _employee(self, name):
        return self.env["hr.employee"].search([("name", "=", f"OU HR {name}")])

    def test_hr_version_tz_calendar(self):
        """Test the timezone of versions, and the flexible calendar of their company"""
        e3 = self._employee("E3")
        self.assertEqual(self._employee("E1").tz, "Asia/Shanghai")
        self.assertEqual(self._employee("E2").tz, "America/New_York")
        self.assertTrue(e3.resource_calendar_id._is_fully_flexible())
        self.assertEqual(e3.resource_calendar_id.company_id, e3.company_id)
        self.assertEqual(e3.resource_id.calendar_id, e3.resource_calendar_id)

    def test_hr_job(self):
        """Test the company, the name and the recruiter of jobs without company"""
        main_job, conflict, job = self.env["hr.job"].search(
            [("name", "like", "OU HR")], order="id"
        )
        self.assertEqual(conflict.name, f"OU HR Dup ({conflict.id})")
        self.assertEqual(conflict.company_id, main_job.company_id)
        self.assertEqual(job.company_id.name, "OU HR B")
        self.assertEqual(job.recruiter_id.name, "OU HR U1")

    def test_hr_employee_type(self):
        """Test the types of versions, and the deletion of obsolete types"""
        e1, e3 = self._employee("E1").version_id, self._employee("E3").version_id
        self.assertTrue(e1.fixed_term)
        self.assertEqual(e1.employee_type_id, self.env.ref("hr.contract_type_student"))
        self.assertEqual(e3.employee_type_id.name, "Worker")
        self.assertFalse(self.env.ref("hr.contract_type_statutory", False))

    def test_hr_employee_departure(self):
        """Test the departure, which the cron skips, and the notes of employees"""
        employee = self._employee("E5")
        departure = employee.version_ids.departure_id
        self.assertEqual(len(departure), 1)
        self.assertEqual(str(departure.last_contract_date_end), "2026-12-31")
        self.env["hr.employee.departure"]._cron_apply_departure()
        self.assertEqual(len(employee.version_ids), 2)
        self.assertEqual(employee.additional_note, "N2")
        self.assertEqual(employee.contract_template_id.name, "OU HR Template")

    def test_hr_selection_values(self):
        """Test that gender `other` is emptied and `coach` is chosen on launch"""
        template = self.env["mail.activity.plan.template"].search(
            [("plan_id.name", "=", "OU HR")]
        )
        self.assertFalse(self._employee("E2").sex)
        self.assertEqual(template.responsible_type, "on_demand")

    def test_hr_noupdate_data(self):
        """Test that an internal user can't see the bank accounts of employees"""
        user = self.env["res.users"].search([("login", "=", "ou_hr_user")])
        domain = [("partner_id", "=", self._employee("E1").work_contact_id.id)]
        self.assertTrue(self.env["res.partner.bank"].search(domain))
        self.assertFalse(self.env["res.partner.bank"].with_user(user).search(domain))
