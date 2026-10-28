# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import ast

from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrRecruitmentMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.applicant = self.env["hr.applicant"].search(
            [("partner_name", "=", "OU Applicant")]
        )
        self.job = self.env["hr.job"].search([("name", "=", "OU Job 1")])
        self.employee_1, self.employee_4 = (
            self.env["hr.employee"].search(
                [("user_id.login", "=", f"ou_recruiter_{i}")]
            )
            for i in (1, 4)
        )

    def test_hr_applicant_duration_tracking(self):
        """Test that the history of the stages was rebuilt from the tracking values"""
        stage_1, stage_2 = self.env["hr.recruitment.stage"].search(
            [("name", "like", "OU Stage")], order="name"
        )
        self.assertEqual(self.applicant.duration_tracking["s"], stage_2.id)
        self.assertIn(str(stage_1.id), self.applicant.duration_tracking)

    def test_hr_applicant_recruiter_id(self):
        """Test that the recruiter set by hand is kept, not the one of the job"""
        self.assertEqual(self.applicant.recruiter_id, self.employee_4)

    def test_hr_job_alias_defaults(self):
        """Test that the defaults of the alias hold the employee, not the user"""
        defaults = ast.literal_eval(self.job.alias_id.alias_defaults)
        self.assertNotIn("user_id", defaults)
        self.assertEqual(defaults["recruiter_id"], self.employee_1.id)
        self.env["hr.applicant"].create(dict(defaults, partner_name="OU Alias"))

    def test_hr_job_favorite_recruiter_ids(self):
        """Test that the favorite of the user is a favorite of its employee"""
        self.assertEqual(self.job.favorite_recruiter_ids, self.employee_1)

    def test_res_company_applicant_properties_definition(self):
        """Test that the properties of the jobs were merged in the company, without
        duplicate, and that the value of the applicant can be read"""
        definition = self.env.company.applicant_properties_definition
        names = [d["name"] for d in definition if d["name"].startswith("ou_")]
        self.assertEqual(names, ["ou_a", "ou_b"])
        properties = self.applicant.read(["applicant_properties"])[0]
        values = {p["name"]: p.get("value") for p in properties["applicant_properties"]}
        self.assertEqual(values["ou_a"], "x")
