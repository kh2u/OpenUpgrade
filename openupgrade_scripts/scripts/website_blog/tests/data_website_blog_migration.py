# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
env = locals().get("env")

blog = env.ref("website_blog.blog_blog_1")
env["blog.post"].create(
    [
        # scheduled: published, with a date in the future
        {
            "name": "OU Scheduled",
            "blog_id": blog.id,
            "is_published": True,
            "published_date": "2099-01-01 10:00:00",
        },
        # published without date: `post_date` is the creation date
        {"name": "OU Published", "blog_id": blog.id, "is_published": True},
    ]
)
env.cr.commit()
