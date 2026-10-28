env = locals().get("env")

provider_vals = {
    "auth_endpoint": "https://example.com/oauth/authorize",
    "validation_endpoint": "https://example.com/oauth/userinfo",
}
# 19.0 default css_class
env["auth.oauth.provider"].create(
    {**provider_vals, "name": "OU test default", "body": "Default"}
)
# brand icon, which has to survive the migration
env["auth.oauth.provider"].create(
    {
        **provider_vals,
        "name": "OU test github",
        "body": "GitHub",
        "css_class": "fa fa-fw fa-github text-dark",
    }
)
# icon of the former odoo_ui_icons
env["auth.oauth.provider"].create(
    {
        **provider_vals,
        "name": "OU test oi",
        "body": "Search",
        "css_class": "oi oi-search text-info",
    }
)
# icon without a counterpart
env["auth.oauth.provider"].create(
    {
        **provider_vals,
        "name": "OU test unknown",
        "body": "Unknown",
        "css_class": "fa fa-fw fa-ou-unknown text-info",
    }
)

env.cr.commit()
