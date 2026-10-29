# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.fields import Datetime
from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
class TestWebsiteBlogMigration(TransactionCase):
    def _post(self, name):
        return self.env["blog.post"].search([("name", "=", name)])

    def test_blog_post_publish_on(self):
        """Test that a post published in the future is scheduled instead"""
        post = self._post("OU Scheduled")
        self.assertEqual(
            (post.is_published, post.publish_on),
            (False, Datetime.to_datetime("2099-01-01 10:00:00")),
        )

    def test_blog_post_published_date(self):
        """Test that a published post stays published, with the date it had"""
        post = self._post("OU Published")
        self.assertEqual(
            (post.is_published, post.publish_on, post.published_date),
            (True, False, post.create_date),
        )


@openupgrade_test
@tagged("post_install")
class TestWebsiteBlogPostMigration(TransactionCase):
    def test_blog_blog_cover_properties(self):
        """Test that the default cover is the old one, with the new image format"""
        cover = self.env.ref("website_blog.blog_blog_1").cover_properties
        self.assertIn("img/cover_5.webp", cover)
        self.assertNotIn("o_cc5", cover)
