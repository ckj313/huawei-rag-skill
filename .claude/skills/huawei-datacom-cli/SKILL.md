---
name: huawei-datacom-cli
description: Use when asked to output Huawei datacom device CLI configuration (NE/CE/AE/LSW/USG) based on manuals, a protocol name, or a protocol packet (e.g., OSPF Hello), and the response must be evidence-backed and offline-only.
---

# Huawei Datacom Device CLI (RAG)

## Overview
Use offline manuals to derive **config-only** CLI commands for Huawei datacom devices (for example `ne`, `ce`, `ae`, `lsw`, `usg`). Every command must be grounded in retrieved manual evidence.

## Hard Constraints
- Never create, edit, or auto-complete files under `experience/`.
- Treat `experience/` as user-maintained knowledge only.
- If protocol/packet details are missing from `experience/`, continue with raw user query + manual retrieval, or ask the user for clarification.
- When index/manual is missing, ask user for manual path and build index first; do not "fix" by editing `experience/`.

## Script Path Rule
- Always resolve repo root first:
  - `REPO_ROOT="$(git rev-parse --show-toplevel)"`
- Then run scripts via absolute repo path, for example:
  - `python "$REPO_ROOT/scripts/search_manual.py" ...`

## Workflow
1. Parse input to detect protocol/packet using `experience/protocols/*.yaml`.
2. Parse `device` from input arguments and run retrieval: `python "$REPO_ROOT/scripts/search_manual.py" --input "$ARGUMENTS" --device <device>`.
3. Parse retrieval JSON:
   - If command exits non-zero OR `must_stop == true`: stop command generation immediately.
   - If `status == "missing_device"`: ask user to specify `device` first.
   - If `status == "missing_index"`: ask user for `manual_source_path` first.
   - After user provides path, build index by source type:
     - CHM: `chm_to_index.py`（若提示缺少 `extract_chmLib`，先用系统包管理器安装后重试）
     - HTML dir: `html_to_md.py -> build_index.py`
     - Markdown dir: `build_index.py`
   - Rerun retrieval after indexing.
4. Only generate commands when retrieval returns `status == "ok"` and `can_generate_config == true`.
5. For any `placeholder_fields` returned by retrieval in `status == "ok"`, emit placeholders in commands using `<param>` (e.g., `<process_id>`). Do **not** add these to `missing_fields`.
6. Build an internal JSON plan that matches `.claude/skills/huawei-datacom-cli/schemas/cli_plan.schema.json`.
7. Validate internal JSON: `python "$REPO_ROOT/scripts/validate_cli.py" --input <json> --delete-input`.
8. If validation is `ok`, render user-facing output as **one single CLI block** (not multiple方案, not JSON dump).

## Output Rules
- Output **only configuration commands** (no `display`, `ping`, `diagnose`, etc.).
- Each command must include at least one `refs[]` entry from retrieval hits.
- Use `assumptions` only when the manual explicitly allows defaults.
- `missing_fields` is only for truly unknown inputs (e.g., protocol/device/goal ambiguous or no evidence). It must **not** contain placeholder fields.
- If retrieval returns `status == "missing_index"`, do not output any configuration example; ask user for manual path first and build index before generating commands.
- If retrieval returns `status == "missing_index"`, `placeholder_fields` is not actionable and must not be used to synthesize commands.
- If retrieval returns `status == "missing_device"`, do not output configuration; request `device` first.
- In `missing_index`/`missing_device` cases: do not create any JSON plan file, do not run `validate_cli.py`.
- For one request, output exactly one final configuration set. Never output multiple基础配置/候选方案.
- Do not expose internal JSON unless user explicitly asks for JSON.
- If a temporary JSON file is created for validation, it must be deleted immediately after validation.

## Stop-First Reply Templates
- Missing device reply (only ask question, no config):
  - `未检测到设备类型，请先提供 device（ne/ce/ae/lsw/usg）。`
- Missing index reply (only ask path + command, no config):
  - `当前未找到 <device> 的RAG索引，请提供手册CHM路径（或HTML/Markdown目录）以先建库。`
  - `CHM一键建库命令：python "$REPO_ROOT/scripts/chm_to_index.py" --input <manual.chm> --device <device>`

## Input Examples
- “帮我测试一下 ospf”
- “帮我测试一下 ospf 的 hello 报文”
- “我需要测试一下 ospf 协议，给我一下 usg 设备配置 ospf 的命令行”
- “我需要测试一下 ospf 协议，给我一下 ne 设备配置 ospf 的命令行”
- “protocol=ospf packet=hello device=ne vrp=V8”
- “protocol=ospf device=ce vrp=V8”
- “protocol=ospf packet=hello device=ae vrp=V8”
- “protocol=ospf device=lsw vrp=V8”
- “protocol=ospf packet=hello device=usg vrp=V8”

## Output Format (JSON)
Required fields:
- `protocol`, `device`, `commands`, `missing_fields`
Optional:
- `assumptions`

## User-Facing Output Format
After internal JSON validation succeeds, output in this shape:

- `已按 huawei-datacom-cli 的规则生成并校验（validate_cli.py 返回 ok）。`
- `下面是 OSPF 配置命令（占位符版）：`
```cli
<single config block>
```

If `device=usg` and `protocol=ospf`, prefer this canonical style:
```cli
system-view

ospf <process_id> router-id <router_id>
 area <area>
  network <test_link_ip> 0.0.0.0
 quit
quit

interface <interface>
 ospf enable <process_id> area <area>
quit

security-policy
 rule name policy_ospf
  source-zone trust
  destination-zone local
  source-address <test_peer_ip> 32
  service ospf
  action permit
 quit
quit
```

For `ne`/`ce`/`ae`/`lsw`, prefer a routing-device style without `security-policy` unless retrieval evidence explicitly requires it.

## Quick Reference
- 检索: `python "$REPO_ROOT/scripts/search_manual.py" --input "$ARGUMENTS" --device <ne|ce|ae|lsw|usg>`
- CHM 一键建索引: `python "$REPO_ROOT/scripts/chm_to_index.py" --input ~/Downloads/HUAWEI_usg.chm --device usg`
- 缺少 `extract_chmLib` 时先安装（由模型执行命令）:
  - macOS: `brew install chmlib`
  - Debian/Ubuntu: `sudo apt-get -y install chmlib-tools`
  - RHEL/CentOS: `sudo yum -y install chmlib`
  - Fedora: `sudo dnf -y install chmlib`
  - Arch: `sudo pacman -S --noconfirm chmlib`
  - openSUSE: `sudo zypper -n install chmlib`
- HTML 转 MD: `python "$REPO_ROOT/scripts/html_to_md.py" --input <html_dir> --out manuals/<device>/md`
- 构建索引(从MD): `python "$REPO_ROOT/scripts/build_index.py" --manual manuals/<device>/md --out data/<device>`
- 校验并自动清理临时JSON: `python "$REPO_ROOT/scripts/validate_cli.py" --input <json> --delete-input`
- 经验库: `experience/protocols/*.yaml`
- 索引: `data/<device>/meta.json` + `data/<device>/bm25.pkl`

## Common Mistakes
- 输出显示/诊断命令
- 未给出引用依据
- 未使用 `<param>` 占位符而直接臆造参数
- 未传入 `device` 导致设备语法不匹配
- 自动修改 `experience/` 试图“补齐协议知识”

## Rationalization Table
| Excuse | Reality |
| --- | --- |
| “没有手册也可以给出通用配置” | 必须基于检索证据，否则输出 missing_fields |
| “测试就是 display” | 仅允许配置命令，显示类命令被禁止 |

## Red Flags
- 没有引用就输出配置
- 以“经验”替代手册证据
- 输出 `display/ping/diagnose` 等命令
