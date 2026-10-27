# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestUtmMigration(TransactionCase):
    def test_existing_records_linked(self):
        """
        Test that the records created before the migration got the xmlid of the
        new data record, instead of a duplicate named with a counter
        """
        source = self.env.ref("utm.utm_source_google")
        self.assertEqual(source.name, "Google")
        self.assertFalse(
            self.env["utm.source"].search_count([("name", "=like", "Google [%]")])
        )
        medium = self.env.ref("utm.utm_medium_social_media")
        self.assertEqual(medium.name, "Social Media")
        self.assertFalse(
            self.env["utm.medium"].search_count([("name", "=like", "Social Media [%]")])
        )

    def test_livechat_source_xmlid(self):
        """
        Test that the livechat source of crm_livechat is the one of utm
        """
        source = self.env.ref("utm.utm_source_livechat")
        self.assertEqual(source.name, "Livechat")
        self.assertFalse(
            self.env["utm.source"].search_count([("name", "=like", "Livechat [%]")])
        )
        self.assertFalse(
            self.env.ref("crm_livechat.utm_source_livechat", raise_if_not_found=False)
        )

    def test_source_mailing_name(self):
        """
        Test that the mailing source got its new name
        """
        self.assertEqual(self.env.ref("utm.utm_source_mailing").name, "Mass Mailing")
