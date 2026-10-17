
from app.event_memory import EventMemory
from app.schemas import Category, ConfidenceStatus, EventCandidate


def make_event(t: float, track_id: int = 1) -> EventCandidate:
    return EventCandidate(
        camera_id="cam1",
        category=Category.PERSON_DOWN,
        start_video_time_s=t,
        summary="Person down",
        confidence=0.9,
        confidence_status=ConfidenceStatus.CONFIRMED,
        keyframe_path=f"frame_{t}.jpg",
        track_ids=[track_id],
    )


def test_repeated_event_updates_existing_memory():
    memory = EventMemory(gap_seconds=10)

    memory.add_event(make_event(10))
    memory.add_event(make_event(15))

    assert len(memory.active_events) == 1
    event = next(iter(memory.active_events.values()))
    assert event.start_video_time_s == 10
    assert event.end_video_time_s == 15
    assert len(memory.completed_events) == 0

def test_different_tracks_create_separate_events():
    memory = EventMemory(gap_seconds=10)

    memory.add_event(make_event(10, track_id=1))
    memory.add_event(make_event(12, track_id=2))

    assert len(memory.active_events) == 2
def test_quiet_event_moves_to_completed():
    memory = EventMemory(gap_seconds=10)

    memory.add_event(make_event(10))
    memory.flush(current_time_s=21)

    assert len(memory.active_events) == 0
    assert len(memory.completed_events) == 1
    assert memory.completed_events[0].start_video_time_s == 10