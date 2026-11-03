# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestHrGamificationMigration(TransactionCase):
    def test_gamification_badge_user_access(self):
        """Test that the access of all users to the badges is deactivated, in favor
        of the one restricted to the badges they granted"""
        access = self.env.ref("gamification.gamification_badge_user_access")
        self.assertFalse(access.active)
