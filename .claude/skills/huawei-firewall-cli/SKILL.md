---
name: huawei-firewall-cli
description: Use when asked to output Huawei V8 device CLI configuration (NE/USG) based on manuals, a protocol name, or a protocol packet (e.g., OSPF Hello), and the response must be evidence-backed and offline-only.
---

# Huawei V8 Device CLI (RAG)

## Overview
Use offline manuals to derive **config-only** CLI commands for Huawei V8 devices (for example `ne-v8`, `usg-v8`). Every command must be grounded in retrieved manual evidence.

## Workflow
1. Parse input to detect protocol/packet using `experience/protocols/*.yaml`.
2. Parse `device` from input arguments and run retrieval: `python scripts/search_manual.py --input "$ARGUMENTS" --device <device>`.
3. Parse retrieval JSON:
   - If `status == "missing_index"`: do not generate configuration yet; ask user for `manual_source_path`.
   - After user provides path, build index by source type:
     - CHM: `extract_chm.py -> html_to_md.py -> build_index.py`
     - HTML dir: `html_to_md.py -> build_index.py`
     - Markdown dir: `build_index.py`
   - Rerun retrieval after indexing.
4. Only generate commands that are supported by retrieved snippets when `status == "ok"`.
5. For any `placeholder_fields` returned by retrieval, emit placeholders in commands using `<param>` (e.g., `<process_id>`). Do **not** add these to `missing_fields`.
6. Output JSON that matches `.claude/skills/huawei-firewall-cli/schemas/cli_plan.schema.json`.
7. Validate: `python scripts/validate_cli.py --input <json>`.

## Output Rules
- Output **only configuration commands** (no `display`, `ping`, `diagnose`, etc.).
- Each command must include at least one `refs[]` entry from retrieval hits.
- Use `assumptions` only when the manual explicitly allows defaults.
- `missing_fields` is only for truly unknown inputs (e.g., protocol/device/goal ambiguous or no evidence). It must **not** contain placeholder fields.
- If retrieval returns `status == "missing_index"`, ask for manual path first and build index before generating any commands.

## Input Examples
- “帮我测试一下 ospf”
- “帮我测试一下 ospf 的 hello 报文”
- “protocol=ospf packet=hello device=ne-v8 vrp=V8”

## Output Format (JSON)
Required fields:
- `protocol`, `device`, `commands`, `missing_fields`
Optional:
- `assumptions`

## Example
Input:
`/huawei-firewall-cli protocol=ospf goal=hello测试 device=ne-v8 vrp=V8` 

Output (placeholder example):
```json
{
  "protocol": "ospf",
  "device": "ne-v8",
  "assumptions": [],
  "missing_fields": [],
  "commands": [
    {
      "cmd": "ospf <process_id>",
      "purpose": "创建 OSPF 进程",
      "refs": [{"source": "<manual>.md", "section": "<section>", "title": "<title>"}]
    },
    {
      "cmd": "area <area>",
      "purpose": "进入 OSPF 区域",
      "refs": [{"source": "<manual>.md", "section": "<section>", "title": "<title>"}]
    },
    {
      "cmd": "interface <interface>",
      "purpose": "进入接口视图",
      "refs": [{"source": "<manual>.md", "section": "<section>", "title": "<title>"}]
    },
    {
      "cmd": "ospf timer hello <hello_interval>",
      "purpose": "设置 Hello 报文间隔",
      "refs": [{"source": "<manual>.md", "section": "<section>", "title": "<title>"}]
    }
  ]
}
```

## Quick Reference
- 检索: `python scripts/search_manual.py --input "$ARGUMENTS" --device <ne-v8|usg-v8>`
- CHM 解包: `python scripts/extract_chm.py --input <manual.chm> --out manuals/<device>/html`
- HTML 转 MD: `python scripts/html_to_md.py --input <html_dir> --out manuals/<device>/md`
- 构建索引: `python scripts/build_index.py --manual manuals/<device>/md --out data/<device>`
- 校验: `python scripts/validate_cli.py --input <json>`
- 经验库: `experience/protocols/*.yaml`
- 索引: `data/<device>/meta.json` + `data/<device>/bm25.pkl`

## Common Mistakes
- 输出显示/诊断命令
- 未给出引用依据
- 未使用 `<param>` 占位符而直接臆造参数
- 未传入 `device` 导致设备语法不匹配

## Rationalization Table
| Excuse | Reality |
| --- | --- |
| “没有手册也可以给出通用配置” | 必须基于检索证据，否则输出 missing_fields |
| “测试就是 display” | 仅允许配置命令，显示类命令被禁止 |

## Red Flags
- 没有引用就输出配置
- 以“经验”替代手册证据
- 输出 `display/ping/diagnose` 等命令
