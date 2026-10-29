# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
env = locals().get("env")

website = env.ref("website.default_website")

# a menu without page
env["website.menu"].create(
    {"name": "OU Menu", "url": "/ou-menu", "website_id": website.id}
)

# pages published in the future, in the past, and not published in the future
for name, published, date in (
    ("OU Scheduled", True, "2036-01-01 10:00:00"),
    ("OU Published", True, "2020-01-01 10:00:00"),
    ("OU Draft", False, "2036-01-01 10:00:00"),
):
    env["website.page"].create(
        {
            "name": name,
            "url": "/" + name.lower().replace(" ", "-"),
            "type": "qweb",
            "key": "website." + name.lower().replace(" ", "_"),
            "arch": '<t t-name="website.page"><t t-call="website.layout"/></t>',
            "is_published": published,
            "date_publish": date,
        }
    )

# a copy of a view equal to the generic one, and one customized
generic, customized = (
    env.ref("website.option_footer_scrolltop"),
    env.ref("website.template_footer_slideout"),
)
generic.with_context(website_id=website.id).write({"active": True})
customized.with_context(website_id=website.id).write(
    {"arch": customized.arch.replace("</data>", "<!-- OU --></data>")}
)

# a view of the website with all that is converted, and the social network
website.social_facebook = "https://www.facebook.com/ou"
view = env["ir.ui.view"].create(
    {
        "name": "OU View",
        "key": "website.ou_view",
        "type": "qweb",
        "website_id": website.id,
        "arch": """<t t-name="website.ou_view">
    <a href="/website/social/facebook"><i class="fa fa-star"/></a>
    <t t-esc="1+1"/>
    <img src="/website/static/src/img/snippets_demo/s_team_member_1.jpg"/>
</t>""",
    }
)
env.cr.execute("UPDATE ir_ui_view SET visibility = '' WHERE id = %s", (view.id,))

# stored html fields of other models
env.company.report_footer = '<i class="fa fa-star"/>'
env.company.partner_id.comment = '<i class="fa fa-star"/>'

env.cr.commit()
