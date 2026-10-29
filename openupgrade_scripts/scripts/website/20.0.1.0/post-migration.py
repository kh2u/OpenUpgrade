# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def website_menu_manual_url(env):
    """The url of the menus is not stored anymore: it is the one of the page, or
    `manual_url` without page. The menus of the apps (/shop, /blog...) and the
    external links have no page. Only SQL, the inverse of `url` changes pages."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_menu SET manual_url = url
        WHERE page_id IS NULL AND url IS NOT NULL AND url NOT IN ('', '#')
        """,
    )


def website_menu_contactus(env):
    """Delete the template menu of `menu_contactus` with SQL: unlinking a template
    menu with the ORM also deletes the menus with the same url of all websites."""
    openupgrade.logged_query(
        env.cr,
        """
        WITH menu AS (
            DELETE FROM website_menu m
            USING ir_model_data d
            WHERE d.module = 'website' AND d.name = 'menu_contactus'
                AND d.model = 'website.menu' AND d.res_id = m.id
                AND m.website_id IS NULL
            RETURNING m.id
        )
        DELETE FROM ir_model_data
        WHERE model = 'website.menu' AND res_id IN (SELECT id FROM menu)
        """,
    )


def website_page_publish_on(env):
    """A page published with a date in the future was published later in 19.0. In
    20.0 it is scheduled with `publish_on`, which needs an unpublished page. The
    published pages get their `published_date`. The trigger of the cron which
    publishes the scheduled pages is created in end-migration."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_page
        SET publish_on = date_publish, is_published = FALSE
        WHERE is_published AND date_publish > now() AT TIME ZONE 'UTC'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE website_page SET published_date = date_publish
        WHERE is_published AND date_publish <= now() AT TIME ZONE 'UTC'
            AND published_date IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    website_menu_manual_url(env)
    website_menu_contactus(env)
    openupgrade.load_data(
        env,
        "website",
        "20.0.1.0/noupdate_changes.xml",
        xml_transformation_filename="20.0.1.0/noupdate_changes-transformation.xml",
    )
    website_page_publish_on(env)
