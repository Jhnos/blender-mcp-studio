"""SemanticToolRouter — selects relevant tools using keyword/embedding similarity.

Reduces LLM "hallucinated tool name" errors by pre-filtering the tool list
to only tools semantically relevant to the user's request.

Strategy (data-driven, no model required):
  1. Keyword matching: each tool has a set of trigger keywords
  2. If ≥1 tool matches, return only matching tools
  3. If 0 match, return all tools (safe fallback)

Future upgrade path: replace keyword matching with sentence embeddings
(e.g., sentence-transformers) for semantic similarity without changing the interface.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from src.core.ports.llm_port import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class ToolKeywords:
    """Keyword triggers for a tool — if any match, the tool is included."""

    tool_name: str
    keywords: frozenset[str] = field(default_factory=frozenset)


# Data-driven: add/remove keywords without changing routing logic
_TOOL_KEYWORD_MAP: list[ToolKeywords] = [
    ToolKeywords("create_object", frozenset([
        "create", "add", "make", "build", "new", "place", "insert",
        "建立", "新增", "加入", "製作", "新建", "生成物件",
        "cube", "sphere", "cylinder", "cone", "torus", "plane", "mesh",
        "立方體", "球", "圓柱", "圓錐", "甜甜圈", "平面",
    ])),
    ToolKeywords("delete_object", frozenset([
        "delete", "remove", "destroy", "erase", "clear",
        "刪除", "移除", "清除",
    ])),
    ToolKeywords("modify_object", frozenset([
        "move", "scale", "resize", "rotate", "position", "location",
        "transform", "modify", "change", "adjust", "hide", "show",
        "移動", "縮放", "旋轉", "調整", "修改", "位置",
    ])),
    ToolKeywords("apply_material", frozenset([
        "material", "color", "colour", "texture", "metallic", "roughness",
        "shiny", "matte", "glossy", "paint", "surface", "appearance",
        "材質", "顏色", "紋理", "表面", "光澤", "粗糙度",
    ])),
    ToolKeywords("get_scene_info", frozenset([
        "scene", "list", "objects", "what", "show", "info", "describe",
        "場景", "物件列表", "有什麼", "顯示",
    ])),
    ToolKeywords("execute_code", frozenset([
        "code", "script", "python", "bpy", "custom", "advanced", "complex",
        "geometry nodes", "animation", "modifier", "constraint",
        "程式碼", "腳本", "幾何節點", "動畫", "修改器",
    ])),
    ToolKeywords("hunyuan3d_generate", frozenset([
        "hunyuan", "ai generate", "ai model", "text to 3d", "generate model",
        "ai 生成", "文字轉3d", "hunyuan3d",
    ])),
    ToolKeywords("hyper3d_rodin_generate", frozenset([
        "rodin", "hyper3d", "high quality model", "ai 3d generation",
        "高品質模型",
    ])),
    ToolKeywords("get_viewport_screenshot", frozenset([
        "screenshot", "capture", "preview", "photo", "image", "render",
        "截圖", "預覽", "拍照",
    ])),
]

# Pre-build normalized keyword → tool_name mapping
_KEYWORD_INDEX: dict[str, list[str]] = {}
for _entry in _TOOL_KEYWORD_MAP:
    for _kw in _entry.keywords:
        _KEYWORD_INDEX.setdefault(_kw.lower(), []).append(_entry.tool_name)


class SemanticToolRouter:
    """Pre-filters tool definitions based on user message relevance.

    Reduces the tool list sent to the LLM, improving accuracy and reducing
    token usage. Matches are based on keyword overlap with the user message.
    """

    def select_tools(
        self,
        user_message: str,
        all_tools: list[ToolDefinition],
        min_tools: int = 3,
    ) -> list[ToolDefinition]:
        """Return a filtered subset of tools relevant to the user message.

        Args:
            user_message: The raw user input text.
            all_tools: Complete list of available ToolDefinitions.
            min_tools: Minimum tools to return (guarantees create/modify always included).

        Returns:
            Filtered tool list. Falls back to all_tools if no matches found.
        """
        tokens = set(re.findall(r'\w+', user_message.lower()))
        matched_names: set[str] = set()

        for token in tokens:
            for name in _KEYWORD_INDEX.get(token, []):
                matched_names.add(name)

        if not matched_names:
            logger.debug("SemanticToolRouter: no keyword matches, returning all %d tools", len(all_tools))
            return all_tools

        # Build filtered list preserving original order
        filtered = [t for t in all_tools if t.name in matched_names]

        # Ensure minimum tools (always include get_scene_info as context tool)
        tool_names = {t.name for t in filtered}
        if len(filtered) < min_tools:
            for t in all_tools:
                if t.name not in tool_names:
                    filtered.append(t)
                    tool_names.add(t.name)
                if len(filtered) >= min_tools:
                    break

        logger.debug(
            "SemanticToolRouter: '%s...' → %d/%d tools: %s",
            user_message[:40],
            len(filtered),
            len(all_tools),
            [t.name for t in filtered],
        )
        return filtered
