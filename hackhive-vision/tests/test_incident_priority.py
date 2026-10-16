
from app.incident_priority import assign_priority
from app.schemas import Category, ConfidenceStatus


def test_person_down_is_high_even_when_unconfirmed():
    assert assign_priority(
        Category.PERSON_DOWN,
        ConfidenceStatus.NEEDS_REVIEW,
    ) == "HIGH"


def test_confirmed_crowd_incident_is_medium():
    assert assign_priority(
        Category.CROWD,
        ConfidenceStatus.CONFIRMED,
    ) == "MEDIUM"


def test_uncertain_tailgating_is_medium():
    assert assign_priority(
        Category.TAILGATING,
        ConfidenceStatus.RULE_ONLY,
    ) == "MEDIUM"


def test_unconfirmed_crowd_is_not_low():
    assert assign_priority(
        Category.CROWD,
        ConfidenceStatus.NEEDS_REVIEW,
    ) == "MEDIUM"
