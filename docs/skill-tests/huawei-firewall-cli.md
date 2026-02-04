# Skill TDD - huawei-firewall-cli

## Baseline (no skill)

### 场景 A
- 输入: “帮我测试一下 ospf”
- 压力: 仅输出可下发配置、无手册引用、设备为华为防火墙 V8、需要与测试仪交互
- 观察到的典型行为 (无技能):
  - 给出泛化 OSPF 配置/显示命令混杂 (如 `display ospf peer`)
  - 未要求关键参数 (接口/area/process-id/router-id/测试仪对端地址)
  - 未提供任何依据引用
  - 可能使用非防火墙或非 VRP V8 语法

### 场景 B
- 输入: “帮我测试一下 ospf 的 hello 报文”
- 压力: 只输出可下发配置，必须基于手册证据
- 观察到的典型行为 (无技能):
  - 把“报文测试”当作抓包/显示命令处理
  - 忽略与测试仪交互所需的邻接/接口配置
  - 未声明缺失字段，直接臆造默认值

## 失败模式总结
- 不输出引用依据
- 输出非配置命令或不允许的显示/抓包命令
- 忽略缺失字段与最小追问
- 语法/视图不确定但未标注假设


## With Skill (expected behavior)

### 场景 A
- 期望行为:
  - 先检索 `scripts/search_manual.py` 获取 OSPF 片段
  - 仅在证据支持时输出配置命令，并为每条命令附 `refs`
  - 对 `placeholder_fields` 使用 `<param>` 占位符，不再输出 `missing_fields`

### 场景 B
- 期望行为:
  - 识别为 OSPF Hello 报文场景
  - 仍然以 OSPF 基本/接口配置为主，输出配置命令或缺失字段
  - 不输出 display/diagnose/ping 等非配置命令

## 新增合理化与反制
- 合理化: “hello 报文测试需要抓包/显示命令”
  - 反制: 明确禁止 display/diagnose/ping，且只允许配置命令
- 合理化: “没有输入参数就必须停下来”
  - 反制: 对 `placeholder_fields` 使用 `<param>` 占位符继续输出配置
