<div align="center">
  <h1>向山出发</h1>
  <p><strong>在行走中感受自己，也感受外界</strong></p>
  <p>一个陪用户走一段、慢慢看清内在困惑的 Agent Skill</p>
</div>

---

有时人知道自己被什么困住了，却还说不清那到底是什么。go-trail 提供一段独立的对话，让用户在与自己和外界的接触中，慢慢把心里的话说完整。

它不急着解释，也不替用户决定。Agent 会认真听，诚实回应，偶尔放下一个问题或新的角度。理解从对话里长出来，最后仍由用户判断什么与自己有关。

## 快速开始

```bash
git clone https://github.com/xxYaOho/skill-go-trail.git
cd skill-go-trail
mkdir -p ~/.agents/skills
ln -s "$(pwd)/skill" ~/.agents/skills/go-trail
```

`~/.agents/skills/` 是跨工具通用目录。也可以按所用 Agent 工具选择专用目录：

| CLI | 用户级 Skill 目录 |
| --- | --- |
| Claude Code | `~/.claude/skills/`，也读取 `~/.agents/skills/` |
| Kimi Code CLI | `~/.kimi-code/skills/`，也读取 `~/.agents/skills/` |
| Codex CLI | `~/.agents/skills/`，项目级为 `<repo>/.agents/skills/` |
| DeepSeek Harness | `~/.agents/skills/` |

例如，只安装给 Claude Code：

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skill" ~/.claude/skills/go-trail
```

链接名必须是 `go-trail`，链接目标必须是包含 `SKILL.md` 的 `skill/` 目录，而不是仓库根目录。

确认安装：

```bash
ls ~/.agents/skills/go-trail/SKILL.md
```

移除通用安装：

```bash
unlink ~/.agents/skills/go-trail
```

这只会删除符号链接，不会删除仓库。

## 会发生什么

Agent 可以在开场时给自己取一个简短的 nickname，随后就把注意力放回用户身上。它不会扮演一个有背景故事的人物。

对话没有固定步骤。Agent 会沿着用户真正说出来的内容，一次只往前走一点。有时它问一个问题，有时只把听见的东西还给用户。它可以提出不同看法，也会承认自己可能理解错了。

Agent 的语气温和，但不会顺着用户说。它不使用自动夸奖或空泛安慰；遇到回避和矛盾，也可以坦诚指出。所有判断都交还用户核对。

## 用户卡

本技能维护一张本地用户卡 `~/.data/go-trail/human-card.md`。每次进入向山出发时，先读取这张卡；如果不存在，就创建一张空卡，再随着对话逐步完善。创建和更新不要求用户逐条确认，但首次创建时会告知用户；用户可以随时查看、修改、删除或清空。

主 Agent 会在会话开始时创建一个低强度 subagent，内部称为“小精灵”。小精灵负责读取或初始化用户卡，并在同一会话中持续复用；后续只接收新增信息。它不参与主对话，也不保存完整谈话。

用户卡大约八成用于稳定背景、长期责任与约束，两成用于沟通偏好；这是取舍原则，不是字段配额。它保存最低必要的抽象，例如将孩子人数归纳为“承担育儿责任”，而不是保留家庭构成。一次性情绪、心理推断、人格模式、关系动机、危机内容、秘密和完整对话不会写入；敏感内容即使经过抽象，也只有在明确、稳定且长期有用时才会保留。

## 边界

Agent 不替用户选择，不把对话变成问题求解，也不提供心理诊断或治疗。它不会宣称比用户更了解其内心，也不会把新会话的内容带回原会话。用户卡只保存明确的长期背景，不是心理档案。

当对话显示可能存在自伤、他伤、虐待控制或其他即时人身风险时，Agent 会暂停常规探询，优先确认安全并建议联系现实中的可信任对象、当地紧急服务或专业支持。
