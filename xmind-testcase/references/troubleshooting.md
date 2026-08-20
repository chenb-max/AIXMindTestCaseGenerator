# 故障排查

## Case Tree 失败

```bash
python scripts/validate_case_tree.py case_tree.json --json
```

检查字段路径、重复用例、占位内容、来源和假设。

结构化输入可先单独检查：

```bash
python scripts/validate_input.py input.json --json
```

该命令只校验 `references/schema/input.schema.json`，不会修改输入或生成用例。

## XMind 文件失败

```bash
python scripts/validate_xmind.py output.xmind --json
python -m zipfile -l output.xmind
```

现代格式需要 `content.json`、`manifest.json`、`metadata.json`；XML 格式至少需要 `content.xml`、`styles.xml` 和 `comments.xml`，并可附带 `meta.xml` 和 `META-INF/manifest.xml`。

## 覆盖警告

覆盖警告表示 Case Tree 缺少当前模式和覆盖等级下的建议场景，不一定阻止生成；它们不证明语义上的穷尽覆盖。`full` 覆盖还需要人工复核分支完整性。若 `focus_scenarios` 排除了全部场景，生成会直接失败。

## 输出文件保护

生成器默认不覆盖已有 `.xmind` 或摘要文件：

```bash
python scripts/create_xmind.py case_tree.json output.xmind --force
```

只有所有临时文件校验通过后才会替换目标；这是逐文件替换而非跨文件事务。若摘要替换失败，生成器会回滚已替换的 XMind；若底层文件系统阻止回滚，会保留同目录备份并报错，供人工恢复。

## 图片分析不准确

- 提供原始分辨率截图。
- 按流程顺序提供截图。
- 用文字补充按钮行为和页面跳转。
- 对模糊区域提供局部放大图。
- 对推导场景填写明确假设。

## V2 工作流排查

如果生成结果质量不稳定，按以下顺序检查：

1. 是否先区分了需求事实、截图事实和风险推断。
2. 是否读取了与输入类型匹配的 Reference。
3. 是否完成页面/流程摘要后再设计测试意图。
4. 是否存在重复意图、虚构限制或不可观察预期。
5. 是否在 Case Tree 校验失败后修复并重新运行校验。

事实清单、页面摘要和测试意图默认是 Agent 的内部工作步骤，不要求为了排错而改变现有 XMind 输出契约。
