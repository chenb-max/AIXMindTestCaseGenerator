---
name: xmind-testcase
description: Use when the task is to design software test cases from UI screenshots, page descriptions, requirements, or cross-page flows and package them as validated XMind files. Do not use for generic mind maps.
---

# XMind 测试用例生成

将需求、功能描述或页面截图整理为高质量、可追溯的 Case Tree，并生成经过校验的 `.xmind` 文件。默认在一次调用中完成分析、生成和校验；只有缺少关键输入导致无法确定测试目标时才询问用户。

## 默认行为

- 未指定 `coverage_level` 时使用 `standard`。
- 未指定目标格式时使用 `modern-json`。
- 未指定 `single_page` 或 `cross_page` 时，根据页面数量、流程描述和页面跳转线索判断。
- 未指定输出路径时，按模块或流程名称选择当前工作区下的 `<module>-test-cases.xmind`；目标已存在时选择不冲突的新文件名，不擅自覆盖。
- 使用用户当前语言生成用例内容；保留 Case Tree 和 XMind 的既有字段契约。
- 非阻塞信息缺失时继续生成，并在 `assumptions` 或 warning 中说明；不要为了确认每个细节而中断一次调用。

## 必须执行流程

按以下顺序完成。事实清单、页面/流程摘要和测试意图是内部工作步骤，除非用户要求，默认不要展示。

1. **输入识别**：识别需求、功能描述、截图、流程说明或已有 Case Tree；确定测试模式、覆盖等级、重点场景和输出路径。
2. **读取 Reference**：按下方“Reference 路由”加载与输入和当前阶段相关的规则。
3. **事实提取**：分开记录用户明确描述、需求明确内容、截图可见事实、未知信息和风险推断。遵守来源优先级，不把推断写成事实。
4. **页面/流程摘要**：内部整理页面角色、控件、状态、可见提示、动作、页面顺序和跳转关系。页面关系不确定时保留 `unknown` 或假设，不虚构中间页面。
5. **测试意图设计**：先列出要验证的业务目标或风险，再决定测试技术、场景分类、优先级、来源、置信度和假设。没有依据的场景不为凑分类而生成。
6. **生成 Case Tree**：将测试意图展开为现有 Case Tree 契约，补充前置条件、测试数据、可执行步骤、步骤级预期、最终预期、优先级、来源、置信度和假设。
7. **质量审查**：生成 Case Tree 前检查无依据事实、重复意图、虚构限制、遗漏主流程、不可执行步骤和不可观察预期；发现问题先修正，再写入 Case Tree。
8. **执行校验**：如果用户提供结构化输入，先运行 `validate_input.py`；保存 Case Tree 后运行 `validate_case_tree.py`。校验失败时按错误路径修复并重新校验。
9. **生成 XMind**：仅在 Case Tree 校验通过后运行 `create_xmind.py`，随后运行 `validate_xmind.py`。已有输出默认不覆盖，只有用户明确要求替换时才使用 `--force`。

## 事实与推断硬约束

来源优先级为：

```text
用户明确描述 > 需求明确内容 > 截图可见事实 > 页面语义推断 > 通用测试风险推断
```

- 不编造截图外的控件、字段、页面、权限、接口行为或业务规则。
- 不编造未提供的精确长度、大小、数量、时间、错误码或下拉选项。
- 模糊文字不得生成精确字段用例；按钮含义不明时降低置信度并记录假设。
- `visible` 只能用于截图中清晰可见的事实，`described` 只能用于用户或需求明确描述的事实。
- 风险推导必须使用 `source: inferred`，填写具体、可审查的 `assumptions`，并降低 `confidence`。
- 需求和截图冲突时不要静默选择；保留冲突 warning，并生成可验证实际行为的低置信度用例（如适用）。

## 质量门禁

生成 Case Tree 前确认：

- 每个测试意图只有一个核心目标，且没有明显重复。
- 主流程和当前测试模式适用的核心异常已考虑。
- 前置条件、测试数据和步骤足以让测试人员执行。
- 每个预期描述页面、数据、状态或提示中的可观察结果。
- 没有“系统正常”“功能正常”等不可验证的 Oracle。
- 所有推断都有假设，所有来源标签与事实来源一致。

覆盖分类检查是 advisory warning，不代表业务分支穷尽；`full` 覆盖仍需人工复核。

## Reference 路由

所有任务读取：

- [testcase_generate.md](references/testcase_generate.md)
- [test_intent_and_quality.md](references/test_intent_and_quality.md)

输入包含需求文档或功能描述时读取：

- [requirement_analysis.md](references/requirement_analysis.md)

输入包含页面截图时读取：

- [image_analysis_guide.md](references/image_analysis_guide.md)
- [page_parse.md](references/page_parse.md)

存在多个页面、页面顺序或跨页面流程时读取：

- [flow_build.md](references/flow_build.md)

遇到 XMind 格式、版本兼容、Case Tree 或生成故障时读取：

- [xmind_format_spec.md](references/xmind_format_spec.md)
- [troubleshooting.md](references/troubleshooting.md)

只读取与当前任务相关的 Reference；不要把不同文件中的规则重复写回 Case Tree。

## 校验命令

```bash
python scripts/validate_input.py input.json --json
python scripts/validate_case_tree.py case_tree.json --json
python scripts/create_xmind.py case_tree.json output.xmind --summary output.summary.json
python scripts/validate_xmind.py output.xmind --json
```

现代格式运行时使用 `requirements.txt`；需要 `legacy-xml` 或 `hybrid` 的 XMind 8 SDK 校验时使用 `requirements-legacy.txt`。

## 最终响应协议

成功后只需报告：

- XMind 文件路径。
- 用例数量和 Sheet 数量。
- 覆盖等级和测试模式。
- 推断用例数量。
- 关键 assumptions 或 warnings。
- Case Tree 与 XMind 校验结果。

不要把内部事实清单、页面摘要和完整意图推理默认输出给用户。
