from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


def _load_schema(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _load_rules(rules_path: Path) -> list[re.Pattern]:
    patterns: list[re.Pattern] = []
    if not rules_path.exists():
        return patterns
    for line in rules_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(re.compile(line, re.IGNORECASE))
    return patterns


def validate_plan(plan: dict[str, Any], schema_path: Path, rules_path: Path) -> list[str]:
    errors: list[str] = []
    schema = _load_schema(schema_path)
    validator = Draft7Validator(schema)
    for err in sorted(validator.iter_errors(plan), key=str):
        errors.append(err.message)

    missing_fields = plan.get("missing_fields", [])
    commands = plan.get("commands", [])
    if missing_fields and commands:
        errors.append("missing_fields 不为空时 commands 必须为空")

    for idx, cmd in enumerate(commands):
        refs = cmd.get("refs", []) if isinstance(cmd, dict) else []
        if not refs:
            errors.append(f"commands[{idx}].refs 不能为空")

    patterns = _load_rules(rules_path)
    for idx, cmd in enumerate(commands):
        cmd_text = cmd.get("cmd", "") if isinstance(cmd, dict) else ""
        for pattern in patterns:
            if pattern.search(cmd_text):
                errors.append(f"命令触发禁用规则: commands[{idx}] '{cmd_text}'")
                break

    return errors
