#!/usr/bin/env python3
"""validate.py — multi-agent-coupling 编排计划七维校验器

输入: 编排计划 JSON（schema 见 tests/sample_good.json）
  {
    "baseline": {
      "task_count": 15,                       # 基线任务数 10-20
      "metrics": ["success_rate", "duration", "call_volume", "typical_errors"]
    },
    "tasks": [
      {
        "id": "TASK-1",
        "check": {                            # 三问体检
          "start_without_others": true,       # Q1 不看别人中间状态能否开工
          "independently_checkable": true,    # Q2 是否独立可验收产物
          "no_shared_state_mutation": true    # Q3 中途是否改别人状态(true=不改)
        },
        "decision": "split",                  # split | keep_single
        "contract": {                         # decision=split 时必填五字段
          "problem": "...",
          "inputs_tools": "...",
          "deliverable": "...",
          "stop_condition": "...",
          "return_fields": ["conclusion", "evidence", "open_questions"]
        },
        "shared_state_via": "task_input",     # task_input | persisted_artifact | context(禁止)
        "reviewer": "evidence_based"          # evidence_based | similarity(禁止) | none(禁止)
      }
    ],
    "retest": {                               # 存在 split 时必填
      "metrics": ["quality", "time", "resource", "handoff_errors"]
    }
  }

七维校验（任一 FAIL → exit 1）：
  D1 基线纪律: baseline.task_count ∈ [10,20]；metrics 四项齐全
     （成功率/耗时/调用量/典型错误）——无基线不判拆
  D2 三问一致性: check 三问任一为 false 且 decision==split → FAIL（三问不过不拆）
  D3 契约完整: decision==split 时 contract 五字段非空，return_fields ≥3 且全非空
  D4 共享状态通道: shared_state_via ∈ {task_input, persisted_artifact}；
     context（上下文默契）= FAIL
  D5 审查纪律: decision==split 时 reviewer 必须为 evidence_based
     （similarity=相似审查幻觉，none=无审查）
  D6 复测纪律: 存在任何 split 时 retest.metrics 四项齐全
     （质量/耗时/资源/新增交接错误）；无 split 豁免
  D7 决策合法: decision ∈ {split, keep_single}，check 三键齐全且为布尔

退出码：0=通过 / 1=有缺陷 / 2=文件/格式错误
"""
import json
import sys

BASELINE_METRICS = {"success_rate", "duration", "call_volume", "typical_errors"}
RETEST_METRICS = {"quality", "time", "resource", "handoff_errors"}
CHECK_KEYS = {"start_without_others", "independently_checkable", "no_shared_state_mutation"}
CONTRACT_FIELDS = ("problem", "inputs_tools", "deliverable", "stop_condition", "return_fields")
DECISIONS = {"split", "keep_single"}
STATE_VIA = {"task_input", "persisted_artifact"}


def fail(checks, code, msg):
    checks.append(("FAIL", code, msg))


def ok(checks, code, msg):
    checks.append(("OK", code, msg))


def validate(plan):
    checks = []
    tasks = plan.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        fail(checks, "D0", "tasks 必须是非空数组")
        return checks

    # D1 基线纪律
    base = plan.get("baseline") or {}
    n = base.get("task_count")
    if not isinstance(n, int) or n < 10 or n > 20:
        fail(checks, "D1", f"baseline.task_count={n!r}——基线任务集须 10-20 个")
    else:
        ok(checks, "D1", f"基线任务数 {n}")
    bmetrics = set(base.get("metrics") or [])
    missing = BASELINE_METRICS - bmetrics
    if missing:
        fail(checks, "D1", f"baseline.metrics 缺失: {sorted(missing)}——无基线四数字不判拆")
    else:
        ok(checks, "D1", "基线四指标齐全")

    has_split = False
    for i, t in enumerate(tasks):
        where = f"tasks[{i}]({t.get('id', '?')})"

        # D7 决策合法
        dec = t.get("decision")
        if dec not in DECISIONS:
            fail(checks, "D7", f"{where}: decision 非法: {dec!r}（须为 split/keep_single）")
            continue
        chk = t.get("check") or {}
        if set(chk.keys()) != CHECK_KEYS or not all(isinstance(v, bool) for v in chk.values()):
            fail(checks, "D7", f"{where}: check 三问须齐全且为布尔: {chk!r}")
            continue
        ok(checks, "D7", f"{where}: decision={dec}")

        if dec == "split":
            has_split = True
            # D2 三问一致性
            bad_q = sorted(k for k, v in chk.items() if v is False)
            if bad_q:
                fail(checks, "D2", f"{where}: 三问不过 {bad_q} 仍判 split——留在同一 Agent 循环，别拆")
            else:
                ok(checks, "D2", f"{where}: 三问全过，允许拆")
            # D3 契约完整
            contract = t.get("contract") or {}
            for f in CONTRACT_FIELDS:
                v = contract.get(f)
                if f == "return_fields":
                    if not isinstance(v, list) or len(v) < 3 or not all(str(x).strip() for x in v):
                        fail(checks, "D3", f"{where}: contract.return_fields 须 ≥3 个非空字段")
                elif not str(v or "").strip():
                    fail(checks, "D3", f"{where}: contract.{f} 缺失——交回'完成了'=不合格")
            else:
                ok(checks, "D3", f"{where}: 契约五字段齐全")
            # D4 共享状态通道
            via = t.get("shared_state_via")
            if via == "context":
                fail(checks, "D4", f"{where}: shared_state_via=context——禁止上下文默契，走任务输入或落盘产物")
            elif via not in STATE_VIA:
                fail(checks, "D4", f"{where}: shared_state_via 非法: {via!r}")
            else:
                ok(checks, "D4", f"{where}: 共享状态通道 {via}")
            # D5 审查纪律
            rev = t.get("reviewer")
            if rev == "similarity":
                fail(checks, "D5", f"{where}: reviewer=similarity——相似审查=幻觉，须 evidence_based（引用证据/测试失败）")
            elif rev == "none":
                fail(checks, "D5", f"{where}: reviewer=none——split 任务无审查角色，不合格")
            elif rev != "evidence_based":
                fail(checks, "D5", f"{where}: reviewer 非法: {rev!r}")
            else:
                ok(checks, "D5", f"{where}: 审查=证据")
        else:
            ok(checks, "D2", f"{where}: keep_single，D2-D5 豁免")

    # D6 复测纪律
    if has_split:
        rmetrics = set((plan.get("retest") or {}).get("metrics") or [])
        missing = RETEST_METRICS - rmetrics
        if missing:
            fail(checks, "D6", f"存在 split 但 retest.metrics 缺失: {sorted(missing)}——四数字复测不可省")
        else:
            ok(checks, "D6", "复测四指标齐全")
    else:
        ok(checks, "D6", "无 split，复测豁免")

    return checks


def main():
    if len(sys.argv) != 2:
        print("usage: python validate.py plan.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: 无法读取/解析: {e}", file=sys.stderr)
        return 2
    if not isinstance(plan, dict):
        print("ERROR: 顶层必须是 JSON 对象", file=sys.stderr)
        return 2

    checks = validate(plan)
    fails = [c for c in checks if c[0] == "FAIL"]
    for status, code, msg in checks:
        if status == "FAIL":
            print(f"[{code}] FAIL {msg}")
    print(f"== {len(checks) - len(fails)} OK / {len(fails)} FAIL ==")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
