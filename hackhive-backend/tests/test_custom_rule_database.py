from app.database import (
    init_db,
    create_custom_rule,
    get_custom_rule,
    list_custom_rules,
)


def test_create_and_retrieve_custom_rule(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    rule_data = {
        "description": "Alert me when a person enters the restricted zone.",
        "event_type": "person_enters_zone",
        "region_id": "restricted_zone",
        "object_type": "person",
        "enabled": True,
    }

    saved = create_custom_rule(rule_data, db_path)

    assert saved["rule_id"] is not None
    assert saved["description"] == rule_data["description"]
    assert saved["event_type"] == "person_enters_zone"
    assert saved["region_id"] == "restricted_zone"
    assert saved["object_type"] == "person"
    assert saved["enabled"] is True
    assert get_custom_rule(saved["rule_id"], db_path) == saved


def test_list_custom_rules_filters_enabled_status(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    rule_data = {
        "description": "Alert me when a person enters the restricted zone.",
        "event_type": "person_enters_zone",
        "region_id": "restricted_zone",
        "object_type": "person",
        "enabled": True,
    }

    create_custom_rule(rule_data, db_path)

    disabled_rule = {
        **rule_data,
        "description": "Disabled test rule",
        "enabled": False,
    }
    create_custom_rule(disabled_rule, db_path)

    assert len(list_custom_rules(enabled=True, db_path=db_path)) == 1
    assert len(list_custom_rules(enabled=False, db_path=db_path)) == 1
    assert len(list_custom_rules(db_path=db_path)) == 2
