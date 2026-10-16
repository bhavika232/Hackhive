
from app.query_parser import parse_query


def test_parse_crowd_query():
    result = parse_query("Show all crowd incidents")

    assert result["category"] == "crowd_incident"
    assert result["review_status"] is None
    assert result["camera_id"] is None


def test_parse_person_down_query():
    result = parse_query("Find person-down incidents")

    assert result["category"] == "person_down"


def test_parse_combined_filters():
    result = parse_query(
        "Show unreviewed crowd incidents from camera 1"
    )

    assert result == {
        "category": "crowd_incident",
        "review_status": "unreviewed",
        "camera_id": "cam1",
    }


def test_parse_false_positive_query():
    result = parse_query("Show false alarms")

    assert result["review_status"] == "false_positive"


def test_parse_empty_query():
    result = parse_query("")

    assert result == {
        "category": None,
        "review_status": None,
        "camera_id": None,
    }


def test_parse_camera_reference():
    result = parse_query("Show incidents from camera 2")
    assert result["camera_id"] == "cam2"


def test_parse_unrecognized_query_has_no_filters():
    result = parse_query("show me something completely unrelated")
    assert result == {
        "category": None,
        "review_status": None,
        "camera_id": None,
    }


def test_parse_query_is_case_insensitive():
    result = parse_query("SHOW CROWD INCIDENTS FROM CAMERA 3")
    assert result["category"] == "crowd_incident"
    assert result["camera_id"] == "cam3"


def test_parse_false_alarm():
    result = parse_query("show false alarms")
    assert result["review_status"] == "false_positive"
