# FriendsVerse — Story Prototype Technical Design

**版本**：v0.1.0（实施候选方案）  
**日期**：2026-10-23  
**状态**：技术设计已形成，**尚未编码 / 尚未执行真实模型验收**  
**对应产品需求**：[PRD](PRD.md) · [Story Prototype](STORY_PROTOTYPE.md) · [Character Design](CHARACTER_DESIGN.md) · [World & Interaction](WORLD_INTERACTION.md) · [Decisions](DECISIONS.md)

> 本文件给出一个可执行的最小系统设计。Python、SQLite 和 OpenAI-compatible API 等为推荐默认方案，不是用户已确认的永久架构决策。验收核心是人物、关系与故事质量，而非框架复杂度。

## 1. 问题、目标和不做什么

### 1.1 首个工程目标

用最少的代码建立「**两个角色在合法地点自主相遇 → 交流 → 执行动作 → 保存独立记忆 → 下次交互能利用旧记忆**」的真实 LLM 闭环。第一条链路跑通之后，再扩展到六人、一虚拟日的三时段、连续七集与剧本剪辑。

**七集终态**：同一 Universe 可以手动逐集推进七个虚拟日，保存原始行动日志和世界状态，生成轻松搞笑的情景剧剧本，并能解释重要关系变化来自哪些真实事件。

### 1.2 明确不做
- 不引入 LangGraph / AutoGen / CrewAI 作为硬依赖，不需要 Coordinator Agent、Planner Agent、Critic Agent 团队；
- 不做通用多 Agent 平台、动态招聘 Agent、DAG Scheduler、分布式执行、异步队列；
- 不接图数据库、Redis、Elasticsearch、向量数据库，早期记忆不需要语义检索；
- 不做复杂经济、道路导航、完整工作模拟、视频生成、语音、多人在线；
- 不为了凑满场景数，虚构没有发生的争执、和解或对白。

**为何不直接 Fork social-agent-sim**：原项目以 TypeScript、Claude CLI 和特定驱逐事件为核心。FriendsVerse 可以复用其理念，但直接继承全部规则与技术选择不一定更省事。先用自身最小闭环评估工作量；如果复用效果确实更好，可之后另行作出复用决定。

## 2. 总体系统架构

    CLI (init / next / inspect)
               |
               v
    EpisodeOrchestrator  <----> SQLiteRepository
               |
      +--------+---------+
      |                  |
    WorldEngine      CharacterAgent
    (规则与时段)      (唯一决策入口)
      |                  |
      +------> ActionResolver
               |
               v
        EventRecorder (事实日志)
               |
               v
       MemoryRelationshipUpdater
               |
               v
          EpisodeEditor
               |
               v
         EpisodeValidator
               |
               v
      Atomic Episode Commit

### 2.1 模块职责与明确边界

| 模块 | 输入 | 输出 | 禁止的职责 |
|---|---|---|---|
| EpisodeOrchestrator | 上一集世界快照、预算、事件日程 | 按时段推进的模拟结果、候选新剧集 | 自己编写人物对白 |
| WorldEngine | 当前时间、位置、日程、角色意向、世界事件 | 可合法执行的会面/环境感知 | 决定人物应该喜欢谁或吵架 |
| CharacterAgent | Persona、本人记忆、本人已知关系、局部感知、可用动作 | 结构化行动意向 / 一条对白 | 直接改写世界与其他人的记忆 |
| ActionResolver | 意向、快照、时间/地点约束 | 执行结果、行动事件 | 自主产生额外对白 |
| EventRecorder | 经过校验的动作与对话 | 带事件 ID、时间、地点、目击者的事实 | 根据主观猜测写客观世界事实 |
| MemoryRelationshipUpdater | 原始事件、各角色视角、已有未完事项 | 私有记忆、承诺状态、可解释关系更新 | 无证据大幅修改关系数值 |
| EpisodeEditor | 当天可见的事件片段与前情 | 3–5 场的剧本候选与来源 ID | 创造没有发生的对话、改变事件顺序 |
| EpisodeValidator | 事件、剧本、关系更新、快照 | 通过/不通过 + 失败原因 | 用「文学质量」掩盖事实错误 |
| SQLiteRepository | 发布候选快照、事件与剧本 | 原子持久化、可回读版本 | 在生成期间让未确认状态成为正式世界 |

### 2.2 执行范式

采用**确定性工作流 + 局部 ReAct 式交互**：
- 外层固定：载入 → 日内推进 → 收集真实事件 → 记忆/关系更新 → 剧本剪辑 → 校验 → 提交。
- 内层有限：CharacterAgent 根据感知选择动作，收到 ActionResolver 的真实反馈，再决定下一步。
- 无全局预先规划的七集剧情；角色只是为自己的目标作局部决策。
- 同一场会面中的人物按顺序回应，以便下一位确实看到上一位说过的内容。MVP 采用单进程顺序执行，避免并发写入冲突。

不应把六个人同时发给一个 Prompt 让 LLM 一次扮演六人；每位角色独立人格、状态、可见历史和调用上下文，但可以**共享同一个基础模型**。

## 3. 技术栈与为什么这么选

**推荐默认栈**（代码阶段可基于一次真实接入验证微调）：
- Python 3.11+；
- OpenAI-compatible LLM API，经一个轻量 ProviderAdapter 封装模型调用、错误处理和用量统计；
- Pydantic 验证模型的动作 JSON 和剧集数据；优先使用模型支持的结构化输出能力，不支持时使用文本 JSON + 本地校验 + 一次修复尝试；
- SQLite（标准库 sqlite3 即可），用单数据库保存世界快照、事件、剧本、运行信息；
- pytest 覆盖纯规则单测、假模型集成测试、可选真实模型端到端测试；
- YAML 或 JSON 存静态角色 Persona、场景及生活事件；环境变量存模型配置，**不得上传 API Key**；
- CLI 作为用户入口（初始化、下一集、检视），不做 MVP Web UI。

**相对 TypeScript Fork 的权衡**：
- Python 适合现有 Agent 实验与评测、Pydantic 数据模型、较小的运行时实现；
- 若未来要直接复用 social-agent-sim 的 viewer 或运行时，TypeScript 迁移成本更低；
- 优先用一个 2-Agent spike 检验真实调用与内容质量，避免仅凭偏好否定复用。

不锁定具体模型厂商、SDK 版本或自建后端；需验证目标供应商能否可靠返回结构化输出。

## 4. 推荐项目结构

    FriendsVerse/
      README.md
      docs/
        PRD.md
        STORY_PROTOTYPE.md
        CHARACTER_DESIGN.md
        WORLD_INTERACTION.md
        STORY_PROTOTYPE_TECHNICAL_DESIGN.md
        DECISIONS.md
      config/
        characters/      # 6 份人格种子
        world.json        # 地点/时段
        opportunities.json
      src/friendsverse/
        cli.py
        config.py
        models.py
        llm.py
        orchestrator.py
        world.py
        character.py
        actions.py
        memory.py
        relationships.py
        episode.py
        repository.py
      tests/
        unit/
        integration/
        live/            # 真实模型测试，默认跳过
      .env.example
      pyproject.toml

这是**代码开始后的建议布局**，目前不创建空目录或无效模块。

## 5. 核心数据契约

### 5.1 WorldSnapshot（唯一可提交客观状态）
包含 universe_id、version、next_episode_no、virtual_day、period、location_by_character、可见世界物件/生活事件、角色个人当前目标、主观记忆和关系投影、未完事项。静态 Persona 与事实 Baseline 不在每轮重复复制。

推荐 Pydantic 模型以 JSON 可序列化结构为准。

### 5.2 CharacterPerception（提供给某一个角色）
至少含当前时间/地点、实际在场者、被其观察/听见的信息、自己的人格摘要、目标、自己对在场角色的印象及相关记忆、可用动作。

**硬约束**：绝不自动输入其他角色的内部想法、未公开记忆、未亲眼见到的异地对话；个人信念与事实分开保存。

### 5.3 ActionIntent 与 ExecutedEvent

**ActionIntent** 为模型的建议，建议使用联合类型：
- move_to(target_location)：请求移动；
- speak(target_id 可空, text)：发出一句可被现场听见的对白；
- do(action_type, target 可空)：从白名单选择简单行为（例如请求帮助、归还物品、协助排练；具体枚举逐步增加）；
- wait(reason 可空)：暂不行动。

模型返回 JSON，含 actor_id、action、参数和可选简短意向说明；**说明不是事实，也不公开为剧本对白**。一次模型调用原则上只产生一个动作，避免未经验证便批量连续执行多步。

**ExecutedEvent** 必须由 Runtime 确认后生成：event_id、episode_no、period、location_id、actor_id、receivers、event_type、payload、witnesses、source_action_id、success、failure_reason（如失败）。只有成功动作会更改实际世界；失败也可作为行动反馈被角色看见，不可误写成成功事实。

### 5.4 SocialFact / Commitment / RelationshipChange
- 客观社会事实只从已执行/实际说出的事件中推导；带 source_event_ids。
- 「说出了明天帮忙」与「对方确实确认了时间」需要区分。建议 Commitment 使用 proposed / acknowledged / fulfilled / missed / cancelled 等状态及参与者、截止日、证据事件 ID，避免仅凭一句含糊的话直接认定失约。
- 私人记忆可以记录误会和主观情绪，世界事实仍以源事件为准。
- RelationshipChange 至少含 from_id、to_id、dimension、before、after、reason、source_event_ids，且源事件必须存在并发生在变更之前。
- 首版可用定性等级或统一默认标尺初始化，**不必为六人手填 30 条有向关系的全部精确数值**；变化阈值在样片测试中校准。

### 5.5 Episode / Scene
Episode 含 universe_id、episode_no、virtual_day、title、recap、scenes、relationship_changes、source_event_ids、world_version_from/to。每个 Scene 含 location、period、lines（角色对白/必要动作）、对应原始 event_id 列表。

**编辑器边界**：允许删掉不重要内容、分场、拟标题、补少量不改变事实的时间/地点提示；首版**关键对白逐字保留**，不能改写说话者、行为事实、顺序和知识边界。任何摘要应能被源事件支持。无足够内容时允许短集。

## 6. 单集生成的精确运行顺序

0. 输入：用户明确执行 next；获取已提交的 Snapshot 和版本号；本地标记本轮在处理中（CLI 同进程禁止重复提交）。
1. 创建一份**仅在内存中变化**的工作快照，不立即更改正式数据库状态。
2. 遍历早晨 / 下午 / 晚上三个时段：
   - WorldEngine 推进基础日程与符合条件的 0–1 个环境刺激；
   - 激活存在目标、会面可能、未完事项或特殊刺激的角色；纯通勤/睡眠直接走规则；
   - 每位角色基于**自己能看到的世界**先选活动意向；
   - WorldEngine 统一解析合法移动、相遇、在场和访问权限；
   - 遭遇参与者有限轮分别调用 CharacterAgent，接收结构化动作；
   - ActionResolver 校验并执行；EventRecorder 即时把事实写入工作日志；
   - 视事件及时更新角色本轮可见上下文；重要的跨日记忆/承诺/关系可以在每个场景后更新工作快照。
3. 日终把事件整理成因果顺序，补全未完事项，调用 MemoryRelationshipUpdater 更新全部受影响角色的个人视角和关系事件。
4. EpisodeEditor 从**实际已发生事件**中挑选可读片段，生成剧集草稿。
5. EpisodeValidator 检查剧集来源引用、角色身份、同一时段地点一致性、角色可知信息、未完事项、关系证据、剧集编号与世界版本。
6. 若通过：在**一个 SQLite 事务**里提交新快照、新剧集、事件和关系证据；version + 1。未通过：原世界保持不变，返回明确失败原因。
7. CLI 返回已保存剧集的路径/编号、重要关系变化和运行统计。后续只有用户再次调用 next 才会生成下一集。

**一致性与并发**：
- 不在持有数据库写事务期间等待 LLM 网络返回。
- 按快照版本进行提交前校验；仅当库中 version 仍等于开始时的版本才允许提交（optimistic check）。
- 给 universe_id + episode_no 添加 UNIQUE 约束；两次意外并发的提交只能有一次成功，另一方重新读取而非覆盖。
- 运行期可以在内存工作快照写临时事件；崩溃时原世界未发布。恢复后重复生成的是新的一次候选，不宣称随机模型结果可逐字复现。
- 为可复盘保存模型请求与响应的必要审计信息、模型标识和实际 token 统计；API 不返回时只能标记为估算值。**精确 replay 必须重放保存的模型响应，而非单靠随机种子**。

## 7. 最小存储方案

推荐 SQLite，不使用 ORM 也可以：
- universes：主键、当前版本、最新剧集号、完整 JSON 快照；
- episodes：universe_id、episode_no、title、剧本 JSON、source_event_ids、基于快照的发布元信息；唯一键(universe_id, episode_no)；
- events：event_id、universe_id、episode_no、period、payload JSON、可见者；
- runs（可选但推荐）：run_id、起始版本、模型调用/工具调用统计、失败原因、耗时，支持定位原型问题。

独立角色记忆、当前关系和未完事项可先存 universe snapshot JSON；无需提早拆成大量关系表。事件表负责事实证据和查找来源。

**取舍**：相比散落的 JSON/Markdown 文件，SQLite 的优势是一个事务能同时提交剧集和快照；相比完整业务数据库，它部署简单、符合单用户 CLI 的规模。

## 8. 模型调用及异常处理策略

- **同一个基础模型，多份角色 Persona**。CharacterAgent 只使用一个标准 Prompt 模板 + 角色数据 + 局部感知 + 动作 Schema。
- 角色不直接调用任意系统工具，不支持 Bash、浏览器或外部网络操作；动作只通过白名单 Resolver 执行。
- 模型 API/网络失败：限次重试（建议一次）；若仍失败，记录错误并让角色执行安全的 wait 或终止本日，不能捏造输出。
- JSON 格式失败：本地 Pydantic 校验；可进行一次 JSON 修复/重采样；仍失败则明确失败/等待。
- 非法移动或知识穿越：ActionResolver 拒绝，给出动作失败反馈；重要一致性问题应使当前剧集校验失败，不靠编剧补救。
- 会话反复寒暄：在无新事实、新意向或新增参与者时退出；另设有限轮次/调用预算上限。
- 环境事件和情景剧编辑不能改变其他角色的私有意图；避免「导演 Agent」强行让人物冲突。
- **预算是运行参数，不是无限自由循环**：建议原型先限制每段会面最多约 4–6 次轮流回应，再用真实数据调整；不把具体限额写死为永久产品要求。

## 9. 评测与可观测性

### 9.1 必须留下的证据
- 每次模型输入可访问的上下文类别（避免意外泄露其他角色记忆）、输出动作、Resolver 执行结果；
- 每次实际对话文本、地点、时段、目击者和事件 ID；
- 角色关系的前后状态、原因、来源 event_id；
- 剧集每个主要段落链接到源事件，原始剧本可固定回看；
- 模型、耗时、调用次数、失败类型、token（真实/估算标识）和必要的调试 Trace。

### 9.2 确定性测试
- 非法行动被拒绝，世界快照不会被直接修改；
- 不在场角色不知道异地对白，无法瞬移；
- 会面中后说话的人能看到此前真实对白，早说话的人不能预见未来；
- 失约只在约定成立且对应期限到来后成立；
- 单个笑话/普通感谢不自动导致关系剧烈波动；
- 关键关系变动指向真实 event_id；
- EpisodeEditor 不改变说话者或编造台词；
- 超预算可安全结束，失败重试不产生重复集数；
- 失败事务不发布半成品；同一 universe 同一集仅允许一个版本提交。

### 9.3 内容体验测试（人工）
- 同一情境六个角色对比，判断人格差异与刻板重复；
- 不看名字能否分辨多数主要对白的角色；
- 连续七集至少有一条可信、由事件驱动的关系故事线跨越三集；
- 3–5 名目标用户逐集评分：幽默、角色辨识、关系可信、连续性、追剧意愿；
- 不强制必须出现某对情侣或激烈争吵；没有冲突也不代表执行失败；
- 如果「行动系统正确，但观众不愿看」：先改故事机会、人格及编辑规则，而不是扩大系统复杂度。

## 10. 四步里程碑（按最短可验收闭环）

### T0 — 基础协议（不接真实模型）
- 固定两个人物、一个地点、一个时段；
- 实现 Schema、ActionResolver、EventRecord 和 SQLite 保存/回读；
- 用 FakeLLM 决定简单动作并验证非法移动/信息隔离。
- **DoD**：测试通过、事件可追溯、重启后状态一致。

### T1 — 两人真实交互
- 使用 Chandler 与 Joey，共用标准 CharacterAgent，但各自 Persona 和记忆不同；
- LLM 正常产生自主请求/回应；可承诺下次帮助，下一次运行能读回个人记忆；
- 实际生成的对白和活动保存并可 Inspect。
- **DoD**：真实模型完整执行至少两次连续交互；不是提前写好的行动脚本。

### T2 — 六人世界与单日剧集
- 增加六人、四个核心场景、三个日内时段和少量机会事件；
- 实现活动意向→地点解析→有限对话、角色知识隔离、轻量关系更新、EpisodeEditor；
- 实际生成一集可阅读剧本，并通过事实一致性校验。
- **DoD**：剧本事实能逐条关联 event_id；不会串地点、泄露未知信息、无故跳变关系。

### T3 — 七集连续性与评测
- 同一宇宙手动生成七集，记录所有事件、记忆和关系变化；
- 对照主要关系线的证据链，试读七集；
- 记录内容缺陷、模型/工具失败类型、成本与耗时。
- **DoD**：达到 [Story Prototype](STORY_PROTOTYPE.md) 中既定的硬门槛和体验评审要求；若观众没有追剧兴趣，先优化内容，不直接推进 Web UI。

**先完成 T0/T1 再讨论更多通用 Agent 基础设施；这是避免过度设计的最重要约束。**

## 11. 已知风险与必须承认的边界

1. **故事无聊**：Agent 在环境中正确执行不等于剧集好看。需要调节故事机会频率和内容选择，但不能伪造事件。
2. **LLM 结构化输出不稳定**：不同兼容接口支持的 Schema 强度不同；本地校验与重试必须存在。
3. **人物认知穿越**：多角色共享世界状态不等于共享所有信息；输入构造必须按可见性过滤。
4. **时间和承诺歧义**：自然语言约定如果缺少时间或确认，不应立即认定已兑现或失约。
5. **关系数字制造假精度**：应优先保存事实证据，再探索量化规则。
6. **Token 与运行速度**：真实成本需要 T1/T2 测量；不要在未验证前给出保证。
7. **单一 SQLite/单进程适用于原型而非横向扩容产品**：升级为多人实时系统时再考虑分布式一致性。
8. **版权/商标/肖像**：目前为私人粉丝概念验证；公开分发前需要授权或原创 IP 化。

## 12. 待实验确定而非立即锁死的选项

- Python 自研最小闭环 vs TypeScript 复用 social-agent-sim 的实际成本；
- 模型及配置字段；是否使用供应商原生结构化输出；
- 角色关系定性等级向数字映射的具体公式；
- 每次相遇的最大对话轮数、每集可承担的预算；
- EpisodeEditor 是否需要单独模型调用，是否满足强制引用原文对白的约束；
- 长期记忆何时需要摘要和召回策略（前七集先尽量保留原始重要记忆）。

## 13. 版本记录

| 版本 | 日期 | 变化 |
|---|---|---|
| v0.1.0 | 2026-10-23 | 给出低复杂度 Python/SQLite CLI 候选架构、领域模型、逐集执行事务、一致性约束、真实模型验证与 T0–T3 实施顺序 |
