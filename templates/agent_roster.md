# Agent 清单（agent-roster）

> 用户可编辑的 agent 名单，首次运行时由技能自动生成（基于 openclaw.json 的 agents.list 探测填充）。
> 之后用户自行增删改，技能不写死任何环境信息。
> 本文件建议放在工作区根目录：`agent-roster.md`（或 `agent-roster.json`）。

## 说明

| 字段 | 含义 |
|------|------|
| `id` | agent id（对应 openclaw.json 的 agents.list[].id，**必须一致**） |
| `name` | 显示名（可选，默认同 id） |
| `capabilities` | 能力标签（用户填写，用于「找个会画图的」这类模糊匹配） |
| `note` | 备注（可选） |
| `allowlisted` | 是否在 agentToAgent.allow 白名单（技能读取配置后标注，用户勿手改） |

## 模板

```json
{
  "agents": [
    {
      "id": "xiaoguang",
      "name": "小光",
      "capabilities": ["绘图", "可视化", "架构图"],
      "note": "承接绘图任务",
      "allowlisted": true
    },
    {
      "id": "xiaozhi",
      "name": "小智",
      "capabilities": ["调研", "分析", "竞品"],
      "note": "承接调研任务",
      "allowlisted": true
    }
  ],
  "updatedAt": "2026-08-30"
}
```

## 使用规则

1. **技能**：首次运行时读 openclaw.json 的 agents.list 生成此文件；之后读此文件获取 agent 名单与能力
2. **用户**：随时编辑 capabilities/note；新增 agent 时把 id 加进来（同时需在 openclaw.json 配置好该 agent）
3. **白名单**：`allowlisted` 由技能读取配置后标注，**用户不要手改**——白名单真相源是 openclaw.json 的 agentToAgent.allow
4. **缺失**：文件不存在时技能自动重新生成；agents.list 为空时技能保持沉默（无可分发对象）
