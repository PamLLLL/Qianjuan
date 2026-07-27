# 千卷 QianJuan — 全局约定

## 代码风格
- Python 3.11+，使用 type hints
- 行宽上限 100 字符
- import 排序：stdlib → third-party → local（ruff 自动处理）
- 不写多余注释，代码自解释

## Git 工作流
- 每完成一个功能模块提交一次
- commit message 格式：`type: description`（feat/fix/chore/refactor/test/docs）
- 不提交 .env、data/*.db

## 错误处理
- API 层用 HTTPException，附 detail 说明
- 服务层抛自定义异常，API 层捕获转 HTTP 错误
- AI 调用失败通过 AiProvider 基类统一重试

## 项目结构约定
- 一个模型一个文件（app/models/xxx.py）
- 一个路由模块一个文件（app/api/xxx.py）
- 服务层不直接创建数据库 session，通过参数注入
