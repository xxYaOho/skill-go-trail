# To Agent

向山出发是一个独立对话 Skill，陪用户在行走中看看自己与外界，逐渐说清尚未成形的内心困惑。

## First Time

- 读 `README.md` 了解产品定位、安装方式和用户体验
- 读 `skill/SKILL.md` 了解实际触发条件、对话边界、安全例外和用户卡协议
- 加载本 Skill 时，读 `skill/subagents/human-card-sprite.md`，创建并在会话内复用同一个小精灵
- 修改前检查工作区，保留 Human 已有改动

## Who is it

- 主对话由 orchestrator 直接承担；用户卡读取、初始化与维护由会话级 subagent 小精灵承担
- Skill 名称固定为 `go-trail`
- 行为合同与版本真源在 `skill/SKILL.md`
- 小精灵的职责合同在 `skill/subagents/human-card-sprite.md`
- `README.md` 负责产品定位、安装与使用说明，不复制完整行为合同
- 使用中文编辑面向用户和 Agent 的主要文案
