from db.connection import Database

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    club_name TEXT NOT NULL DEFAULT 'Community Golf Club',
    default_start_time TEXT NOT NULL DEFAULT '10:00',
    default_tee_interval INTEGER NOT NULL DEFAULT 9,
    smtp_host TEXT,
    smtp_port INTEGER,
    smtp_username TEXT,
    smtp_password TEXT,
    smtp_from_name TEXT,
    smtp_from_email TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    handicap REAL,
    skill_tier INTEGER,
    joined_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'member')),
    member_id INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (member_id) REFERENCES members(id)
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    address TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    contact_name TEXT,
    contact_email TEXT,
    preferred_format TEXT DEFAULT 'both'
);

CREATE TABLE IF NOT EXISTS outings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_date TEXT NOT NULL,
    course_id INTEGER NOT NULL,
    start_time TEXT NOT NULL DEFAULT '10:00',
    tee_interval_minutes INTEGER NOT NULL DEFAULT 9,
    tee_time_count INTEGER NOT NULL,
    max_players_per_tee_time INTEGER NOT NULL DEFAULT 4,
    status TEXT NOT NULL DEFAULT 'draft',
    version INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_by INTEGER,
    updated_by INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tee_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    tee_time TEXT NOT NULL,
    position_index INTEGER NOT NULL,
    max_players INTEGER NOT NULL DEFAULT 4,
    locked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tee_time_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tee_time_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    player_order_in_group INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    locked INTEGER NOT NULL DEFAULT 0,
    checked_in INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (tee_time_id) REFERENCES tee_times(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id),
    UNIQUE(tee_time_id, member_id)
);

CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    outing_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    date_played TEXT NOT NULL,
    tee_time_id INTEGER,
    group_label TEXT,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (outing_id) REFERENCES outings(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (tee_time_id) REFERENCES tee_times(id)
);

CREATE TABLE IF NOT EXISTS pairing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_a_id INTEGER NOT NULL,
    member_b_id INTEGER NOT NULL,
    times_paired INTEGER NOT NULL DEFAULT 0,
    last_paired_date TEXT,
    UNIQUE(member_a_id, member_b_id)
);

CREATE TABLE IF NOT EXISTS member_tee_order (
    member_id INTEGER PRIMARY KEY,
    total_rounds INTEGER NOT NULL DEFAULT 0,
    total_first_slots INTEGER NOT NULL DEFAULT 0,
    total_last_slots INTEGER NOT NULL DEFAULT 0,
    average_tee_index REAL NOT NULL DEFAULT 0,
    last_tee_index INTEGER,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (member_id) REFERENCES members(id)
);

CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    recipient_email TEXT NOT NULL,
    recipient_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL,
    attachment_paths TEXT,
    error_message TEXT,
    sent_at TEXT NOT NULL,
    FOREIGN KEY (outing_id) REFERENCES outings(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def create_schema(db: Database) -> None:
    with db.get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
