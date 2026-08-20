# xmind-testcase 仓库工作约定

## 适用范围

本文件适用于整个仓库。仓库的核心交付物是 `xmind-testcase` Agent Skill；修改应围绕软件测试用例的分析、Case Tree 校验和 XMind 生成展开。

## 事实来源

- `xmind-testcase/SKILL.md`：Skill 触发边界、必需流程和最终响应协议。
- `xmind-testcase/references/`：需求、截图、流程、质量和 XMind 格式的详细规则。
- `xmind-testcase/references/schema/`：输入、Case Tree、输出和 XMind 的结构化契约。
- `xmind-testcase/scripts/`：校验、生成和渲染的确定性行为。
- `xmind-testcase/tests/`：可执行的回归预期。
- `xmind-testcase/agents/openai.yaml`：面向用户的 Skill 展示信息。
- `README.md`：简洁的安装和使用说明，不承载运行时规则。

同一条规则只维护一处：核心执行步骤写入 `SKILL.md`，详细领域规则写入对应 Reference，可强制的数据行为写入 Schema 或脚本。

## 任务分流

- 生成测试用例时，严格执行 `xmind-testcase/SKILL.md`，只加载其 Reference 路由选中的文件。
- 通用思维导图任务不使用本 Skill。
- 维护 Skill 时，编辑前完整阅读 `SKILL.md` 和本次修改直接涉及的文件。
- 修改 Schema 或输出格式时，同时检查对应 Schema、生成器、校验器、示例和测试。
- 修改触发条件或工作流时，确认 `agents/openai.yaml` 和 `README.md` 仍然准确。

## 修改原则

- 保持 `SKILL.md` 简洁，使用祈使式表达，只保留核心流程和 Reference 路由。
- Reference 与 `SKILL.md` 只保持一层目录关系；需要加载的文件必须由 `SKILL.md` 直接链接。
- 不在 `xmind-testcase/` 内增加 README、安装指南、变更日志等辅助文档。
- 可确定执行的行为优先通过现有脚本和 Schema 实现，不只写成文字约定。
- 保持 Case Tree 为生成 XMind 前唯一的结构化契约。
- 不把缺失的需求写成确定事实。推断用例必须使用正确的 `source`、降低 `confidence`，并记录具体 `assumptions`。
- 测试步骤必须可执行，预期结果必须可观察，不使用“系统正常”“功能正常”等模糊表述。
- 除非用户明确要求破坏性变更，否则保持已有契约向后兼容。
- 除非用户明确允许覆盖，否则不得替换已有生成产物。

## 验证要求

先运行与改动直接相关的检查；共享行为或结构化契约发生变化时扩大验证范围。

修改 Skill 行为、脚本、Schema、示例或测试后，运行：

```powershell
python -m pytest xmind-testcase/tests -v -p no:cacheprovider
```

修改输入、Case Tree 或 XMind 处理逻辑时，再运行对应的命令行校验：

```powershell
python -B xmind-testcase/scripts/validate_input.py xmind-testcase/examples/input_example.json --json
python -B xmind-testcase/scripts/validate_case_tree.py xmind-testcase/examples/case_tree_example.json
python -B xmind-testcase/scripts/validate_case_tree.py xmind-testcase/examples/multi-sheet-case-tree.json
python -B xmind-testcase/scripts/validate_xmind.py xmind-testcase/examples/file-upload-flow.xmind
```

修改已提交的生成示例时，必须使用仓库脚本重新生成并通过对应校验。纯文档修改无需运行完整测试，除非它改变了命令、契约或运行时行为。

## 仓库卫生

- 文本文件使用 UTF-8 和 LF。
- 不提交 `evaluation/`、缓存、虚拟环境、临时 XMind 或本地生成的摘要。
- `AI_Xmind/` 只提交与本 Skill 使用或维护直接相关的内容。
- 不做无关重构，不制造生成元数据噪音；没有明确需求时不增加运行依赖。
- 提交前检查暂存文件清单，并说明实际运行过的验证命令。

## Code Review Rules

- 标记任何未先校验 Case Tree 就生成 XMind 的路径。
- 标记把推断行为写成 `visible` 或 `described`，以及缺少 assumptions 的推断用例。
- 标记没有测试覆盖，或未同步生成器和校验器的 Schema 变更。
- 行为变化后，标记过期的示例、Skill 元数据和 README 说明。
