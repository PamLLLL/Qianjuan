---
name: create-rule-file
description: 创建新的 Markdown 规则文件（平台/生成/风格/类型），供规则引擎加载注入 Prompt
---

## 步骤

1. 确定规则类型和文件位置：
   - 平台规则 → `rules/platforms/{name}.md`
   - 生成规则 → `rules/generation/{name}.md`
   - 风格模板 → `rules/styles/{name}.md`
   - 类型规则 → `rules/genres/{name}.md`

2. 使用标准格式创建文件：
   ```markdown
   ---
   name: {name}
   type: {platform|generation|style|genre}
   display_name: 显示名称
   description: 一行描述
   version: 1.0
   ---

   # 标题

   ## 子章节
   - 规则要点...
   ```

3. 在 `app/services/rules_engine.py` 中确认对应的 load 方法能加载此文件

4. 在 `tests/test_rules_engine/` 中添加加载测试
