PRAGMA foreign_keys = ON;

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    default_tee_time_count INTEGER NOT NULL DEFAULT 0 CHECK (default_tee_time_count >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE course_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    title TEXT,
    email TEXT,
    phone TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    receives_tee_time_requests INTEGER NOT NULL DEFAULT 1 CHECK (receives_tee_time_requests IN (0, 1)),
    receives_final_schedule INTEGER NOT NULL DEFAULT 1 CHECK (receives_final_schedule IN (0, 1)),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE course_fee_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    fee_cents INTEGER NOT NULL CHECK (fee_cents >= 0),
    effective_start_date TEXT NOT NULL,
    effective_end_date TEXT,
    notes TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE member_suspensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL,
    reason TEXT NOT NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'lifted', 'expired', 'voided')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lifted_at TEXT,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE outings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    play_date TEXT NOT NULL,
    workflow_state TEXT NOT NULL DEFAULT 'draft'
        CHECK (workflow_state IN (
            'draft',
            'invites_sent',
            'rsvp_open',
            'rsvp_closed',
            'schedule_draft',
            'schedule_final',
            'completed',
            'cancelled'
        )),
    tee_time_count INTEGER NOT NULL CHECK (tee_time_count >= 0),

    course_name_snapshot TEXT NOT NULL,
    green_fee_cents_snapshot INTEGER NOT NULL CHECK (green_fee_cents_snapshot >= 0),
    course_contact_name_snapshot TEXT,
    course_contact_email_snapshot TEXT,

    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (course_id) REFERENCES courses(id)
);

CREATE TABLE outing_invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    rsvp_token TEXT NOT NULL UNIQUE,
    sent_at TEXT,
    delivery_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (delivery_status IN ('pending', 'previewed', 'sent', 'failed')),
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    UNIQUE (outing_id, member_id)
);

CREATE TABLE rsvps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    response TEXT NOT NULL CHECK (response IN ('yes', 'no')),
    responded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL DEFAULT 'link'
        CHECK (source IN ('link', 'manual', 'admin')),
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    UNIQUE (outing_id, member_id)
);

CREATE TABLE guests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    sponsor_member_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE,
    FOREIGN KEY (sponsor_member_id) REFERENCES members(id) ON DELETE CASCADE
);

CREATE TABLE scheduling_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    sponsor_member_id INTEGER NOT NULL,
    rsvp_id INTEGER,
    unit_size INTEGER NOT NULL CHECK (unit_size BETWEEN 1 AND 4),
    priority_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'scheduled', 'waitlisted', 'ineligible', 'cancelled')),
    ineligibility_reason TEXT,
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE,
    FOREIGN KEY (sponsor_member_id) REFERENCES members(id) ON DELETE CASCADE,
    FOREIGN KEY (rsvp_id) REFERENCES rsvps(id),
    UNIQUE (outing_id, sponsor_member_id)
);

CREATE TABLE scheduling_unit_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduling_unit_id INTEGER NOT NULL,
    member_id INTEGER,
    guest_id INTEGER,
    player_type TEXT NOT NULL CHECK (player_type IN ('member', 'guest')),
    display_name TEXT NOT NULL,
    FOREIGN KEY (scheduling_unit_id) REFERENCES scheduling_units(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (guest_id) REFERENCES guests(id),
    CHECK (
        (player_type = 'member' AND member_id IS NOT NULL AND guest_id IS NULL)
        OR
        (player_type = 'guest' AND guest_id IS NOT NULL AND member_id IS NULL)
    )
);

CREATE TABLE tee_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    tee_time TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE,
    UNIQUE (outing_id, sequence_number),
    UNIQUE (outing_id, tee_time)
);

CREATE TABLE tee_time_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tee_time_id INTEGER NOT NULL,
    scheduling_unit_player_id INTEGER NOT NULL,
    slot_number INTEGER NOT NULL CHECK (slot_number BETWEEN 1 AND 4),
    FOREIGN KEY (tee_time_id) REFERENCES tee_times(id) ON DELETE CASCADE,
    FOREIGN KEY (scheduling_unit_player_id) REFERENCES scheduling_unit_players(id) ON DELETE CASCADE,
    UNIQUE (tee_time_id, slot_number),
    UNIQUE (scheduling_unit_player_id)
);

CREATE TABLE schedule_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'final')),
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TEXT,
    notes TEXT,
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE,
    UNIQUE (outing_id, version_number)
);

CREATE TABLE email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_key TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER,
    member_id INTEGER,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    email_type TEXT NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (delivery_status IN ('pending', 'previewed', 'sent', 'failed')),
    sent_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (outing_id) REFERENCES outings(id),
    FOREIGN KEY (member_id) REFERENCES members(id)
);

CREATE TABLE workflow_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outing_id INTEGER NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    event_note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (outing_id) REFERENCES outings(id) ON DELETE CASCADE
);

CREATE INDEX idx_course_contacts_course_id ON course_contacts(course_id);
CREATE INDEX idx_course_fee_schedules_course_dates ON course_fee_schedules(course_id, effective_start_date, effective_end_date);
CREATE INDEX idx_member_suspensions_member_dates ON member_suspensions(member_id, starts_on, ends_on);
CREATE INDEX idx_outings_play_date ON outings(play_date);
CREATE INDEX idx_rsvps_outing_response_time ON rsvps(outing_id, response, responded_at);
CREATE INDEX idx_scheduling_units_outing_status_priority ON scheduling_units(outing_id, status, priority_at);
CREATE INDEX idx_tee_times_outing_sequence ON tee_times(outing_id, sequence_number);
CREATE INDEX idx_email_logs_outing_type ON email_logs(outing_id, email_type);
CREATE INDEX idx_workflow_events_outing_created ON workflow_events(outing_id, created_at);
