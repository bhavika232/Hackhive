
import re

SUPPORTED_RULE = {
    "event_type": "person_enters_zone",
    "region_id": "restricted_zone",
    "object_type": "person",
}


def parse_custom_rule(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Please enter an alert instruction.")

    normalized = re.sub(r"\s+", " ", text.strip().lower())

    person_patterns = [
        r"\bperson\b",
        r"\bpeople\b",
        r"\bsomeone\b",
        r"\banyone\b",
        r"\bindividual\b",
    ]

    entry_patterns = [
        r"\benters?\b",
        r"\bentering\b",
        r"\bgoes? into\b",
        r"\bwalks? into\b",
        r"\bsteps? into\b",
    ]

    zone_patterns = [
        r"\brestricted zone\b",
        r"\brestricted area\b",
        r"\brestricted region\b",
    ]

    has_person = any(re.search(p, normalized) for p in person_patterns)
    has_entry = any(re.search(p, normalized) for p in entry_patterns)
    has_zone = any(re.search(p, normalized) for p in zone_patterns)

    if has_person and has_entry and has_zone:
        return {
            **SUPPORTED_RULE,
            "description": text.strip(),
            "enabled": True,
        }

    raise ValueError(
        "Unsupported instruction. Try: "
        "'Alert me when a person enters the restricted zone.'"
    )
