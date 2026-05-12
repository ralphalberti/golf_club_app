from db.connection import Database
from db.schema import create_schema

from repositories.course_repository import CourseRepository
from repositories.member_repository import MemberRepository
from repositories.outing_repository import OutingRepository
from repositories.rsvp_repository import RSVPRepository
from repositories.guest_repository import GuestRepository

from services.scheduling_service import SchedulingService
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


def test_scheduler_skips_oversized_guest_unit_but_schedules_later_solo_member(
    tmp_path,
):
    #
    # Create isolated temp database
    #
    db_path = tmp_path / "test_scheduler.db"

    db = Database(db_path)

    create_schema(db)

    #
    # Repositories / services
    #
    course_repo = CourseRepository(db)
    member_repo = MemberRepository(db)
    outing_repo = OutingRepository(db)
    rsvp_repo = RSVPRepository(db)
    guest_repo = GuestRepository(db)
    scheduling_service = SchedulingService(db)

    #
    # Create course
    #
    course_id = course_repo.create(
        {
            "name": "Test Course",
        }
    )

    #
    # Create outing
    #
    outing_id = outing_repo.create(
        {
            "outing_date": "2026-05-01",
            "course_id": course_id,
            "start_time": "10:00",
            "tee_interval_minutes": 9,
            "tee_time_count": 2,
            "max_players_per_tee_time": 4,
            "status": "open",
        }
    )

    #
    # Create members A/B/C/D
    #
    member_ids = []

    for name in ["A", "B", "C", "D"]:
        member_id = member_repo.create(
            {
                "first_name": name,
                "last_name": "Member",
                "joined_date": "2026-01-01",
                "skill_tier": 1,
            }
        )

        member_ids.append(member_id)

    #
    # RSVP all YES in order
    #
    for member_id in member_ids:
        rsvp_repo.record_yes_if_first(
            outing_id,
            member_id,
        )

    #
    # Add guests:
    #
    # A +2
    # B +2
    # C +2
    # D +0
    #
    for sponsor_member_id in member_ids[:3]:

        for guest_num in range(2):

            guest_id = guest_repo.create_guest(
                {
                    "first_name": f"G{guest_num}",
                    "last_name": f"S{sponsor_member_id}",
                }
            )

            guest_repo.add_guest_to_outing(
                outing_id=outing_id,
                guest_id=guest_id,
                sponsoring_member_id=sponsor_member_id,
                status="yes",
            )

    #
    # Run scheduler
    #
    scheduling_service.generate_schedule(outing_id)

    #
    # Fetch assignments
    #
    assignments = outing_repo.get_assignments(outing_id)

    scheduled_member_ids = {int(row["member_id"]) for row in assignments}

    #
    # A + B + D scheduled
    #
    assert member_ids[0] in scheduled_member_ids
    assert member_ids[1] in scheduled_member_ids
    assert member_ids[3] in scheduled_member_ids

    #
    # C should NOT be scheduled
    #
    assert member_ids[2] not in scheduled_member_ids

    #
    # Verify no tee time exceeds expanded capacity
    #
    tee_times = outing_repo.get_tee_times(outing_id)

    for tee_time in tee_times:

        tee_time_id = int(tee_time["id"])

        expanded_size = outing_repo._guest_aware_tee_time_size(
            db.connect(),
            outing_id,
            tee_time_id,
        )

        assert expanded_size <= 4
