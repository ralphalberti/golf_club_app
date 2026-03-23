from app.utils import build_tee_times

def test_build_tee_times():
    assert build_tee_times("10:00", 9, 3) == ["10:00", "10:09", "10:18"]
