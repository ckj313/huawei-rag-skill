---
name: pageindex-retrieve
description: Use when local manual retrieval needs VectifyAI/PageIndex tree build and script-driven search without function-calling APIs.
---

# PageIndex Retrieve

按以下顺序执行：
1. `tools/pageindex_build.py`（若 tree 缺失）
2. `tools/pageindex_search.py`
3. 读取 `artifacts/pageindex_results*.json` 并生成 evidence blocks

## Build（CHM）
```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
python "$REPO_ROOT/tools/pageindex_build.py" \
  --chm-file ~/Downloads/HUAWEI_usg.chm \
  --out "$REPO_ROOT/artifacts/pageindex_build.json"
```

## Search（ISIS）
```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
python "$REPO_ROOT/tools/pageindex_search.py" \
  --tree-dir "$REPO_ROOT/data/pageindex/huawei_usg" \
  --query "USG ISIS 命令 isis enable network-entity isis process is-level" \
  --topk 8 \
  --out "$REPO_ROOT/artifacts/pageindex_results_isis.json"
```

## Evidence 规则
- 必须只使用 `hits[]` 生成证据块。
- `hits` 为空时停止命令生成，提示用户缩小 query 或确认手册来源。
