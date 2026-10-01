"""Load and validate role/phase personalization configuration."""

from __future__ import annotations

import json
from pathlib import Path

from digest_engine.tagger import TAGS


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"


def _load_profile(path: Path, key: str) -> tuple[str, dict[str, float]]:
    with path.open(encoding="utf-8") as handle:
        profiles = json.load(handle)
    normalized = key.strip().lower().replace(" ", "_")
    if normalized not in profiles:
        options = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown profile '{key}'. Choose one of: {options}")
    profile = profiles[normalized]
    weights = profile["weights"]
    unknown = set(weights) - set(TAGS)
    if unknown:
        raise ValueError(f"Unknown tags in {path.name}: {sorted(unknown)}")
    return profile["display_name"], {tag: float(value) for tag, value in weights.items()}


def load_role_weights(role: str) -> tuple[str, dict[str, float]]:
    return _load_profile(CONFIG_DIR / "roles.json", role)


def load_phase_weights(phase: str) -> tuple[str, dict[str, float]]:
    return _load_profile(CONFIG_DIR / "phases.json", phase)
