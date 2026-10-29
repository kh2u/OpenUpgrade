# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import TransactionCase, tagged

from odoo.addons.openupgrade_framework import openupgrade_test


@openupgrade_test
@tagged("post_install")
class TestWebsiteMigration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref("base.default_website")
        self.view = self.env["ir.ui.view"].search([("key", "=", "website.ou_view")])

    def _page(self, url):
        return self.env["website.page"].search([("url", "=", url)])

    def _copy(self, key):
        views = self.env["ir.ui.view"].with_context(active_test=False)
        return views.search([("key", "=", key), ("website_id", "=", self.website.id)])

    def test_ir_ui_view_visibility(self):
        """Test that the visibility `''` of public views is now `public`"""
        self.assertEqual(self.view.visibility, "public")

    def test_website_menu_manual_url(self):
        """Test that the url of a menu without page was kept"""
        menu = self.env["website.menu"].search([("name", "=", "OU Menu")])
        self.assertEqual(menu.url, "/ou-menu")

    def test_website_menu_home(self):
        """Test that the menu of the template is still linked to the homepage"""
        menu = self.env.ref("website.menu_home")
        self.assertEqual(menu.page_id, self.env.ref("website.homepage_page"))

    def test_website_menu_contactus(self):
        """Test that the menu of the website was kept, but not the template"""
        domain = [("url", "=", "/contactus"), ("website_id", "=", self.website.id)]
        self.assertTrue(self.env["website.menu"].search(domain))
        self.assertFalse(self.env.ref("website.menu_contactus", False))

    def test_website_page_publish_on(self):
        """Test that the page published in the future is scheduled"""
        page = self._page("/ou-scheduled")
        self.assertEqual(str(page.publish_on), "2036-01-01 10:00:00")
        self.assertFalse(page.is_published)

    def test_website_page_cron_trigger(self):
        """Test that the cron which publishes the scheduled pages will run on time"""
        cron = self.env.ref("website.ir_cron_publish_scheduled_pages")
        domain = [("cron_id", "=", cron.id), ("call_at", "=", "2036-01-01 10:00:00")]
        self.assertTrue(self.env["ir.cron.trigger"].search(domain))

    def test_website_page_published_date(self):
        """Test that the page published in the past got its published date"""
        page = self._page("/ou-published")
        self.assertEqual(str(page.published_date), "2020-01-01 10:00:00")
        self.assertTrue(page.is_published)

    def test_website_page_not_published(self):
        """Test that a page not published is not scheduled"""
        self.assertFalse(self._page("/ou-draft").publish_on)

    def test_cow_templates_equal_to_upstream(self):
        """Test that the copy of a view equal to its generic view was reset to it,
        with the translations"""
        self.env.cr.execute(
            "SELECT COUNT(DISTINCT arch_db) FROM ir_ui_view WHERE key = %s",
            ("website.option_footer_scrolltop",),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1)

    def test_cow_templates_customized(self):
        """Test that the copy of a customized view was not reset"""
        self.assertIn(
            "<!-- OU -->", self._copy("website.template_footer_slideout").arch_db
        )

    def test_res_company_social_facebook(self):
        """Test that the social network of the website was copied to its company"""
        self.assertEqual(
            self.website.company_id.social_facebook, "https://www.facebook.com/ou"
        )

    def test_stored_html_social_link(self):
        """Test that the link to the social network was replaced with its url"""
        self.assertIn('href="https://www.facebook.com/ou"', self.view.arch_db)

    def test_stored_html_icon(self):
        """Test that the FontAwesome icon was converted"""
        self.assertIn('data-icon="star"', self.view.arch_db)

    def test_stored_html_t_out(self):
        """Test that t-esc was replaced with t-out"""
        self.assertIn('t-out="1+1"', self.view.arch_db)

    def test_stored_html_static_image(self):
        """Test that the path of the image which changed of format was updated"""
        self.assertIn("s_team_member_1.webp", self.view.arch_db)

    def test_stored_html_other_models(self):
        """Test that the html fields of the other models are converted, translated
        or not"""
        company = self.website.company_id
        self.assertIn('data-icon="star"', company.report_footer)
        self.assertIn('data-icon="star"', company.partner_id.comment)

    def test_stored_cover_properties(self):
        """Test that the path of the image of a cover which changed of format is
        not the old one anymore"""
        self.env.cr.execute(
            """
            SELECT cover_properties FROM blog_blog b
            JOIN ir_model_data d ON d.model = 'blog.blog' AND d.res_id = b.id
            WHERE d.module = 'website_blog' AND d.name = 'blog_blog_1'
            """
        )
        self.assertNotIn("cover_5.jpg", self.env.cr.fetchone()[0])
