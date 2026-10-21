"""Shared pose-reference vocabulary for public photo discovery and human review.

These fields describe requested camera coverage, NOT automatically verified poses,
species, sex, rights, image-generation readiness, or actual animal behaviour.
Public research has no private card IDs.
"""
from __future__ import annotations
import re

CORE_POSES = (
    "FRONTAL", "WALKING_AWAY_REAR_OBLIQUE", "LATERAL_PROFILE",
    "OBLIQUE_THREE_QUARTER", "DORSAL_TOP_DOWN", "POSTERIOR",
)
OPTIONAL_POSES = (
    "ELEVATED_ALERT", "DEFENSIVE_THREAT", "VENTRAL_UNDERSIDE", "VERTICAL_CLIMB",
)
ALL_POSES = CORE_POSES + OPTIONAL_POSES
UNKNOWN_POSE = "UNREVIEWED"
POSE_LABELS = {
    "FRONTAL": "Frontal / eye-level",
    "WALKING_AWAY_REAR_OBLIQUE": "Walking away / rear three-quarter",
    "LATERAL_PROFILE": "Lateral / side profile",
    "OBLIQUE_THREE_QUARTER": "Front oblique / three-quarter",
    "DORSAL_TOP_DOWN": "Dorsal / top-down",
    "POSTERIOR": "Direct rear / posterior",
    "ELEVATED_ALERT": "Alert / raised stance",
    "DEFENSIVE_THREAT": "Defensive threat display",
    "VENTRAL_UNDERSIDE": "Ventral / underside",
    "VERTICAL_CLIMB": "Vertical climbing / trunk",
}
# These are OPTIONAL search hints in untrusted observer prose.
# Even a match is not evidence that any photograph shows that pose.
TEXT_CUES = {
    "FRONTAL": r"\b(?:front(?:al)?\s+(?:view|shot|photo)|face[- ]on|head[- ]on)\b",
    "WALKING_AWAY_REAR_OBLIQUE": r"\b(?:walking away|rear three[- ]quarter)\b",
    "LATERAL_PROFILE": r"\b(?:side[- ]view|side profile|lateral view)\b",
    "OBLIQUE_THREE_QUARTER": r"\b(?:oblique view|three[- ]quarter view)\b",
    "DORSAL_TOP_DOWN": r"\b(?:top[- ]down|dorsal view|viewed from above)\b",
    "POSTERIOR": r"\b(?:rear view|posterior view|back view)\b",
    "ELEVATED_ALERT": r"\b(?:alert posture|raised stance|body raised)\b",
    "DEFENSIVE_THREAT": r"\b(?:threat pose|defensive posture|threat display)\b",
    "VENTRAL_UNDERSIDE": r"\b(?:ventral view|underside view|viewed from below)\b",
    "VERTICAL_CLIMB": r"\b(?:climbing(?: on)? (?:a )?(?:tree|trunk|bark)|vertical trunk)\b",
}

def unverified_text_pose_hints(description: str) -> list[str]:
    if not isinstance(description, str):
        return []
    value = description[:1000].casefold()
    return [pose for pose, cue in TEXT_CUES.items() if re.search(cue, value, re.I)]

def research_needs() -> dict:
    # Zero confirmed by design: public candidate metadata cannot see verified
    # sex, camera angle or whether a view is suitable to the focal species.
    return {
        "schema": "VNMV1_CAMERA_VIEW_RESEARCH_NEEDS_V1",
        "core_targets": list(CORE_POSES),
        "optional_species_dependent_targets": list(OPTIONAL_POSES),
        "visually_verified_pose_coverage": [],
        "pose_coverage_status": "UNKNOWN_UNTIL_INDEPENDENT_IMAGE_REVIEW",
        "photo_count_is_not_pose_coverage": True,
        "no_forced_threat_or_ventral_view": True,
    }
