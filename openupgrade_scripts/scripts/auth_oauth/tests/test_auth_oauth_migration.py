# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestAuthOauthMigration(TransactionCase):
    def _provider(self, name):
        return self.env["auth.oauth.provider"].search([("name", "=", name)], limit=1)

    def test_default_css_class(self):
        """
        Test that the 19.0 default css_class got the 20.0 default and icon
        """
        provider = self._provider("OU test default")
        self.assertEqual(provider.css_class, "oi oi-fw text-primary")
        self.assertEqual(provider.icon, "login")

    def test_custom_css_class(self):
        """
        Test that the brand icon of a custom css_class moved to the icon field
        """
        provider = self._provider("OU test github")
        self.assertEqual(provider.css_class, "oi oi-fw text-dark")
        self.assertEqual(provider.icon, "oi_github")

    def test_oi_css_class(self):
        """
        Test that an odoo_ui_icons class is converted as well
        """
        provider = self._provider("OU test oi")
        self.assertEqual(provider.css_class, "oi text-info")
        self.assertEqual(provider.icon, "search")

    def test_unknown_css_class(self):
        """
        Test that without a counterpart only the modifier classes are converted
        """
        provider = self._provider("OU test unknown")
        self.assertEqual(provider.css_class, "oi oi-fw fa-ou-unknown text-info")
        self.assertEqual(provider.icon, "login")

    def test_standard_provider(self):
        """
        Test that the css_class of a standard provider is untouched
        """
        provider = self.env.ref("auth_oauth.provider_openerp")
        self.assertEqual(
            provider.css_class, "o_auth_oauth_provider_icon o_odoo_provider"
        )
        self.assertEqual(provider.icon, "login")
