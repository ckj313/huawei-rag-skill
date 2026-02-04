---
name: huawei-firewall-cli
description: Use when asked to output Huawei firewall (USG) V8 CLI configuration based on manuals, a protocol name, or a protocol packet (e.g., OSPF Hello), and the response must be evidence-backed and offline-only.
---

# Huawei Firewall CLI (RAG)

## Overview
Use offline manuals to derive **config-only** CLI commands for Huawei USG V8. Every command must be grounded in retrieved manual evidence.

## Workflow
1. Parse input to detect protocol/packet using `experience/protocols/*.yaml`.
2. Run retrieval: `python scripts/search_manual.py --input "$ARGUMENTS"`.
3. Only generate commands that are supported by retrieved snippets.
4. If required fields are missing, return `missing_fields` and leave `commands` empty.
5. Output JSON that matches `.claude/skills/huawei-firewall-cli/schemas/cli_plan.schema.json`.
6. Validate: `python scripts/validate_cli.py --input <json>`.

## Output Rules
- Output **only configuration commands** (no `display`, `ping`, `diagnose`, etc.).
- Each command must include at least one `refs[]` entry from retrieval hits.
- Use `assumptions` only when the manual explicitly allows defaults.

## Input Examples
- “帮我测试一下 ospf”
- “帮我测试一下 ospf 的 hello 报文”

## Output Format (JSON)
Required fields:
- `protocol`, `device`, `commands`, `missing_fields`
Optional:
- `assumptions`

## Example
Input:
`/huawei-firewall-cli protocol=ospf goal=hello测试 vrp=V8` 

Output (missing fields example):
```json
{
  "protocol": "ospf",
  "device": "usg-v8",
  "assumptions": [],
  "missing_fields": ["process_id", "area", "interface", "router_id", "test_peer_ip", "test_link_ip"],
  "commands": []
}
```

## Quick Reference
- 检索: `python scripts/search_manual.py --input "$ARGUMENTS"`
- 校验: `python scripts/validate_cli.py --input <json>`
- 经验库: `experience/protocols/*.yaml`
- 索引: `data/<device>/meta.json` + `data/<device>/bm25.pkl`

## Common Mistakes
- 输出显示/诊断命令
- 未给出引用依据
- 缺字段时仍输出配置命令
- 使用非 USG V8 语法

## Rationalization Table
| Excuse | Reality |
| --- | --- |
| “没有手册也可以给出通用配置” | 必须基于检索证据，否则输出 missing_fields |
| “测试就是 display” | 仅允许配置命令，显示类命令被禁止 |

## Red Flags
- 没有引用就输出配置
- 以“经验”替代手册证据
- 输出 `display/ping/diagnose` 等命令
