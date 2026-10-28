# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import ast

env = locals().get("env")

users = env["res.users"].with_context(no_reset_password=True)
user_1, user_4 = users.create(
    [
        {
            "name": f"OU Recruiter {i}",
            "login": f"ou_recruiter_{i}",
            "create_employee": 1,
        }
        for i in (1, 4)
    ]
)


def prop(name):
    return {"name": name, "string": name, "type": "char"}


# two jobs with a property in common
job_1, job_2 = env["hr.job"].create(
    [
        {
            "name": "OU Job 1",
            "user_id": user_1.id,
            "favorite_user_ids": [(6, 0, user_1.ids)],
            "applicant_properties_definition": [prop("ou_a")],
        },
        {
            "name": "OU Job 2",
            "applicant_properties_definition": [prop("ou_a"), prop("ou_b")],
        },
    ]
)
assert "user_id" in ast.literal_eval(job_1.alias_id.alias_defaults)

# the recruiter was changed by hand, and the stage changed once: this generates a
# tracking value, which is only created when the write is committed on its own
stage_1, stage_2 = env["hr.recruitment.stage"].create(
    [{"name": "OU Stage 1"}, {"name": "OU Stage 2"}]
)
applicant = env["hr.applicant"].create(
    {
        "partner_name": "OU Applicant",
        "job_id": job_1.id,
        "user_id": user_4.id,
        "stage_id": stage_1.id,
        "applicant_properties": {"ou_a": "x"},
    }
)
env.cr.commit()
applicant.write({"stage_id": stage_2.id})
env.cr.commit()
