from db.connection import Database
from app.utils import now_iso, hash_password


def seed_defaults(db: Database) -> None:
    with db.get_conn() as conn:
        now = now_iso()
        conn.execute(
            """
            INSERT OR IGNORE INTO app_settings
            (id, club_name, default_start_time, default_tee_interval, updated_at)
            VALUES (1, 'Community Golf Club', '10:00', 9, ?)
            """,
            (now,),
        )
        exists = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        if exists == 0:
            conn.execute(
                """
                INSERT INTO users
                (username, password_hash, role, member_id, active, created_at, updated_at)
                VALUES (?, ?, 'admin', NULL, 1, ?, ?)
                """,
                ("admin", hash_password("admin123"), now, now),
            )
    seed_email_templates(db)


def seed_email_templates(db) -> None:
    now = now_iso()

    templates = [
        {
            "course_id": None,
            "audience_type": "member",
            "template_type": "invitation",
            "subject_template": "Del Webb Monday Golf: {{course_name}} {{outing_date}}",
            "body_text_template": (
                "Golfers,\n\n"
                "We play at {{course_name}} next {{outing_date}}. "
                "First tee time is at {{start_time}} and Green Fees will be {{green_fee}}.\n\n"
                "First come, first serve. We have {{tee_time_count}} tee times available. "
                "If you miss the cut, you will be placed on a waitlist in the order of your responses.\n\n"
                "Let me know if you intend to play.\n\n"
                "{{rsvp_link}}\n\n"
                "--{{sender_name}}"
            ),
        },
        {
            "course_id": None,
            "audience_type": "member",
            "template_type": "pairings",
            "subject_template": "Del Webb Monday Golf: Pairings for {{outing_date}}",
            "body_text_template": (
                "Golfers,\n\n"
                "Here are the pairings for {{outing_date}} @ {{course_name}}. "
                "Please arrive at least 30 minutes prior to tee time.\n\n"
                "{{schedule_text}}\n\n"
                "--{{sender_name}}"
            ),
        },
        {
            "course_id": None,
            "audience_type": "member",
            "template_type": "revised_pairings",
            "subject_template": "Del Webb Monday Golf: Revised Pairings for {{outing_date}}",
            "body_text_template": (
                "Golfers,\n\n"
                "Here are the revised pairings for {{outing_date}} @ {{course_name}}. "
                "Please arrive at least 30 minutes prior to tee time.\n\n"
                "{{schedule_text}}\n\n"
                "--{{sender_name}}"
            ),
        },
        {
            "course_id": None,
            "audience_type": "course",
            "template_type": "course_hold_request",
            "subject_template": "Del Webb Tee Times {{outing_date}}",
            "body_text_template": (
                "For {{outing_date}}, I will need:\n\n"
                "{{requested_tee_time_count}} tee times on the 18 hole course.\n\n"
                "--{{sender_name}}"
            ),
        },
        {
            "course_id": None,
            "audience_type": "course",
            "template_type": "course_final_schedule",
            "subject_template": "Dell Webb Pairings {{outing_date}}",
            "body_text_template": (
                "Here are the pairings for the 18 hole course this week.\n\n"
                "{{schedule_text}}"
            ),
        },
    ]

    with db.get_conn() as conn:
        for template in templates:
            existing = conn.execute(
                """
                SELECT id
                FROM email_templates
                WHERE course_id IS NULL
                  AND audience_type = ?
                  AND template_type = ?
                """,
                (template["audience_type"], template["template_type"]),
            ).fetchone()

            if existing:
                continue

            conn.execute(
                """
                INSERT INTO email_templates (
                    course_id,
                    audience_type,
                    template_type,
                    subject_template,
                    body_text_template,
                    body_html_template,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    template["course_id"],
                    template["audience_type"],
                    template["template_type"],
                    template["subject_template"],
                    template["body_text_template"],
                    None,
                    now,
                    now,
                ),
            )
        conn.commit()
