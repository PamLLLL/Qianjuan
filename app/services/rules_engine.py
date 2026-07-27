# 启用延迟类型注解，让类型提示在运行时不立即求值（Python 3.10+ 风格的 X | Y 写法需要这个）
from __future__ import annotations

# 导入日志模块，用于记录警告和错误信息
import logging
# 导入 Path 类，用于跨平台的文件路径操作
from pathlib import Path

# 从项目配置中导入规则文件的根目录路径（默认是项目下的 rules/ 文件夹）
from app.config import RULES_DIR
# 导入 Markdown 解析器，用于读取 .md 文件中去掉 frontmatter 后的纯正文内容
from app.core.markdown.parser import read_markdown_content

# 创建当前模块的日志记录器，名字自动设为 "app.services.rules_engine"
logger = logging.getLogger(__name__)


# 自定义异常：当必需的规则文件找不到时抛出
class RulesFileNotFound(Exception):
    """Raised when a required rules file is missing."""


# 规则引擎：负责从 rules/ 目录加载 Markdown 规则文件，并拼装成给 AI 用的 System Prompt
class RulesEngine:
    """Loads Markdown rule files and assembles System Prompts.

    Rule files live under RULES_DIR with this structure:
        rules/platforms/{name}.md    — 发布平台规则（如起点、番茄）
        rules/generation/{step}.md   — 生成步骤规则（如大纲、章节）
        rules/styles/{name}.md       — 写作风格模板（如轻松、严肃）
        rules/genres/{name}.md       — 小说类型规则（如玄幻、都市）
    """

    # 初始化方法：接收可选的规则目录路径，不传则使用配置文件中的默认值
    def __init__(self, rules_dir: Path | None = None) -> None:
        # 如果调用方传了自定义路径就用自定义的，否则用全局配置的 RULES_DIR
        self.rules_dir = rules_dir or RULES_DIR

    # 内部方法：从指定路径加载一个规则文件的内容
    # path: 文件路径；required: 是否必需（必需的文件缺失会报错，可选的会跳过）
    def _load(self, path: Path, required: bool = True) -> str:
        # 检查文件是否存在
        if not path.exists():
            # 如果是必需文件，抛异常中断流程
            if required:
                raise RulesFileNotFound(f"必需的规则文件缺失: {path}")
            # 如果是可选文件，记一条警告日志然后返回空字符串
            logger.warning("可选规则文件不存在，跳过: %s", path)
            return ""

        # 文件存在，调用 Markdown 解析器读取正文内容（会自动去掉 YAML frontmatter 头部）
        content = read_markdown_content(path)
        # 检查读到的内容是否为空（去掉空白后）
        if not content.strip():
            # 必需文件内容为空也报错
            if required:
                raise RulesFileNotFound(f"规则文件内容为空: {path}")
            # 可选文件内容为空，记警告并跳过
            logger.warning("规则文件内容为空，跳过: %s", path)
            return ""

        # 返回读到的规则文本内容
        return content

    # 加载指定发布平台的规则（如 "qidian" → rules/platforms/qidian.md）
    # 平台规则是必需的，找不到会报错
    def load_platform_rules(self, platform: str) -> str:
        """Load platform rules (required — will raise if missing)."""
        # 拼接文件路径：rules_dir/platforms/平台名.md
        path = self.rules_dir / "platforms" / f"{platform}.md"
        # 调用 _load 加载，required=True 表示这个文件必须存在
        return self._load(path, required=True)

    # 加载指定生成步骤的规则（如 "outline" → rules/generation/outline.md）
    # 生成步骤规则也是必需的
    def load_generation_rules(self, step: str) -> str:
        """Load generation step rules (required)."""
        # 拼接文件路径：rules_dir/generation/步骤名.md
        path = self.rules_dir / "generation" / f"{step}.md"
        return self._load(path, required=True)

    # 加载写作风格模板（如 "humorous" → rules/styles/humorous.md）
    # 风格是可选的，文件不存在就返回空字符串，不会报错
    def load_style(self, style: str) -> str:
        """Load style template (optional — returns empty if missing)."""
        # 拼接文件路径：rules_dir/styles/风格名.md
        path = self.rules_dir / "styles" / f"{style}.md"
        # required=False 表示可选，缺失不报错
        return self._load(path, required=False)

    # 加载小说类型规则（如 "xuanhuan" → rules/genres/xuanhuan.md）
    # 类型也是可选的
    def load_genre(self, genre: str) -> str:
        """Load genre rules (optional — returns empty if missing)."""
        # 拼接文件路径：rules_dir/genres/类型名.md
        path = self.rules_dir / "genres" / f"{genre}.md"
        return self._load(path, required=False)

    # 组装完整的 System Prompt（发给 AI 的系统指令）
    # 最终结果 = 基础系统提示词 + 平台规则 + 风格模板(可选) + 类型规则(可选)
    def build_system_prompt(
        self,
        platform: str,            # 发布平台名，如 "qidian"
        style: str | None = None, # 写作风格名，可选
        genre: str | None = None, # 小说类型名，可选
    ) -> str:
        """Assemble full System Prompt = base + platform + style + genre."""
        # 第一块：加载基础系统提示词（rules/generation/system-prompt.md）
        parts = [self.load_generation_rules("system-prompt")]
        # 第二块：追加平台规则
        parts.append(self.load_platform_rules(platform))
        # 第三块：如果指定了风格，尝试加载风格模板
        if style:
            style_content = self.load_style(style)
            # 只有内容非空才追加（可选文件可能返回空字符串）
            if style_content:
                parts.append(style_content)
        # 第四块：如果指定了类型，尝试加载类型规则
        if genre:
            genre_content = self.load_genre(genre)
            # 同样只有非空才追加
            if genre_content:
                parts.append(genre_content)
        # 用两个换行符把所有部分拼接起来，形成完整的 System Prompt
        return "\n\n".join(parts)

    # 构建某个具体生成步骤所需的完整提示词
    # 返回一个元组：(system_prompt, step_rules)
    # system_prompt 是系统指令，step_rules 是这个步骤特有的生成规则
    def build_step_prompt(
        self,
        step: str,                # 生成步骤名，如 "outline"、"chapter"
        platform: str,            # 发布平台名
        style: str | None = None, # 写作风格名，可选
        genre: str | None = None, # 小说类型名，可选
    ) -> tuple[str, str]:
        """Build system prompt + step-specific generation rules.

        Returns (system_prompt, step_rules) tuple.
        """
        # 先调用 build_system_prompt 组装完整的系统提示词
        system_prompt = self.build_system_prompt(platform, style, genre)
        # 再单独加载这个步骤的生成规则（如 rules/generation/outline.md）
        step_rules = self.load_generation_rules(step)
        # 返回两部分，调用方可以分别放到 AI 请求的 system 和 user message 中
        return system_prompt, step_rules

    # 列出某个分类目录下所有可用的规则文件
    # category 可以是 "platforms"、"styles"、"genres" 等
    # 返回一个列表，每项包含 name（文件名）、display_name（显示名）、description（描述）
    def list_available(self, category: str) -> list[dict[str, str]]:
        """List available rule files in a category (platforms/styles/genres).

        Returns list of {name, display_name, description}.
        """
        # 在函数内部延迟导入，避免模块级别的循环依赖
        from app.core.markdown.parser import parse_markdown_file

        # 拼接分类目录路径，如 rules/platforms/
        category_dir = self.rules_dir / category
        # 如果目录不存在，返回空列表
        if not category_dir.exists():
            return []

        # 准备结果列表
        result = []
        # 遍历目录下所有 .md 文件，sorted 保证按文件名排序
        for md_file in sorted(category_dir.glob("*.md")):
            # 跳过 AGENTS.md（这是给 Claude Code 用的代理配置文件，不是规则文件）
            if md_file.name == "AGENTS.md":
                continue
            # 解析 Markdown 文件，提取 frontmatter 中的元数据（name、display_name、description）
            parsed = parse_markdown_file(md_file)
            # 把解析结果加入列表；如果 frontmatter 没写某个字段，用文件名（不含 .md）作为兜底
            result.append({
                "name": parsed.name or md_file.stem,              # 规则标识名
                "display_name": parsed.display_name or md_file.stem,  # 前端显示名
                "description": parsed.description or "",          # 规则描述
            })
        # 返回所有可用规则的列表
        return result
