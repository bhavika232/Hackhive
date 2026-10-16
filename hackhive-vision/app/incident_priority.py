
from app.schemas import Category, ConfidenceStatus


def assign_priority(
    category: Category,
    confidence_status: ConfidenceStatus,
) -> str:
    """Assign an operational priority to an incident."""

    # A possible person-down event needs urgent review,
    # even if the VLM cannot confirm it.
    if category == Category.PERSON_DOWN:
        return "HIGH"

    # Confirmed crowd and tailgating incidents need attention.
    if confidence_status == ConfidenceStatus.CONFIRMED:
        return "MEDIUM"

    # Uncertain incidents must not be dismissed as low risk.
    if confidence_status in (
        ConfidenceStatus.RULE_ONLY,
        ConfidenceStatus.NEEDS_REVIEW,
    ):
        return "MEDIUM"

    # Safe fallback for unexpected inputs.
    return "LOW"
