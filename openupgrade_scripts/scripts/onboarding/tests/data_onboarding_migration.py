env = locals().get("env")

env["onboarding.onboarding.step"].create(
    {"title": "OU test trophy", "done_icon": "fa-trophy"}
)
# icon without a counterpart
env["onboarding.onboarding.step"].create(
    {"title": "OU test unknown", "done_icon": "fa-ou-unknown"}
)

env.cr.commit()
