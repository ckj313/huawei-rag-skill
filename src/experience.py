from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def load_protocol_profiles(base_dir: Path) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(base_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        protocol = data.get("protocol")
        if not protocol:
            continue
        profiles[protocol.lower()] = data
    return profiles


def detect_intent(text: str, profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    norm_text = _norm(text)
    selected_protocol = None
    selected_profile: dict[str, Any] | None = None
    selected_alias_len = -1

    for protocol, profile in profiles.items():
        aliases = profile.get("aliases", []) + [protocol]
        for alias in aliases:
            if not alias:
                continue
            if _norm(alias) in norm_text and len(alias) > selected_alias_len:
                selected_protocol = protocol
                selected_profile = profile
                selected_alias_len = len(alias)

    packet = None
    if selected_profile:
        packet_types = selected_profile.get("packet_types", {})
        for packet_name, packet_info in packet_types.items():
            for alias in packet_info.get("aliases", []):
                if _norm(alias) in norm_text:
                    packet = packet_name
                    break
            if packet:
                break

    required_fields = []
    if selected_profile:
        required_fields = list(selected_profile.get("required_fields", []))

    return {
        "protocol": selected_protocol,
        "packet": packet,
        "required_fields": required_fields,
        "profile": selected_profile,
    }
