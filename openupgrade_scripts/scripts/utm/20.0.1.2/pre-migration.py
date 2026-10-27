# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade

_renamed_xmlids = [
    ("crm_livechat.utm_source_livechat", "utm.utm_source_livechat"),
]

# (table, model, xmlid name, name) of the records that 20.0 adds to its data files
_linked_records = [
    ("utm_medium", "utm.medium", "utm_medium_messaging", "Messaging"),
    ("utm_medium", "utm.medium", "utm_medium_social_media", "Social Media"),
    ("utm_source", "utm.source", "utm_source_google", "Google"),
    ("utm_source", "utm.source", "utm_source_instagram", "Instagram"),
    ("utm_source", "utm.source", "utm_source_survey", "Survey"),
    ("utm_source", "utm.source", "utm_source_youtube", "YouTube"),
]


def utm_link_existing_records(env):
    """The names of sources and mediums are unique: when the new data records are
    created while a record with the same name exists (e.g. created from tracking
    URLs), the ORM would suffix the name with a counter ("Google [2]").
    Give the xmlid to the existing record instead, unless the xmlid exists
    already (19.0 creates `utm.utm_medium_<name>` on the fly in
    `_fetch_or_create_utm_medium`)."""
    for table, model, xmlid_name, name in _linked_records:
        openupgrade.logged_query(
            env.cr,
            f"""
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            SELECT 'utm', %s, %s, id, TRUE
            FROM {table}
            WHERE name = %s
            ON CONFLICT (module, name) DO NOTHING
            """,
            (xmlid_name, model, name),
        )


def utm_source_mailing_name(env):
    """utm.utm_source_mailing is renamed from 'Lead Recall' to 'Mass Mailing'.

    noupdate_changes.xml is not loaded because it only contains this name: it
    would overwrite a customized name, and it would fail on the unique name
    constraint if another source is already called 'Mass Mailing'.
    """
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE utm_source us
        SET name = 'Mass Mailing'
        FROM ir_model_data imd
        WHERE imd.module = 'utm'
            AND imd.name = 'utm_source_mailing'
            AND imd.res_id = us.id
            AND us.name = 'Lead Recall'
            AND NOT EXISTS (SELECT 1 FROM utm_source WHERE name = 'Mass Mailing')
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_xmlids(env.cr, _renamed_xmlids)
    utm_link_existing_records(env)
    utm_source_mailing_name(env)
