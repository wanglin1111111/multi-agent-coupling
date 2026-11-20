# multi-agent-coupling

多智能体拆分判定与编排治理技能：拆不拆由任务耦合度决定，唯一硬判据是同任务复测差值。

一句话：**多智能体不是性能问题，是任务耦合度问题——子任务能否各自独立产出可检查的结果，决定协作是赚还是赔。**

## 证据底座

- 财务分析基准：四类多智能体架构比单 Agent 高 57%–80.8%
- PlanCraft 规划基准（顺序约束）：反而低 39%–70%
- 方向相反 → 不存在「多 Agent 更强」的统一答案；变量是耦合方式
- Anthropic 电商场景：单 Agent 循环 + Skills，避免共享实时状态在交接中稀释
- 约 45% 单 Agent 基线分界是拟合现象，不是可照搬阈值

## 解决什么

| 痛点 | 本技能的做法 |
|---|---|
| 「要不要搞多 Agent」拍脑袋 | 举证关：答不出可验证收益就先加工具/Skills/审查 |
| 先画架构图再找任务 | 三问耦合体检：任一不过留在单 Agent 循环 |
| 拆了之后好坏看不见 | 先建单 Agent 基线任务集（10-20 个固定输入与判定） |
| 交回一句「完成了」 | 交接契约五字段，缺一个退回 |
| 多 Agent 共享状态互相覆盖 | 共享状态只走任务输入或落盘产物，禁止上下文默契 |
| 加了审查 Agent 但只产出相似答案 | 审查必须引用证据/测试失败 |
| 收益说不清 | 同任务复测四数字（质量/耗时/资源/新增交接错误），盖不住成本就退回 |

## 安装

复制本目录到 `~/.agents/skills/`（或你的 Skill 加载路径）即可。

## 自检

```bash
python scripts/validate.py tests/sample_good.json   # 必须 exit 0
python scripts/validate.py tests/sample_bad.json    # 必须 exit 1

# 一行自验（正反向 + 退出码全覆盖，零依赖）
python tests/test_validate.py
```

## 结构

```
SKILL.md                              工作流入口（一条主线 + 7 步流程 + 8 条硬规则）
references/coupling-check.md          三问体检判据 + 反直觉证据 + 工作能拆≠会话适合拆
references/baseline-retest.md         基线任务集建设 + 四数字复测 + 数字边界
references/orchestration-contract.md  最小编排 + 交接契约模板 + 审查角色设计
references/gotchas.md                 架构图驱动/跨基准比百分比/相似审查幻觉/状态稀释
scripts/validate.py                   编排计划七维校验器（exit 0/1/2）
tests/sample_good.json                通过基准
tests/sample_bad.json                 拦截基准（三问不过仍拆/契约缺字段/上下文默契…）
docs/methodology.md                   方法论全文（奥卡姆剃刀提炼 + 8 分点 + 5 条行动指南）
```
