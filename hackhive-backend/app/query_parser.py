
import re


def parse_query(query: str) -> dict:
    """
    Convert a natural-language incident query into database filters.
    This parser uses rules only; it does not call an AI model.
    """
    text = query.lower().strip()

    filters = {
        "category": None,
        "review_status": None,
        "camera_id": None,
    }

    # Detect incident category.
    if any(term in text for term in [
        "crowd", "crowding", "gathering"
    ]):
        filters["category"] = "crowd_incident"

    elif any(term in text for term in [
        "person down", "person-down", "fallen person", "fall incident"
    ]):
        filters["category"] = "person_down"

    elif any(term in text for term in [
        "tailgating",
        "tailgate",
        "unauthorized entry",
        "unauthorised entry",
        "following someone through",
    ]):
        filters["category"] = "tailgating"

    # Detect review status.
    if any(term in text for term in [
        "unreviewed", "pending review", "needs review"
    ]):
        filters["review_status"] = "unreviewed"

    elif any(term in text for term in [
        "true positive", "confirmed incident"
    ]):
        filters["review_status"] = "true_positive"

    elif any(term in text for term in [
        "false positive", "false alarm"
    ]):
        filters["review_status"] = "false_positive"

    # Detect camera references such as "cam1", "camera 1",
    # or "camera_id cam1".
    match = re.search(
        r"\b(?:camera(?:_id)?|cam)[\s_-]*(\d+)\b",
        text,
    )

    if match:
        filters["camera_id"] = f"cam{match.group(1)}"

    return filters
