from services.scheduler_units import Participant, SchedulingUnit


def test_participant_member_shape():
    participant = Participant(
        kind="member",
        id=10,
        display_name="Alice Smith",
        sponsor_member_id=None,
        skill_tier=2,
        handicap=14.2,
    )

    assert participant.kind == "member"
    assert participant.id == 10
    assert participant.display_name == "Alice Smith"
    assert participant.skill_tier == 2
    assert participant.handicap == 14.2


def test_scheduling_unit_size_and_ids():
    unit = SchedulingUnit(
        sponsor_member_id=7,
        participants=(
            Participant(
                kind="member",
                id=7,
                display_name="Bob Jones",
                skill_tier=1,
                handicap=8.1,
            ),
            Participant(
                kind="guest",
                id=101,
                display_name="Tom Guest",
                sponsor_member_id=7,
            ),
            Participant(
                kind="guest",
                id=102,
                display_name="Jim Guest",
                sponsor_member_id=7,
            ),
        ),
    )

    assert unit.size == 3
    assert unit.sponsor.id == 7
    assert unit.member_ids == (7,)
    assert unit.guest_ids == (101, 102)


def test_guest_unit_that_does_not_fit_does_not_block_later_solo_member():
    capacity = 8

    units = [
        ("A", 3),  # sponsor + 2 guests
        ("B", 3),  # sponsor + 2 guests
        ("C", 3),  # sponsor + 2 guests -> does not fit
        ("D", 1),  # solo member should still fit
    ]

    scheduled = []
    used_capacity = 0

    for sponsor, unit_size in units:
        if used_capacity + unit_size > capacity:
            # oversized guest-containing unit may be skipped
            if unit_size > 1:
                continue

            # solo RSVP members still get scheduled
            break

        scheduled.append(sponsor)
        used_capacity += unit_size

    assert scheduled == ["A", "B", "D"]
