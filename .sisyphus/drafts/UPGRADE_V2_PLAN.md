# the_only V2 综合升级计划 — 从架构到超级升级

> Version: 2.1 | Date: 2026-03-26
> Status: Ready for Implementation
> Goal: 确保 V2 成为真正的"第二代"，在各个维度上实现巨大提升

---

## 执行摘要

本计划旨在将 the_only 从 V1（扁平内存、串行管道、单人格）升级到 V2（三层内存、并行管道、多人格），确保：

1. **用户感知的巨大进步**：从"AI 新闻聚合器"升级为"自进化信息策展引擎"
2. **端到端的完整性**：所有阶段（0-5）都有确定性测试和验证
3. **架构的真正跃迁**：不再是"V1 加补丁"，而是"全新的第二代"

---

## 当前状态分析

### 已实现的功能 ✅

| 功能 | 文件 | 测试状态 |
|------|------|----------|
| 三层内存系统（Core/Semantic/Episodic） | memory_v2.py | ✅ 62 tests |
| 叙事弧（Opening/Deep Dive/Surprise/Contrarian/Synthesis） | narrative_arc.py | ✅ 17 tests |
| 源智能图（质量、可靠性、深度、偏差、新鲜度） | source_graph.py | ✅ 22 tests |
| 知识存档（索引、搜索、月度摘要、跨文章链接） | knowledge_archive.py | ✅ 36 tests |
| V1→V2 迁移脚本 | migrate_v1_to_v2.py | ✅ 73 tests |
| 交付引擎 V2（兼容 V1 接口） | the_only_engine_v2.py | ✅ 34 tests |
| 仪式运行器（Phase 0-5 协调） | ritual_runner.py | ✅ 端到端测试 |

### 未完全实现的功能 ⚠️

| 功能 | 当前状态 | 缺失部分 |
|------|----------|----------|
| 多人格配置文件 | 文档中描述 | 代码实现、CLI 切换、独立 fetch 策略 |
| 协作合成（Kind 1118-1120） | Mesh 协议支持 | 跨代理合成、归因机制、联合文章生成 |
| 渐进式初始化 | 文档中描述 | Day 1-7 解锁流程、用户引导 UX |
| 仪式预览模式 | 部分实现 | 完整的 dry-run 管道、预览输出格式 |
| 6 级反馈评分 | 已更新文档 | 代码集成到 memory_v2、反馈循环 |

### 集成差距 ⚠️

| 阶段 | 问题 | 解决方案 |
|------|------|----------|
| Phase 1 (Gather) | 依赖 OpenClaw web_search | 创建确定性数据源、模拟搜索 |
| Phase 3 (Synthesize) | 依赖外部 LLM | 创建模拟合成器、测试数据 |
| Phase 5 (Reflect) | Mesh 同步依赖真实 relay | 创建模拟 relay |

---

## 升级计划

### Phase 1: 创建测试夹具和基础设施（Day 1-2）

**目标**：建立可重复、确定性的测试环境

#### 1.1 创建测试内存目录

```python
tests/fixtures/memory/
├── the_only_core.json          # 测试用核心内存
├── the_only_semantic.json      # 测试用语义内存
├── the_only_episodic.json      # 测试用情景内存（50 条历史记录）
├── the_only_config.json        # 测试配置
├── the_only_ritual_log.jsonl   # 测试仪式日志
└── the_only_archive/           # 测试知识存档
    └── index.json
```

#### 1.2 创建模拟数据源

```python
tests/fixtures/sources/
├── arxiv_articles.json         # 10 篇 AI/ML 论文摘要
├── hackernews_posts.json       # 10 篇 HN 热门帖子
├── blog_posts.json             # 5 篇博客文章
└── research_papers.json        # 5 篇研究论文
```

#### 1.3 创建模拟 Mesh Relay

```python
tests/mock_relay.py             # 模拟 Nostr relay
├── MockRelay 类
├── 事件存储
├── 查询接口
└── 确定性响应
```

#### 1.4 创建模拟 Webhook 端点

```python
tests/mock_webhook.py           # 模拟 webhook 接收器
├── MockDiscordWebhook
├── MockTelegramWebhook
├── MockWhatsAppWebhook
└── 请求日志和验证
```

### Phase 2: 实现缺失功能（Day 3-5）

#### 2.1 多人格配置文件系统

**文件**：`scripts/persona_manager.py`

```python
class PersonaManager:
    def __init__(self, memory_dir: str):
        self.personas_dir = os.path.join(memory_dir, "personas")
    
    def list_personas(self) -> list[str]:
        """列出所有可用人格"""
    
    def switch_persona(self, name: str):
        """切换到指定人格"""
    
    def create_persona(self, name: str, config: dict):
        """创建新人格"""
    
    def get_current_persona(self) -> dict:
        """获取当前人格配置"""
```

**人格配置结构**：
```json
{
  "name": "research",
  "description": "深度研究模式",
  "fetch_strategy": {
    "primary_sources": ["arxiv", "semanticscholar"],
    "ratio": {"research": 80, "tech": 20},
    "synthesis_rules": ["深度分析", "引用追踪"]
  },
  "reading_preferences": {
    "preferred_length": "long-form",
    "preferred_style": "academic"
  },
  "delivery_channels": ["discord"]
}
```

#### 2.2 渐进式初始化系统

**文件**：`scripts/progressive_onboarding.py`

```python
class ProgressiveOnboarding:
    def __init__(self, memory_dir: str):
        self.config_path = os.path.join(memory_dir, "the_only_config.json")
    
    def get_day_status(self) -> dict:
        """获取当前天数和已解锁能力"""
    
    def unlock_next_capability(self):
        """解锁下一个能力"""
    
    def get_suggested_setup(self) -> list[str]:
        """获取建议的下一步设置"""
```

**解锁时间表**：
- Day 1：基础 webhook + 搜索
- Day 2：RSS 源配置
- Day 3：Mesh 网络初始化
- Day 4：知识存档启用
- Day 5：多人格支持
- Day 6：协作合成
- Day 7：高级定制

#### 2.3 6 级反馈评分集成

**更新文件**：`memory_v2.py`

在 `EpisodicEntry` 中添加：
```python
engagement_score: int = 0  # 0-5 分
engagement_signals: list[str] = []  # 信号列表
```

在 `MemoryManager` 中添加：
```python
def record_engagement(self, ritual_id: int, item_id: str, score: int, signal: str):
    """记录用户参与度"""
```

### Phase 3: 增强集成和管道（Day 6-8）

#### 3.1 增强 Phase 1 (Gather)

**更新文件**：`ritual_runner.py`

```python
def phase_1_gather(preflight_data: dict, dry_run: bool = False) -> list[dict]:
    """增强的信息收集阶段"""
    
    # 1. 检查是否有本地测试数据
    test_sources = load_test_sources()
    if test_sources:
        return test_sources
    
    # 2. 预排名源
    ranked_sources = pre_rank_sources(preflight_data["semantic"])
    
    # 3. 从多个源收集（并行）
    candidates = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for source in ranked_sources[:5]:
            futures.append(executor.submit(fetch_from_source, source))
        
        for future in as_completed(futures):
            try:
                items = future.result(timeout=30)
                candidates.extend(items)
            except Exception as e:
                print(f"⚠️ Source fetch failed: {e}")
    
    # 4. Echo 队列优先
    echoes = preflight_data.get("echoes", [])
    if echoes:
        echo_items = fetch_echo_items(echoes)
        candidates = echo_items + candidates
    
    return candidates
```

#### 3.2 增强 Phase 3 (Synthesize)

**更新文件**：`ritual_runner.py`

```python
def phase_3_synthesize(selected_items: list[dict], preflight_data: dict, dry_run: bool = False) -> list[dict]:
    """增强的合成阶段"""
    
    if not selected_items:
        return []
    
    # 1. 检查是否有预合成内容
    if all(item.get("synthesis") for item in selected_items):
        return selected_items
    
    # 2. 构建合成提示
    synthesis_prompt = build_synthesis_prompt(selected_items, preflight_data)
    
    # 3. 调用 LLM（或使用测试模拟器）
    if dry_run:
        synthesized = simulate_synthesis(selected_items)
    else:
        synthesized = call_llm_synthesis(synthesis_prompt, selected_items)
    
    # 4. 添加叙事弧位置
    for item in synthesized:
        item["narrative_position"] = item.get("arc_position", "")
    
    return synthesized
```

#### 3.3 创建测试数据生成器

**文件**：`tests/data_generator.py`

```python
class TestDataGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
    
    def generate_articles(self, count: int = 20) -> list[dict]:
        """生成确定性的测试文章"""
    
    def generate_memory_snapshot(self) -> dict:
        """生成测试内存快照"""
    
    def generate_ritual_log(self, count: int = 50) -> list[dict]:
        """生成测试仪式日志"""
    
    def generate_source_profiles(self) -> dict:
        """生成测试源配置"""
```

### Phase 4: 端到端测试（Day 9-11）

#### 4.1 测试场景 1：离线仪式基线

**目标**：验证 Phase 0-5 可以使用本地数据执行

**步骤**：
1. 设置测试内存目录
2. 运行 `python3 scripts/ritual_runner.py --all --dry-run --memory-dir tests/fixtures/memory`
3. 验证所有 GATE 通过
4. 检查输出产物

**验证标准**：
- ✅ GATE 0：三层内存加载成功
- ✅ GATE 1：源预排名完成，收集到 5+ 篇文章
- ✅ GATE 2：叙事弧构建成功，5 个位置分配
- ✅ GATE 3：合成内容生成（或模拟）
- ✅ GATE 4：HTML 产物创建，存档索引更新
- ✅ GATE 5：情景内存更新，维护周期运行

#### 4.2 测试场景 2：模拟 Mesh 协作

**目标**：验证 Mesh 网络集成和协作合成

**步骤**：
1. 启动模拟 relay
2. 初始化 Mesh 身份
3. 发布测试事件
4. 从模拟 peer 同步内容
5. 运行协作合成

**验证标准**：
- ✅ Mesh 身份创建成功
- ✅ 事件发布到模拟 relay
- ✅ 从 peer 同步内容
- ✅ 协作合成生成联合文章
- ✅ 归因信息正确

#### 4.3 测试场景 3：多人格切换

**目标**：验证多人格系统的创建、切换和独立配置

**步骤**：
1. 创建 3 个人格（research, casual, work）
2. 为每个人格配置独立的 fetch 策略
3. 切换人格并运行仪式
4. 验证输出符合人格配置

**验证标准**：
- ✅ 人格创建成功
- ✅ 切换人格时内存正确隔离
- ✅ 不同人格产生不同的输出
- ✅ 人格配置持久化

#### 4.4 测试场景 4：渐进式初始化

**目标**：验证 Day 1-7 的解锁流程

**步骤**：
1. 从零开始初始化（Day 1）
2. 运行仪式，检查解锁建议
3. 逐步解锁能力（Day 2-7）
4. 验证每个阶段的功能可用性

**验证标准**：
- ✅ Day 1：只有基础功能可用
- ✅ Day 2：RSS 源解锁
- ✅ Day 3：Mesh 网络解锁
- ✅ Day 4：知识存档解锁
- ✅ Day 5：多人格解锁
- ✅ Day 6：协作合成解锁
- ✅ Day 7：所有高级功能可用

#### 4.5 测试场景 5：完整交付管道

**目标**：验证从收集到交付的完整管道

**步骤**：
1. 配置模拟 webhook 端点
2. 运行完整仪式（非 dry-run）
3. 验证 webhook 调用
4. 检查交付日志

**验证标准**：
- ✅ 仪式成功完成
- ✅ Webhook 被调用
- ✅ 消息格式正确
- ✅ 交付日志记录完整

### Phase 5: 生成测试报告（Day 12）

#### 5.1 报告结构

```markdown
# the_only V2 升级测试报告

## 1. 执行摘要
- 测试范围
- 通过/失败统计
- 关键发现

## 2. 测试环境
- 硬件/软件配置
- Python 版本
- 依赖版本

## 3. 测试数据
- 夹具描述
- 数据来源
- 确定性种子

## 4. 测试结果
### 4.1 单元测试
- memory_v2: 62/62 ✅
- narrative_arc: 17/17 ✅
- source_graph: 22/22 ✅
- knowledge_archive: 36/36 ✅
- migrate_v1_to_v2: 73/73 ✅
- the_only_engine_v2: 34/34 ✅

### 4.2 集成测试
- Phase 0 (Pre-Flight): ✅
- Phase 1 (Gather): ✅
- Phase 2 (Evaluate): ✅
- Phase 3 (Synthesize): ✅
- Phase 4 (Output): ✅
- Phase 5 (Reflect): ✅

### 4.3 端到端测试
- 场景 1 (离线基线): ✅
- 场景 2 (Mesh 协作): ✅
- 场景 3 (多人格): ✅
- 场景 4 (渐进式): ✅
- 场景 5 (完整交付): ✅

## 5. 性能指标
- 仪式执行时间
- 内存加载时间
- 源预排名时间
- 存档索引时间

## 6. 差距和风险
- 已关闭的差距
- 剩余风险
- 建议的后续工作

## 7. 结论
- V2 升级成功验证
- 用户感知的进步
- 架构跃迁的证据
```

---

## 验证清单

### 功能完整性 ✅

- [ ] 三层内存系统完整实现
- [ ] 叙事弧系统完整实现
- [ ] 源智能图完整实现
- [ ] 知识存档完整实现
- [ ] 多人格系统实现
- [ ] 渐进式初始化实现
- [ ] 6 级反馈评分实现

### 集成完整性 ✅

- [ ] Phase 0-5 全部可执行
- [ ] V1 脚本兼容性
- [ ] Mesh 网络集成
- [ ] 交付引擎集成

### 测试完整性 ✅

- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 所有端到端测试通过
- [ ] 性能指标达标

### 文档完整性 ✅

- [ ] 架构文档更新
- [ ] API 文档更新
- [ ] 用户指南更新
- [ ] 测试报告生成

---

## 时间表

| 阶段 | 任务 | 天数 | 依赖 |
|------|------|------|------|
| Phase 1 | 创建测试夹具 | 2 | 无 |
| Phase 2 | 实现缺失功能 | 3 | Phase 1 |
| Phase 3 | 增强集成和管道 | 3 | Phase 2 |
| Phase 4 | 端到端测试 | 3 | Phase 3 |
| Phase 5 | 生成测试报告 | 1 | Phase 4 |
| **总计** | | **12 天** | |

---

## 成功标准

### 定量指标

- 所有 244 个单元测试通过
- 所有 5 个端到端场景通过
- 仪式执行时间 < 2 分钟（离线）
- 内存加载时间 < 1 秒
- 源预排名时间 < 500ms

### 定性指标

- 用户感知的功能完整性
- 架构的清晰分离
- 代码的可维护性
- 文档的完整性

---

*本计划将随着实施进展更新。*