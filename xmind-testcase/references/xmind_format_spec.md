# XMind 文件格式规范

## 现代 JSON 格式

默认 `.xmind` 是 ZIP 包，包含：

```text
content.json
manifest.json
metadata.json
```

现代 topic 通常包含 `id`、`title` 和可选 `class: topic`；真实客户端导出的部分 topic 会省略 `class`，校验器允许这种情况。

## XML 格式

`legacy-xml` 输出包含：

```text
content.xml
styles.xml
comments.xml
meta.xml
META-INF/manifest.xml
```

它与成熟 `xmind==1.2.0` SDK 的 XMind 8 XML 结构保持一致；`meta.xml` 和 manifest 作为增强兼容文件保留。纯 XML 文件面向 XMind 8，不保证被 XMind 25 打开。

## 生成和校验

```bash
python scripts/create_xmind.py case_tree.json output.xmind --summary output.summary.json
python scripts/validate_xmind.py output.xmind --json
```

支持：`modern-json`、`legacy-xml`、`hybrid`。

现代 JSON 生成只依赖 `jsonschema`。legacy/hybrid 的 XMind 8 SDK 兼容校验需要可选依赖 `xmind==1.2.0`，可通过 `requirements-legacy.txt` 安装；完整开发环境使用 `requirements-dev.txt`。

兼容矩阵：

| 输出 | XMind 25.7 | XMind 8 SDK |
| --- | --- | --- |
| `modern-json` | 支持 | 不支持 |
| `legacy-xml` | 不保证 | 支持 |
| `hybrid` | 支持 | 支持 |

跨版本分发优先使用 `hybrid`。客户端兼容结论必须来自实际客户端或对应版本 SDK 验证。
