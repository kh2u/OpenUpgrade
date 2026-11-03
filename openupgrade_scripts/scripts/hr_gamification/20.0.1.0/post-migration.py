# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # gamification creates the access of all users to the badges before the noupdate
    # data of this module is loaded, which then skips it: deactivate it as done on
    # a fresh install, or any employee could edit the badges of others
    openupgrade.load_data(env, "hr_gamification", "20.0.1.0/noupdate_changes.xml")
