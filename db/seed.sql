PRAGMA foreign_keys = ON;

INSERT INTO courses (name, default_tee_time_count, active, notes)
VALUES
    ('Sample Hills Golf Club', 6, 1, 'Primary sample course'),
    ('Lakeside Country Club', 5, 1, 'Secondary sample course');

INSERT INTO course_contacts (
    course_id,
    name,
    title,
    email,
    phone,
    is_primary,
    receives_tee_time_requests,
    receives_final_schedule,
    active
)
VALUES
    (1, 'Pat Morgan', 'Golf Operations Manager', 'pat.morgan@example.com', '555-0101', 1, 1, 1, 1),
    (1, 'Jamie Lee', 'Pro Shop', 'proshop@example.com', '555-0102', 0, 1, 0, 1),
    (2, 'Casey Rivera', 'Tournament Coordinator', 'casey.rivera@example.com', '555-0201', 1, 1, 1, 1);

INSERT INTO course_fee_schedules (
    course_id,
    fee_cents,
    effective_start_date,
    effective_end_date,
    notes,
    active
)
VALUES
    (1, 6500, '2026-01-01', '2026-12-31', 'Standard 2026 outing rate', 1),
    (2, 7200, '2026-01-01', '2026-12-31', 'Standard 2026 outing rate', 1);

INSERT INTO members (
    first_name,
    last_name,
    email,
    phone,
    active
)
VALUES
    ('Alex', 'Carter', 'alex.carter@example.com', '555-1001', 1),
    ('Blake', 'Johnson', 'blake.johnson@example.com', '555-1002', 1),
    ('Chris', 'Miller', 'chris.miller@example.com', '555-1003', 1),
    ('Dana', 'Wilson', 'dana.wilson@example.com', '555-1004', 1),
    ('Elliot', 'Brown', 'elliot.brown@example.com', '555-1005', 1),
    ('Frankie', 'Davis', 'frankie.davis@example.com', '555-1006', 1);

INSERT INTO email_templates (
    template_key,
    subject,
    body,
    active
)
VALUES
    (
        'outing_invitation',
        'Golf Outing Invitation: {{outing_date}}',
        'Hello {{member_first_name}}, please RSVP for the upcoming outing at {{course_name}}.',
        1
    ),
    (
        'tee_time_request',
        'Tee Time Request for {{outing_date}}',
        'Please confirm tee time availability for {{tee_time_count}} groups on {{outing_date}}.',
        1
    ),
    (
        'final_schedule',
        'Final Golf Outing Schedule: {{outing_date}}',
        'The final schedule for {{course_name}} is ready.',
        1
    );
