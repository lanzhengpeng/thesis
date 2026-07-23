## 项目概述
- **名称**: AuroraBid 教学内容拆分与物料生成工作流
- **功能**: 从AuroraBid教学仓库ZIP包中提取教学文档 → 智能拆分为大纲 → 逐小节生成教学物料（图文+HTML视频）→ 审核 → 合并 → 最终总审

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| extract_repo | `nodes/extract_repo_node.py` | task | 下载ZIP文件，解压并读取所有教学文档内容 | - | - |
| content_split | `nodes/content_split_node.py` | agent | Python预拆分(按##标题) + LLM智能组织章节结构、生成有趣标题 | - | `config/content_split_llm_cfg.json` |
| prepare_loop | `nodes/prepare_loop_node.py` | task | 将章节树扁平化为子章节列表（支持test_mode只取第1章） | - | - |
| process_loop | `nodes/gen_material_loop_node.py` | looparray | 循环调用物料生成子图，逐小节处理 | - | - |
| generate_images | `nodes/generate_images_node.py` | task | ThreadPoolExecutor并行批量生成配图 | - | - |
| polish_html | `nodes/polish_html_node.py` | agent | 批量润色所有物料的video_html，添加动画/交互体验 | - | `config/polish_html_llm_cfg.json` |
| merge_materials | `nodes/merge_materials_node.py` | task | 合并所有完成的物料，按章节分组 | - | - |
| final_review | `nodes/final_review_node.py` | agent | 最终总审：检查内容通顺性、逻辑连贯性 | - | `config/final_review_llm_cfg.json` |
| structure_output | `nodes/structure_output_node.py` | task | 输出最终结构化结果 | - | - |
| export_output | `nodes/export_output_node.py` | task | 将所有阶段产出保存到 material/{timestamp}/ 目录 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 子图清单
| 子图名 | 文件位置 | 功能描述 | 被调用节点 |
|-------|---------|------|-----------|
| material_loop_subgraph | `graphs/loop_graph.py` | 逐个处理子章节：生成物料(图文+HTML)→审核→推进 | process_loop |

### 子图内部节点
| 节点名 | 类型 | 功能描述 | 配置文件 |
|-------|------|---------|---------|
| gen_material_func | agent(LLM) | 为单个子章节生成文字教学内容、图片描述、选择题、HTML视频代码（图片后续由generate_images节点批量并行生成） | `config/gen_material_llm_cfg.json` |
| advance_func | task | 保存物料到已完成列表，索引+1，判断是否继续循环 | - |

## 技能使用
- `content_split`节点使用大语言模型技能（LLM），模型: `doubao-seed-2-0-lite-260215`
- `gen_material_func`节点使用大语言模型技能，模型: `doubao-seed-2-0-lite-260215`
- `generate_images`节点使用图片生成技能（ImageGenerationClient），ThreadPoolExecutor(max_workers=4) 并行出图
- `review_material_func`节点使用大语言模型技能，模型: `doubao-seed-2-0-lite-260215`
- `polish_html`节点使用大语言模型技能，模型: `doubao-seed-2-0-lite-260215`
- `final_review`节点使用大语言模型技能，模型: `doubao-seed-2-0-lite-260215`

## 工作流拓扑
```
extract_repo → content_split → prepare_loop → process_loop(调用loop_subgraph)
  → generate_images(并行批量出图) → polish_html → merge_materials → final_review → structure_output → export_output → END

loop_subgraph内部:
gen_material(LLM生成文字+HTML+选择题) → should_continue → (未完成→回gen_material / 已完成→END)
```

## 数据流
- **输入**: zip_file (File), test_mode (bool, 可选)
- **中间数据**: file_contents → split_sections → pending_items → completed_materials(含image_prompt) → image_url填充 → video_html润色 → merged_chapters → final_output
- **输出**: final_output (dict) + material/{timestamp}/ 目录下各阶段JSON快照