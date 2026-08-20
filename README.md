# XMind 测试用例生成 Skill

`xmind-testcase` 是一个 Codex Agent Skill：它根据需求、页面说明、UI 截图或跨页面流程，生成可追溯的测试用例树，并输出经过校验的 `.xmind` 文件。

## 能力

- 自动识别单页面和跨页面测试模式。
- 支持 `minimal`、`standard`、`full` 覆盖等级。
- 覆盖主流程、异常、边界、权限、状态一致性和重复提交等风险。
- 通过 Case Tree Schema 校验后再生成和校验 XMind。
- 支持 `modern-json`、`legacy-xml` 和 `hybrid` 输出格式。

## 目录

```text
xmind-testcase/
├── SKILL.md                 # Skill 入口和执行约束
├── agents/openai.yaml       # 客户端展示与调用策略
├── references/              # 需求、流程、质量和 XMind 规则
├── scripts/                 # 输入、Case Tree、XMind 校验与生成
├── examples/                # 示例输入、Case Tree 和 XMind
└── tests/                   # 自动化测试
```

`evaluation/` 是本地评测数据，不随仓库分发。`AI_Xmind/` 仅保留 Skill 使用说明。

## 安装

环境要求：Python 3.9+，以及支持 Agent Skills 的 Codex CLI 或 IDE 客户端。

```bash
python -m pip install -r xmind-testcase/requirements.txt
```

将 `xmind-testcase/` 复制到客户端的 Skill 目录，例如：

```text
Windows: %USERPROFILE%/.agents/skills/xmind-testcase
macOS/Linux: ~/.agents/skills/xmind-testcase
```

安装后在 Codex 中调用 `$xmind-testcase`，提供需求、截图或流程，并指定输出路径。例如：

```text
使用 $xmind-testcase，根据登录页面截图生成 standard 测试用例，
覆盖正常、异常、边界和重复提交，输出并校验 login.xmind。
```

## 命令行验证

```bash
python xmind-testcase/scripts/validate_input.py xmind-testcase/examples/input_example.json --json
python xmind-testcase/scripts/validate_case_tree.py xmind-testcase/examples/case_tree_example.json
python xmind-testcase/scripts/create_xmind.py xmind-testcase/examples/case_tree_example.json output.xmind --summary output.summary.json
python xmind-testcase/scripts/validate_xmind.py output.xmind
```

运行测试：

```bash
python -m pytest xmind-testcase/tests -v -p no:cacheprovider
```

生成的用例仍需由测试人员审核；没有依据的业务规则会记录为推断或待确认项，不会被当作事实写入。
