# -*- coding: utf-8 -*-
"""检测 openclaw.json 多 agent 协作配置，输出状态报告。

用法:
    python check_config.py [--config PATH] [--json]

说明:
    - 定位 openclaw.json：--config 指定 > OPENCLAW_CONFIG_PATH 环境变量 > 默认路径
    - 检查项：
        1. agents.list 存在且含哪些 agent
        2. tools.agentToAgent.enabled
        3. tools.sessions.visibility（跨 agent 需要 "all"）
        4. tools.agentToAgent.allow（双向：发送方 + 接收方都在内）
    - 输出分级状态（[OK]/[WARN]/[FAIL]）+ 修复建议
    - 零外部依赖，Windows / macOS 双平台通用（纯 Python 标准库）
    - 只读检查，不修改任何配置

示例:
    python check_config.py                          # 默认路径检测
    python check_config.py --config openclaw.json   # 指定路径
    python check_config.py --json                   # JSON 输出（供脚本消费）
"""
import argparse
import json
import os
import sys

DEFAULT_PATHS = [
    # 原生 OpenClaw
    os.path.expanduser("~/.openclaw/openclaw.json"),
    # 小遥Claw 桌面版（Windows / macOS）
    os.path.join(os.environ.get("APPDATA", ""), "xiaoyaoclaw-desktop",
                 "runtime", "openclaw", "state", "openclaw.json"),
    os.path.expanduser("~/Library/Application Support/xiaoyaoclaw-desktop/"
                       "runtime/openclaw/state/openclaw.json"),
]


def locate_config(explicit):
    """定位 openclaw.json，返回路径或 None。"""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    env = os.environ.get("OPENCLAW_CONFIG_PATH")
    if env and os.path.isfile(env):
        return env
    for p in DEFAULT_PATHS:
        if os.path.isfile(p):
            return p
    return None


def load_config(path):
    """加载 openclaw.json。兼容 JSON5 常见写法（剥离注释/尾逗号后解析）。"""
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    # 尝试标准 JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # 轻量 JSON5 兼容：剥离 // 与 /* */ 注释、尾逗号
    import re
    s = re.sub(r"//[^\n]*", "", raw)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return {"__parse_error__": str(e), "__raw__": raw}


def main():
    ap = argparse.ArgumentParser(description="OpenClaw multi-agent config checker")
    ap.add_argument("--config", help="openclaw.json 路径（默认自动定位）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    path = locate_config(args.config)
    if not path:
        msg = {"ok": False, "error": "openclaw.json not found",
               "hint": "use --config PATH or set OPENCLAW_CONFIG_PATH"}
        print(json.dumps(msg, ensure_ascii=False) if args.json else
              "[FAIL] openclaw.json not found (use --config PATH or set OPENCLAW_CONFIG_PATH)")
        sys.exit(1)

    cfg = load_config(path)
    if "__parse_error__" in cfg:
        msg = {"ok": False, "error": "parse failed: " + cfg["__parse_error__"]}
        print(json.dumps(msg, ensure_ascii=False) if args.json else
              "[FAIL] openclaw.json parse failed: " + cfg["__parse_error__"])
        sys.exit(1)

    agents = cfg.get("agents", {}).get("list", []) or []
    tools = cfg.get("tools", {}) or {}
    a2a = tools.get("agentToAgent", {}) or {}
    sessions = tools.get("sessions", {}) or {}

    agent_ids = [a.get("id") for a in agents if isinstance(a, dict) and a.get("id")]
    visibility = sessions.get("visibility", "tree")
    a2a_enabled = a2a.get("enabled", False)
    allow = a2a.get("allow", []) or []

    checks = []
    # 1. agents.list
    if agent_ids:
        checks.append(("agents.list", "OK", "agents: " + ", ".join(agent_ids)))
    else:
        checks.append(("agents.list", "FAIL", "empty — no agents configured"))

    # 2. agentToAgent.enabled
    if a2a_enabled:
        checks.append(("agentToAgent.enabled", "OK", "true"))
    else:
        checks.append(("agentToAgent.enabled", "FAIL", "false — set tools.agentToAgent.enabled=true"))

    # 3. sessions.visibility
    if visibility == "all":
        checks.append(("sessions.visibility", "OK", "all"))
    elif visibility in ("agent", "tree", "self"):
        checks.append(("sessions.visibility", "WARN",
                       f'"{visibility}" — cross-agent needs "all"'))
    else:
        checks.append(("sessions.visibility", "WARN", f'unknown "{visibility}" — cross-agent needs "all"'))

    # 4. allow 双向
    if a2a_enabled:
        if len(allow) >= 2:
            checks.append(("agentToAgent.allow", "OK", ", ".join(allow)))
        elif len(allow) == 1:
            checks.append(("agentToAgent.allow", "WARN",
                           f'only {allow} — allow must include BOTH sender and receiver'))
        else:
            checks.append(("agentToAgent.allow", "FAIL", "empty — add sender+receiver agent ids"))
    else:
        checks.append(("agentToAgent.allow", "SKIP", "agentToAgent not enabled"))

    overall = "OK" if not any(c[1] in ("FAIL", "WARN") for c in checks) else \
              "WARN" if not any(c[1] == "FAIL" for c in checks) else "FAIL"

    if args.json:
        print(json.dumps({
            "config": path, "overall": overall,
            "agents": agent_ids, "visibility": visibility,
            "agentToAgentEnabled": a2a_enabled, "allow": allow,
            "checks": [{"name": n, "status": s, "detail": d} for n, s, d in checks],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"config: {path}")
        print(f"overall: [{overall}]")
        for name, status, detail in checks:
            print(f"  [{status:4s}] {name}: {detail}")

    sys.exit(0 if overall == "OK" else 2 if overall == "FAIL" else 1)


if __name__ == "__main__":
    main()
