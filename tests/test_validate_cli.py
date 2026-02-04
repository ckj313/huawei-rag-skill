from pathlib import Path

from src.validate_cli import validate_plan


def test_validate_cli_missing_refs_fails():
    schema_path = Path(__file__).parent.parent / ".claude" / "skills" / "huawei-datacom-cli" / "schemas" / "cli_plan.schema.json"
    rules_path = Path(__file__).parent.parent / ".claude" / "skills" / "huawei-datacom-cli" / "rules" / "dangerous_commands.txt"
    plan = {
        "protocol": "ospf",
        "device": "usg-v8",
        "commands": [
            {"cmd": "ospf 1", "purpose": "create process", "refs": []}
        ],
        "missing_fields": []
    }
    errors = validate_plan(plan, schema_path, rules_path)
    assert any("refs" in e for e in errors)
