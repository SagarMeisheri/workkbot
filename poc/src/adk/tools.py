"""
Workkbot Local PoC: Google ADK 2.0 Dynamic Toolset & Tool Adapters
Wraps dynamically discovered MCP tools from Google Workspace and Zoho Suite
into official ADK 2.0 BaseToolset and BaseTool abstractions.
"""
from typing import Any, Callable, Dict, List, Optional
try:
    from google.adk.tools.base_toolset import BaseToolset
    from google.adk.tools import BaseTool, ToolContext
    from google.genai import types
except ImportError:
    # Graceful fallback base classes if google-adk is being bootstrapped
    class BaseTool:
        def __init__(self, name: str, description: str):
            self.name = name
            self.description = description

    class BaseToolset:
        def __init__(self, tool_filter=None, tool_name_prefix=""):
            self.tool_filter = tool_filter
            self.tool_name_prefix = tool_name_prefix

    class ToolContext:
        def __init__(self, state=None):
            self.state = state or {}

    class types:
        class FunctionDeclaration:
            def __init__(self, name: str, description: str, parameters_json_schema: dict):
                self.name = name
                self.description = description
                self.parameters_json_schema = parameters_json_schema

from src.mcp.models import McpTool


class DynamicAdkTool(BaseTool):
    """
    ADK 2.0 BaseTool implementation for a dynamically discovered MCP tool.
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        server: str,
        category: str,
        is_mutating: bool,
        executor_func: Callable[[str, Dict[str, Any]], Any],
    ):
        super().__init__(name=name, description=description)
        self.input_schema = input_schema
        self.server = server
        self.category = category
        self.is_mutating = is_mutating
        self.executor_func = executor_func

    def _get_declaration(self) -> Any:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters_json_schema=self.input_schema,
        )

    async def run_async(self, *, args: Dict[str, Any], tool_context: Any = None) -> Any:
        return self.executor_func(self.name, args)

    def __call__(self, **kwargs) -> Any:
        return self.executor_func(self.name, kwargs)


class WorkkbotDynamicToolset(BaseToolset):
    """
    ADK 2.0 BaseToolset that dynamically yields tools based on connected MCP providers.
    If a provider is disconnected, its tools are immediately omitted.
    """

    def __init__(self, registry: Any):
        super().__init__()
        self.registry = registry

    async def get_tools(self, readonly_context: Any = None) -> List[DynamicAdkTool]:
        return self.get_available_adk_tools()

    def get_available_adk_tools(self) -> List[DynamicAdkTool]:
        available_mcp: List[McpTool] = self.registry.get_available_tools()
        adk_tools: List[DynamicAdkTool] = []

        for t in available_mcp:
            tool = DynamicAdkTool(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
                server=t.server,
                category=t.category,
                is_mutating=t.is_mutating,
                executor_func=lambda name, args: self.registry.execute_tool(name, args).data,
            )
            adk_tools.append(tool)

        return adk_tools
