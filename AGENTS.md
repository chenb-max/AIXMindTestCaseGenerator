# xmind-testcase Agent 工作规则

本文件是项目级 Agent 总规则，只规定所有任务必须遵守的原则、职责边界和交付门禁。具体的测试用例设计流程、Reference 路由、Case Tree 字段、XMind 格式和故障处理，由 `xmind-testcase/SKILL.md`、`xmind-testcase/references/`、Schema、脚本和测试承载。

规则强度统一如下：

- **MUST（必须）**：完成任务不可省略。
- **MUST NOT（禁止）**：不得执行。
- **SHOULD（优先）**：无明确反例时采用；偏离时说明依据。
- **MAY（可以）**：允许但非必需。

# 1. Agent 原则

## 事实、决策与任务生命周期

- **MUST** 以当前源码、Schema、测试、示例、配置和近期 Git 变更作为项目事实来源。
- **MUST** 在 README、Skill、Reference 与实现冲突时核对调用方和测试，报告冲突，不得静默选择。
- **MUST NOT** 把未提供的业务规则、字段限制、页面行为、权限、错误码或 XMind 能力写成确定事实。
- **MUST** 在不同选择会改变公开契约、兼容格式、覆盖语义或输出内容时向用户确认。
- **MUST NOT** 在没有执行对应校验时声称 Case Tree、XMind 或客户端兼容性验证通过。

所有任务先理解和分析。修改仓库时依次完成：任务理解、影响分析、实施修改、验证交付；咨询、解释、诊断和审查任务默认只读。涉及公开 Schema、输出兼容性或目录职责变化时，必须先说明方案和兼容影响；用户已明确要求实施时视为完成对应确认。

## 修改范围控制

- **MUST** 在实施前明确目标、受影响职责、预期文件和验证范围。
- **SHOULD** 采用满足目标的最小改动，保持现有 CLI、Schema、生成格式和安装方式兼容。
- **MUST NOT** 顺带修复无关问题，或执行无关重构、批量格式化、重命名和目录整理。
- **MUST** 将额外发现的问题作为风险或建议报告；需要扩大修改范围时先确认。
- **MUST** 完成后检查实际差异、未跟踪文件和忽略状态，不得把未完成事项描述为已完成。

## 实现质量

- **MUST** 遵循现有 Python 风格和已有抽象，优先复用 `case_tree.py` 的共享能力。
- **MUST NOT** 提交伪代码、空实现、无说明占位、死代码、无效分支或未使用依赖。
- **MUST** 保持异常可定位、临时文件可清理、失败写入可回滚、已有输出默认不被覆盖。
- **MUST** 让代码注释和 Docstring 说明职责、契约或非直观原因，不逐行复述实现。
- **MUST** 保持代码标识符、Schema 字段、CLI 参数和既有技术术语兼容。

# 2. 项目事实

- 本仓库交付一个可独立安装的 `xmind-testcase` Agent Skill，不是通用思维导图工具。
- Skill 接收需求、页面说明、UI 截图、跨页面流程或已有 Case Tree，并输出经过校验的 `.xmind`。
- Python 支持范围和 CI 事实以 `.github/workflows/ci.yml` 为准，当前覆盖 Python 3.9 和 3.12。
- 依赖以 `xmind-testcase/requirements.txt`、`xmind-testcase/requirements-dev.txt` 和 `xmind-testcase/requirements-legacy.txt` 为准。
- Case Tree 是生成 XMind 前唯一的结构化契约。
- 当前输出目标为 `modern-json`、`legacy-xml` 和 `hybrid`，布局为 `compact` 和 `detailed`。
- `modern-json` 是默认目标；覆盖等级默认 `standard`。
- 生成器默认拒绝覆盖已有 XMind 和摘要；只有明确授权时才使用 `--force`。

# 3. 职责与架构边界

## 仓库级职责

- `AGENTS.md`：Agent 治理、修改边界、安全规则、验证门禁和输出协议；不描述具体生成步骤。
- `README.md`：面向使用者的简洁安装、调用和验证入口；不是 Agent 规则源。
- `.github/workflows/ci.yml`：持续集成的 Python 版本、依赖安装和检查命令事实来源。
- `AI_Xmind/`：与本 Skill 直接相关的使用材料；不承载运行时规则或实现契约。
- `evaluation/`：本地前向评测材料，不属于可分发 Skill，也不得提交。

## Skill 目录职责

- `xmind-testcase/SKILL.md`：触发边界、默认行为、强制执行流程、Reference 路由和最终响应协议。
- `xmind-testcase/agents/openai.yaml`：Skill 列表中的展示名称、简介和默认提示；不得承载执行规则。
- `xmind-testcase/references/`：按任务阶段加载的测试分析、质量、流程和格式知识；不得复制 `SKILL.md` 的完整流程。
- `xmind-testcase/references/schema/`：输入、Case Tree、摘要输出和 XMind 内容的机器可校验结构契约。
- `xmind-testcase/scripts/case_tree.py`：Case Tree 校验、规范化、覆盖提示和摘要的共享核心。
- `xmind-testcase/scripts/validate_*.py`：面向对应契约的 CLI 校验入口，不承载生成逻辑。
- `xmind-testcase/scripts/create_xmind.py`：消费已校验 Case Tree，生成 XMind 和可选摘要，并保护现有文件。
- `xmind-testcase/scripts/render_case_tree.py`：生成确定性文本视图，用于检查，不替代 XMind 生成和校验。
- `xmind-testcase/examples/`：可重复校验的契约示例和稳定生成样本，不是临时输出目录。
- `xmind-testcase/tests/`：共享行为、CLI、Schema、生成事务和示例一致性的回归门禁。

## 依赖与联动约束

- **MUST** 让 `SKILL.md` 只保留核心流程和直接 Reference 路由；详细规则只维护在一个对应 Reference 中。
- **MUST NOT** 在 `xmind-testcase/` 内新增 README、安装指南、变更日志或与执行无关的辅助文档。
- **MUST** 优先通过 Schema、脚本和测试强制确定性规则，不得只写成自然语言约定。
- **MUST** 在修改 Case Tree 字段或语义时同步检查 Schema、`case_tree.py`、CLI、生成器、示例、测试和相关 Reference。
- **MUST** 在修改 XMind 包结构、目标格式或布局时同步检查 `create_xmind.py`、`validate_xmind.py`、格式 Reference、示例和测试。
- **MUST** 在修改触发条件、默认行为或响应协议时同步检查 `SKILL.md`、`agents/openai.yaml`、README 和相关测试。
- **MUST** 在修改依赖时更新对应 requirements 文件，并确认 Python 3.9 与 3.12 兼容影响。
- **MUST NOT** 绕过 Case Tree 校验直接生成或宣称生成了合格 XMind。
- **MUST NOT** 为重复规则创建新的 Skill 或 Reference；只有现有职责无法承载且存在稳定独立主题时才新增文件。

# 4. 安全与仓库规则

## 输入与生成产物

- **MUST** 将用户需求、截图、业务流程和测试数据视为可能敏感的信息，只读取任务所需内容。
- **MUST NOT** 将用户提供的原始材料、真实账号、凭据、Token、业务数据或临时生成产物提交到仓库，除非用户明确要求且内容已确认可公开。
- **MUST NOT** 为验证覆盖用户已有 `.xmind`、JSON 或摘要；使用临时目录或不冲突的输出路径。
- **MUST** 在解析或生成失败时保留原文件，清理本次创建的临时文件，并报告可恢复状态。
- **MUST NOT** 把 `examples/` 当作普通输出目录；更新稳定示例必须有明确任务依据并通过一致性检查。

## Git、工作区与依赖

- **MUST** 在修改前检查 `git status`、当前分支和已有差异；编辑前重新读取目标文件。
- **MUST** 保留用户或其他 Agent 的修改，不得回退、覆盖、删除或格式化无关改动。
- **MUST NOT** 使用破坏性 Git 或文件命令，除非用户明确授权且目标已核对。
- **MUST NOT** 未经要求创建提交、推送远端、修改 Git 配置或主动纳入无关未跟踪文件。
- **MUST NOT** 提交 `evaluation/`、缓存、虚拟环境、临时 XMind、临时 JSON、构建目录或本地摘要。
- **MUST** 在新增或升级依赖前说明必要性，优先使用标准库和已有依赖，并验证安装与关键命令。

# 5. 验证门禁

## 测试完整性与失败诊断

- **MUST NOT** 为使测试通过而弱化或删除断言、放宽 Schema、删除测试、减少覆盖或把错误行为固化进示例。
- **MUST NOT** 把 advisory coverage warning 当成完整业务覆盖证明；`full` 仍需人工复核。
- **MUST** 根据错误路径、测试输出、生成前后字节和可重复现象定位失败，不得猜测通过原因。
- **MUST** 在修复失败时说明根因、修改依据和验证结果；根因不明时说明假设与证据缺口。
- **MUST** 区分代码失败、契约失败、依赖缺失、环境不可用和未执行，不得混写为“验证通过”。

## 验证等级

验证强度随影响递增：

```text
文档与差异检查 -> 定向 CLI/测试 -> 完整 pytest -> 示例校验 -> 客户端人工兼容检查
```

- 纯说明文字修改：**MUST** 运行 `git diff --check` 并核对文档中的路径、命令和职责。
- 修改单个脚本的内部行为：**MUST** 运行对应定向测试和 CLI 校验。
- 修改共享逻辑、Schema、生成器、校验器、示例或 Skill 行为：**MUST** 运行完整测试：

```powershell
python -m pytest xmind-testcase/tests -v -p no:cacheprovider
```

- 修改输入、Case Tree 或 XMind 契约：**MUST** 运行仓库示例校验：

```powershell
python -B xmind-testcase/scripts/validate_input.py xmind-testcase/examples/input_example.json --json
python -B xmind-testcase/scripts/validate_case_tree.py xmind-testcase/examples/case_tree_example.json
python -B xmind-testcase/scripts/validate_case_tree.py xmind-testcase/examples/multi-sheet-case-tree.json
python -B xmind-testcase/scripts/validate_xmind.py xmind-testcase/examples/file-upload-flow.xmind
```

- 修改已提交生成示例：**MUST** 使用仓库脚本重新生成，并确认新产物通过验证且与预期变更一致。
- 声称 XMind 客户端兼容：**MUST** 在对应客户端和版本中实际打开检查；未检查时只报告包结构校验结果。
- 无法执行某级验证时：**MUST** 执行当前最高可用验证，并报告未执行项、原因和剩余风险。

# 6. 输出协议

- **MUST** 基于实际差异和命令结果报告，不得虚构文件、测试数量、生成结果或验证状态。
- **MUST** 至少说明修改内容、修改文件、验证结果和未验证范围。
- **MUST** 对 Schema、格式兼容或跨模块修改补充影响范围、向后兼容性和迁移风险。
- **MUST** 区分 PASS、FAIL、未执行、环境不可用和未授权，并说明未执行原因。
- **MUST NOT** 在无依据时使用“完全兼容”“覆盖完整”“已经验证通过”等表述。
- **MUST** 在只读分析或审查中给出结论、依据、风险和未验证范围，不生成虚假修改摘要。

# 7. Skill 使用规则

`AGENTS.md` 负责规定“必须遵守什么”，`xmind-testcase/SKILL.md` 负责规定“生成测试用例时具体怎么做”。两者不得重复维护同一套执行流程。

规则与事实按以下职责使用：

1. `AGENTS.md`：仓库治理、安全、职责边界、验证门禁和输出协议。
2. `SKILL.md`：Skill 触发、任务流程、Reference 路由和响应协议。
3. Skill references：测试分析方法、质量标准、流程构建和格式细节。
4. Schema、源码和测试：项目当前可执行行为与契约事实。
5. README 和 `AI_Xmind/`：面向使用者的说明材料。

上述顺序表示职责，不表示文档可以覆盖实现事实。Skill 或文档与 Schema、源码、测试冲突时，必须报告冲突，核对近期变更，并同步修正过期说明。

- **MUST** 在生成测试用例时完整读取 `SKILL.md`，并只加载其路由要求的相关 Reference。
- **MUST** 在维护 Skill 时读取 `SKILL.md` 和本次修改直接涉及的实现、契约及测试。
- **MUST** 在行为、Schema、格式或兼容性变化后同步检查对应 Reference 和用户说明。
- **MUST NOT** 因普通示例内容、单个测试数据或临时问题频繁修改本文件。

# 8. Code Review Rules

- 标记任何绕过 Case Tree 校验直接生成 XMind 的路径。安全做法：先校验或规范化 Case Tree，再生成并校验 XMind 包。
- 标记把推断行为写成 `visible` 或 `described`，以及缺少具体 assumptions 的推断用例。
- 标记破坏已有输出、覆盖失败后无法回滚或遗留临时文件的写入路径。
- 标记没有测试覆盖，或未同步生成器、校验器、示例和 Reference 的 Schema/格式变更。
- 标记把 advisory coverage warning、包结构校验或单一客户端检查表述为完整业务覆盖或全面兼容。
- 标记行为变化后过期的 Skill 元数据、README、示例和调用命令。
