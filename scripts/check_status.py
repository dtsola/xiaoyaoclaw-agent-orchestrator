# -*- coding: utf-8 -*-
"""解析 sessions_list 输出，汇总子任务状态（零 token 确定性操作）。

用法:
    python check_status.py <sessions_list_json_file> [--task KEY...] [--json]

说明:
    - 输入：sessions_list 工具的输出 JSON（保存到文件后传入）
    - 也可从 stdin 读取：cat sessions.json | python check_status.py -
    - 输出：每会话一行（key / kind / updatedAt / 状态判定）
    - 状态判定规则：
        [DONE]    最后一条消息含 [DONE] 标记（对方显式完成）
        [FAILED]  最后一条消息含 [FAILED] 标记（对方显式失败）
        [RUNNING] updatedAt 在 recent_minutes 内（默认 10 分钟）且有活动
        [STALE]   updatedAt 超过 recent_minutes（疑似卡住/超时，需人工查 history）
        [IDLE]    无消息历史
    - 只读分析，零外部依赖，Windows / macOS 双平台通用

示例:
    python check_status.py sessions.json
    python check_status.py sessions.json --task agent:xiaoguang:direct:ou_xxx
    python check_status.py sessions.json --recent-minutes 15 --json
"""
import argparse
import json
import sys
import time

DONE_MARK = "[DONE]"
FAILED_MARK = "[FAILED]"


def extract_messages_text(messages):
    """从 sessions_list 输出中提取最后一条 agent/assistant 文本。"""
    if not messages:
        return ""
    for m in reversed(messages):
        role = m.get("role", "")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def judge(session, recent_minutes):
    """判定单会话状态。"""
    messages = session.get("messages") or []
    last_text = extract_messages_text(messages)
    updated = session.get("updatedAt") or 0
    now_ms = time.time() * 1000
    fresh = (now_ms - updated) < recent_minutes * 60 * 1000

    if DONE_MARK in last_text:
        return "DONE", last_text[-200:]
    if FAILED_MARK in last_text:
        return "FAILED", last_text[-200:]
    if updated and fresh:
        return "RUNNING", last_text[-200:]
    if updated:
        return "STALE", last_text[-200:]
    return "IDLE", ""


def main():
    ap = argparse.ArgumentParser(description="Summarize sub-task status from sessions_list output")
    ap.add_argument("input", help="sessions_list JSON 文件，或 - 读 stdin")
    ap.add_argument("--task", action="append", default=None,
                    help="只显示指定 sessionKey（可多次）")
    ap.add_argument("--recent-minutes", type=int, default=10,
                    help="RUNNING 判定窗口（默认 10 分钟）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        with open(args.input, "r", encoding="utf-8-sig") as f:
            raw = f.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[FAIL] invalid JSON: {e}")
        sys.exit(1)

    sessions = data if isinstance(data, list) else data.get("sessions") or data.get("items") or []
    if not isinstance(sessions, list):
        print("[FAIL] cannot find session list in input")
        sys.exit(1)

    task_filter = set(args.task or [])
    rows = []
    for s in sessions:
        key = s.get("key") or s.get("sessionKey") or ""
        if task_filter and key not in task_filter:
            continue
        status, tail = judge(s, args.recent_minutes)
        updated = s.get("updatedAt") or 0
        age_min = int((time.time() * 1000 - updated) / 60000) if updated else -1
        rows.append({
            "key": key,
            "kind": s.get("kind", ""),
            "updatedAgeMin": age_min,
            "status": status,
            "tail": tail,
        })

    if args.json:
        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"[{r['status']:7s}] {r['key']}  (updated {r['updatedAgeMin']}m ago)")
            if r["tail"]:
                print(f"         {r['tail']}")
        if not rows:
            print("(no matching sessions)")

    failed = [r for r in rows if r["status"] == "FAILED"]
    sys.exit(2 if failed else 0)


if __name__ == "__main__":
    main()
