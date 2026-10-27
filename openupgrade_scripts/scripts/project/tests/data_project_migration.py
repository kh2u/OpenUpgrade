# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
env = locals().get("env")

Project = env["project.project"]
Task = env["project.task"]
Users = env["res.users"].with_context(no_reset_password=True)
group_user = env.ref("base.group_user")
group_portal = env.ref("base.group_portal")
group_project_user = env.ref("project.group_project_user")

# an internal project user, who is not a project manager, and a portal user
user_a = Users.create(
    {
        "name": "OU Project Follower",
        "login": "ou_project_follower",
        "group_ids": [(6, 0, [group_user.id, group_project_user.id])],
    }
)
# portal users B and C belong to the same company, D is not related to them
partner_company = env["res.partner"].create(
    {"name": "OU Portal Company", "is_company": True}
)


def create_portal_user(name, login, parent=None):
    partner = env["res.partner"].create(
        {"name": name, "parent_id": parent.id if parent else False}
    )
    return Users.create(
        {
            "name": name,
            "login": login,
            "partner_id": partner.id,
            "group_ids": [(6, 0, [group_portal.id])],
        }
    )


user_portal = create_portal_user(
    "OU Project Portal Follower", "ou_project_portal_follower", partner_company
)
user_portal_colleague = create_portal_user(
    "OU Project Portal Colleague", "ou_project_portal_colleague", partner_company
)
user_portal_unrelated = create_portal_user(
    "OU Project Portal Unrelated", "ou_project_portal_unrelated"
)

# two stages and a project (stage and visibility)
stage_1 = env["project.task.type"].create({"name": "OU Project Stage 1"})
stage_2 = env["project.task.type"].create({"name": "OU Project Stage 2"})
project_stages = env["project.project.stage"].create(
    [{"name": "OU Project Stage A"}, {"name": "OU Project Stage B"}]
)
project_followers = Project.create(
    {
        "name": "OU Project Followers",
        "privacy_visibility": "followers",
        "type_ids": [(6, 0, [stage_1.id, stage_2.id])],
        "stage_id": project_stages[0].id,
    }
)
project_followers.message_subscribe(
    partner_ids=[user_a.partner_id.id, user_portal.partner_id.id]
)
# the same follower in a project that every internal user can access
project_employees = Project.create(
    {"name": "OU Project Employees", "privacy_visibility": "employees"}
)
project_employees.message_subscribe(partner_ids=[user_a.partner_id.id])
env.cr.commit()

# two portal collaborators, one of them with limited access
project_portal = Project.create(
    {"name": "OU Project Portal", "privacy_visibility": "portal"}
)
partner_limited = env["res.partner"].create({"name": "OU Collaborator Limited"})
partner_full = env["res.partner"].create({"name": "OU Collaborator Full"})
env["project.collaborator"].create(
    [
        {
            "project_id": project_portal.id,
            "partner_id": partner_limited.id,
            "limited_access": True,
        },
        {
            "project_id": project_portal.id,
            "partner_id": partner_full.id,
            "limited_access": False,
        },
    ]
)
env.cr.commit()

# a portal user that only follows the project, which is enough to access it in
# 19.0, and so does their colleague through the company of the follower
project_portal.message_subscribe(partner_ids=[user_portal.partner_id.id])
env.cr.commit()

# a task moves from the first stage to the second one: this generates a tracking
# value, which is only created when the write is committed on its own
task = Task.create(
    {
        "name": "OU Project Task",
        "project_id": project_followers.id,
        "stage_id": stage_1.id,
    }
)
env.cr.commit()
task.write({"stage_id": stage_2.id})
env.cr.commit()
# the project moves to its second stage too
project_followers.write({"stage_id": project_stages[1].id})
env.cr.commit()

# make the dates deterministic: the records were created 2 days ago and moved to
# their second stage 1 day ago
for record in (task, project_followers):
    env.cr.execute(
        f"""
        UPDATE {record._table}
        SET create_date = (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days'
        WHERE id = %s
        """,
        (record.id,),
    )
    env.cr.execute(
        """
        UPDATE mail_tracking_value v
        SET create_date = (NOW() AT TIME ZONE 'UTC') - INTERVAL '1 day'
        FROM mail_message m
        WHERE m.id = v.mail_message_id AND m.model = %s AND m.res_id = %s
            AND v.field_id = (
                SELECT id FROM ir_model_fields WHERE model = %s AND name = 'stage_id'
            )
        """,
        (record._name, record.id, record._name),
    )
    assert env.cr.rowcount == 1, f"expected a stage tracking value of {record}"
env.cr.commit()
