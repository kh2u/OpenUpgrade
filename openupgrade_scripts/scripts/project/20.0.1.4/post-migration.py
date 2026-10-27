# Copyright 2026 KH1688
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from openupgradelib import openupgrade


def project_collaborator_access_mode(env):
    """`limited_access` is replaced by `access_mode`, which the ORM creates with the
    default `view` for every row. In 19.0 collaborators could edit, and only
    those with `limited_access` were restricted, so keep them editors: `edit` for
    them and `advanced_edit` (the only mode that can change the stage and
    priority of tasks) for the others. Mapping them to `view` would make all the
    collaborators read-only."""
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE project_collaborator
        SET access_mode = CASE
            WHEN limited_access THEN 'edit' ELSE 'advanced_edit' END
        """,
    )


def project_project_allowed_internal_user_ids(env):
    """In 19.0 the internal followers of a project with restricted visibility could
    access it, its tasks and its updates. In 20.0 the access rules look at
    `allowed_internal_user_ids` (team members) instead, which the ORM only fills
    with the project manager. Add the internal followers, as the compute method
    does for company: users that cannot access the company of the project are
    skipped. Followers of single tasks are not added: the task rules still give
    them access to those tasks, and adding them to the team would give them
    access to the whole project."""
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO project_allowed_internal_users_rel
            (project_project_id, res_users_id)
        SELECT DISTINCT p.id, u.id
        FROM project_project p
        JOIN mail_followers f
            ON f.res_model = 'project.project' AND f.res_id = p.id
        JOIN res_users u ON u.partner_id = f.partner_id AND NOT u.share
        WHERE p.privacy_visibility IN ('followers', 'invited_users')
            AND (p.company_id IS NULL OR EXISTS (
                SELECT 1
                FROM res_company_users_rel cu
                WHERE cu.user_id = u.id AND cu.cid = p.company_id
            ))
        ON CONFLICT DO NOTHING
        """,
    )


def project_portal_followers_collaborators(env):
    """In 19.0 a portal user could access a project (visible to portal users) if
    one of its followers belonged to the same commercial partner as the user.
    20.0 only looks at the collaborators, so make the portal users that got access
    this way read-only collaborators (`view`, as 20.0 does for the customer of a
    project). Done with SQL to avoid sending invitations. Must run after the
    mapping of `access_mode`, which would overwrite the new rows."""
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO project_collaborator
            (project_id, partner_id, access_mode,
             create_uid, write_uid, create_date, write_date)
        SELECT DISTINCT p.id, u.partner_id, 'view',
            %(uid)s, %(uid)s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC'
        FROM project_project p
        JOIN mail_followers f
            ON f.res_model = 'project.project' AND f.res_id = p.id
        JOIN res_partner follower ON follower.id = f.partner_id
        JOIN res_partner portal_partner
            ON portal_partner.commercial_partner_id = follower.commercial_partner_id
        JOIN res_users u ON u.partner_id = portal_partner.id AND u.share
        JOIN res_groups_users_rel gu ON gu.uid = u.id AND gu.gid = %(group_portal)s
        WHERE p.privacy_visibility IN ('invited_users', 'portal')
        ON CONFLICT DO NOTHING
        """,
        {"uid": env.uid, "group_portal": env.ref("base.group_portal").id},
    )


def project_collaborator_sharing_rule(env):
    """The portal access rule of the project sharing is disabled by default in
    20.0 and Odoo enables it when the first collaborator is created. The
    collaborators of the migrated database already exist, so enable it here."""
    collaborator = env["project.collaborator"]
    if collaborator.search([], limit=1):
        collaborator._toggle_project_sharing_portal_rules(True)


@openupgrade.migrate()
def migrate(env, version):
    project_collaborator_access_mode(env)
    project_portal_followers_collaborators(env)
    project_project_allowed_internal_user_ids(env)
    openupgrade.load_data(env, "project", "20.0.1.4/noupdate_changes.xml")
    openupgrade.delete_record_translations(
        env.cr, "project", ["project_message_user_assigned"], ["arch_db"]
    )
    project_collaborator_sharing_rule(env)
