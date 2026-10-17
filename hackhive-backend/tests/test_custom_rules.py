import pytest

from app.custom_rules import parse_custom_rule


@pytest.mark.parametrize(
    "instruction",
    [
        "Alert me when a person enters the restricted zone.",
        "Notify me when someone walks into the restricted area.",
        "Alert when people step into the restricted region.",
    ],
)
def test_parse_supported_person_entry_rule(instruction):
    rule = parse_custom_rule(instruction)

    assert rule["event_type"] == "person_enters_zone"
    assert rule["region_id"] == "restricted_zone"
    assert rule["object_type"] == "person"
    assert rule["description"] == instruction
    assert rule["enabled"] is True


@pytest.mark.parametrize(
    "instruction",
    [
        "",
        "Alert me when a vehicle enters the restricted zone.",
        "Alert me when a person leaves the restricted zone.",
        "Alert me when a person enters the parking lot.",
    ],
)
def test_reject_unsupported_rule(instruction):
    with pytest.raises(ValueError):
        parse_custom_rule(instruction)
