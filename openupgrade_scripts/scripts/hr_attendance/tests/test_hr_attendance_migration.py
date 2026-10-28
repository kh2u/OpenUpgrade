# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrAttendanceMigration(TransactionCase):
    def _get_attendances(self, employee_name, count):
        """Get the attendances of the employee, oldest first, and check that the
        migration did not run the time rules on them."""
        attendances = self.env["hr.attendance"].search(
            [("employee_id.name", "=", employee_name)], order="check_in"
        )
        self.assertEqual(len(attendances), count)
        self.assertFalse(attendances.time_rule_id)
        self.assertFalse(attendances.source_attendance_id)
        return attendances

    def test_res_company_attendance_validation(self):
        """
        Test that the company where a manager approved the overtime now validates
        the attendances manually, and the other one does not
        """
        company_be = self.env["res.company"].search([("name", "=", "OU Attendance BE")])
        self.assertEqual(
            self.env.ref("base.main_company").attendance_validation, "manual_validation"
        )
        self.assertEqual(company_be.attendance_validation, "no_validation")

    def test_hr_attendance_state(self):
        """
        Test that only the attendances waiting for the manager are drafts: the one
        with overtime to approve and the open one
        """
        attendances = self._get_attendances("OU Attendance Employee", 3)
        self.assertEqual(attendances.mapped("state"), ["draft", "validated", "draft"])
        attendances_be = self._get_attendances("OU Attendance BE Employee", 2)
        self.assertEqual(attendances_be.mapped("state"), ["validated", "validated"])

    def test_hr_attendance_break_duration(self):
        """
        Test that the lunch break deducted from worked hours in 19.0 is the break
        duration, so that worked hours stay the same when they are computed again
        """
        overtime, regular, open_attendance = self._get_attendances(
            "OU Attendance Employee", 3
        )
        self.assertAlmostEqual(overtime.break_duration, 1.0)
        self.assertAlmostEqual(regular.break_duration, 1.0)
        self.assertEqual(open_attendance.break_duration, 0.0)
        self.assertAlmostEqual(regular.worked_hours, 8.0)
        regular._compute_worked_hours()
        self.assertAlmostEqual(regular.worked_hours, 8.0)

    def test_hr_attendance_day_of_date(self):
        """Test that the day of the attendances, which are all on Mondays, is set"""
        attendances = self._get_attendances("OU Attendance Employee", 3)
        self.assertEqual(attendances.mapped("day_of_date"), ["0", "0", "0"])

    def test_hr_attendance_work_entry_type(self):
        """
        Test that the attendances have the time type of the country of their
        employee's company, not the one of the main company
        """
        attendances = self._get_attendances("OU Attendance Employee", 3)
        attendances_be = self._get_attendances("OU Attendance BE Employee", 2)
        self.assertEqual(
            attendances.work_entry_type_id,
            self.env.ref("hr_work_entry.us_work_entry_type_attendance"),
        )
        self.assertEqual(
            attendances_be.work_entry_type_id,
            self.env.ref("hr_work_entry.be_work_entry_type_attendance"),
        )

    def test_hr_time_rule_default_rules(self):
        """
        Test that the rules shipped with hr_work_entry are kept when an overtime
        rule set was in use, and the default one takes the tolerances of 19.0
        """
        rule = self.env.ref("hr_work_entry.hr_time_rule_employee_schedule")
        self.assertTrue(rule.active)
        self.assertAlmostEqual(rule.employer_tolerance, 0.25)
        self.assertAlmostEqual(rule.employee_tolerance, 0.1)
        self.assertTrue(
            self.env.ref("hr_work_entry.hr_time_rule_l10n_id_first_hour").active
        )
