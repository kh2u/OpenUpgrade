# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def blog_post_publish_on(env):
    """19.0 shows a published post as of `post_date`: `published_date`, or the
    creation date when empty. So a published post dated in the future is scheduled.
    20.0 removes `post_date` and shows every published post: schedule those with
    `publish_on` instead. The cron trigger is created by the end-migration of
    website. The other published posts get their `published_date` filled."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE blog_post
        SET is_published = FALSE, publish_on = post_date
        WHERE is_published AND post_date > NOW() AT TIME ZONE 'UTC'
        """,
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE blog_post
        SET published_date = post_date
        WHERE is_published AND published_date IS NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env,
        "website_blog",
        "20.0.1.1/noupdate_changes.xml",
        xml_transformation_filename="20.0.1.1/noupdate_changes-transformation.xml",
    )
    blog_post_publish_on(env)
