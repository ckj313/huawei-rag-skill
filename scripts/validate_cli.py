from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.validate_cli import validate_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CLI plan JSON")
    parser.add_argument("--input", help="JSON file path (default: stdin)")
    parser.add_argument(
        "--schema",
        default=".claude/skills/huawei-datacom-cli/schemas/cli_plan.schema.json",
    )
    parser.add_argument(
        "--rules",
        default=".claude/skills/huawei-datacom-cli/rules/dangerous_commands.txt",
    )
    args = parser.parse_args()

    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        data = json.loads(sys.stdin.read())

    def _resolve(path_str: str) -> Path:
        path = Path(path_str).expanduser()
        return path if path.is_absolute() else ROOT / path

    errors = validate_plan(
        data,
        _resolve(args.schema),
        _resolve(args.rules),
    )
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "ok"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
