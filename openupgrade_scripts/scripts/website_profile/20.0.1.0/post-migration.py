# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(env, "website_profile", "20.0.1.0/noupdate_changes.xml")
    # the body of the template is translated as a whole
    openupgrade.delete_record_translations(
        env.cr, "website_profile", ["validation_email"], ["body_html"]
    )
