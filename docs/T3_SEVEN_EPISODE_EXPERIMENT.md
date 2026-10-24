# T3 — 七集连续性与故事体验实验

**状态**：七集运行与证据导出功能已开发；**尚未完成真实 LLM 七集验收或用户试读**。  
**前置证据**：[T1 已通过真实双角色技术验证](T1_LIVE_VALIDATION_REPORT.md)；T2 六角色真实模型单集仍需验收。

## 目标
把当前六角色、三时段、独立记忆、社会动作、关系演化、事件证据和剧本输出串起来，能在**同一 Universe** 连续产生七集并保存；把工程一致性与故事好看与否分开评价。

## 两种用户操作，不能混淆

- **产品正常模式**：每次 `next` 只推进一集，用户手动选择何时观看。
- **T3 明确请求的实验批处理**：一次执行 `season --days 7`，用于快速生产七集样片。这不是让产品后台自行无限生长，而是一次人工启动的有边界验证。

七集实验提供轻量活动预算：`--actors-per-period 3` 时，每个时段最多三位角色先选择活动意向、再在可能会面时回应，总计**一天最多 18 次角色决策、七天最多 126 次角色决策**。模型 JSON 修复或底层 API 重试可能让真实请求次数增加，Token 数取决于输入记忆长度。先试 1 日有助于确认成本与内容形态。

## 本地 / Actions

```bash
python -m pip install -e ".[dev]"
python -m friendsverse init --mode ensemble --db season.db

# Fake 仅证明数据链完整；不能证明人物自主性
python -m friendsverse season --provider fake --days 7 --actors-per-period 3 \
  --db season.db --out season-review/

python -m friendsverse report --db season.db --out season-review/
```

真实模型可使用同样的 `--provider live`，读取 `LLM_API_KEY`, `LLM_MODEL_ID`, `LLM_BASE_URL`。仓库提供 [T3 seven-episode live experiment](../.github/workflows/t3-season-validation.yml) 手动 GitHub Actions 工作流，填写 model_id（或使用 Variable/Secret）、days（1–7）以及 actors_per_period（建议 2–3）。

### 中断与恢复
每生成一集便执行独立的世界+剧集事务；第 4 集失败不影响前 3 集，可复用**同一份 SQLite** 执行 `season --days 4` 补齐剩余。CLI 拒绝超过七集的 season 请求。

GitHub Actions 每次手动运行使用一个新的 Runner，不会自动继承上次的世界。Artifact 上传当前 DB 供下载与本地恢复，而不是错误承诺「重新点 Run workflow 会从上次继续」。

## 导出文件

| 文件 | 包含内容 | 用途 |
|---|---|---|
| `season-review/season-scripts.md` | 全部实际事件渲染的原始剧集 + 人工评分清单 | 阅读七集样片 |
| `season-review/season-summary.json` | 分集事件、对白数、发言角色、被拒动作、关系证据、检查问题 | 工程与连贯性审计 |
| `season-review/episode-evidence.json` | 每集完整结构化 Action Event、证据和 prior_memory_ids | 溯源/调试 |
| `friendsverse-t3.db` | SQLite 世界状态、记忆与剧集 | 本地续跑与复现快照 |

所有剧本只来自执行的对白和事件；没有虚构一个「编辑 Agent」去编写未发生的内容。

## 验收分两层

### 工程硬门槛
- 相同 Universe 发布七集，编号和世界版本连续，虚拟天数正确；
- 私人记忆引用只指向此前存在且本人亲历的事件；
- 关系变更都有本集真实事件证据，不存在时间先后颠倒；
- 六个角色在整季至少有发言（这是覆盖指标，不是强制每集出场）；
- 中断后已提交的剧集可恢复，不会覆盖此前内容。

### 产品体验（需要真实 LLM 结果与读者评审）
- 角色辨识度、幽默程度、事件因果、人物关系可信度、是否想看下一集；
- 至少一条真正经历三集发展、有前因后果的关系主线；
- 是否因「六人分别发表意见」变成流水账；
- 重要承诺和误会是否造成后续行动，而不只是被模型复述。

`season-summary.json` 中 `evidence_based_multiepisode_relationship_patterns` 只是**关系变化跨集出现的机械证据**，不是故事主线质量证明。程序不能自动声称通过人工体验验收。

## 后续最小动作

先检查 T2 的单日真实六角色样片，再根据样片决定是否需要调整行动频率/交互自由度。确认至少有基本可读互动后，手动执行 T3 七集实验并审阅产物；如果故事不好看，优先调整事件机会与人物社交机制，不建设大型分布式 Harness。
