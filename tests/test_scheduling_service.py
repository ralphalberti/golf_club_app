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
