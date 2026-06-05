from __future__ import annotations

import json
import string
import time
from typing import Any, Callable, Iterable
from dataclasses import dataclass, field

ERROR_UNKNOWN_TOOL = "unknown_tool"
ERROR_INVALID_JSON = "invalid_json"


tools = [
    {
        "type": "function",
        "function":{
            "name": "get_weather",
            "description": "Get today's weather of a location, the user should supply a location first.",
            "parameters":{
                "type": "object",
                "properties":{
                    "location":{
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    }
                },
                "required": ["location"]
            },
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": "Retrieve the current user's profile information, including their name, premium status, and saved preferences.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the file according to the path",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": r"The file's path, e.g. D:\xjbx\Agent-Leanring-Notebook\README.md"
                    }
                },
                "required": ["path"]
            },
        }
    },
    
]



def get_weather(location: str, **kwargs)->str:
    return f"The weather in {location} is sunny!"


def get_user_profile(**kwargs):
    # 无需外部 API，直接返回系统设定好的 Mock 数据
    user_data = {
        "username": "Alex",
        "membership": "VIP",
        "language_preference": "English",
        "home_city": "Beijing",
        "interests": ["AI Technology", "Sci-Fi Movies"]
    }
    return json.dumps(user_data)




available_tools = {
    "get_weather": get_weather,
    "get_user_profile": get_user_profile
}

@dataclass(frozen=True, slots=True)
class ToolResult:
    """Normalized result returned by every tool execution."""
    tool_name: str
    ok: bool
    data: Any
    error_type: str | None
    message: str | None
    latency_ms: int
    attempts: int
    metadata: dict[str, Any] = field(default_factory=dict)


    @classmethod
    def success(
        cls,
        tool_name: str,
        data: Any,
        latency_ms: int = 0,
        attempts: int = 1,
        metadata: dict[str, Any] | None = None,
    )-> "ToolResult":
        return cls(
            tool_name=tool_name,
            ok = True,
            data = data,
            error_type = None,
            message = None,
            latency_ms = latency_ms,
            attempts = attempts,
            metadata = metadata or {},
        )
    
    @classmethod
    def error(
        cls,
        tool_name: str,
        error_type: str,
        message: str,
        latency_ms: int = 0,
        attempts: int = 1,
        data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        return cls(
            tool_name=tool_name,
            ok=False,
            data=data,
            error_type=error_type,
            message=message,
            latency_ms=latency_ms,
            attempts=attempts,
            metadata=metadata or {},
        )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "ok": self.ok,
            "data": self.data,
            "error_type": self.error_type,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "attempts": self.attempts,
            "metadata": self.metadata,
        }

    def to_message_content(self) -> str:
        """Serialize result for role='tool' message content."""
        return json.dumps(
            {
                "ok": self.ok,
                "data": self.data,
                "error_type": self.error_type,
                "message": self.message,
            },
            ensure_ascii=False,
            default=repr,
        )

@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 0
    delay_seconds: float = 0.0
    retry_on: tuple[str, ...] = ("runtime_error", "timeout")

@dataclass(frozen=True, slots=True)
class Tool:
    """
    工具类
    其需要处理invalid_input, runtime_error, empty_result, timeout, retry等边界问题
    同时，其需要计算工具调用耗时
    主要逻辑为，先对输入进行合法性检测，然后调用工具函数
    """

    # 工具名
    name: str
    # 工具描述
    description: str
    # 输入参数约束
    input_schema: dict[str, Any]
    # 一个可调用的对象
    func: Callable[..., Any]
    # 输出规范
    output_schema: dict[str, Any] | None = None
    # 超时控制
    timeout_seconds: float = 5.0
    # 重试策略
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    # 权限
    requires_permission: bool = False

    def to_openai_schema(self)->dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)
    
    def validate_input(self, arguments: dict[str, Any])->str | None:
        """Return error message if arguments are invalid, otherwise None."""
        required = self.input_schema.get("required", [])
        properties = self.input_schema.get("properties", {})

        # 必要的参数没有给
        for field_name in required:
            if field_name not in arguments:
                return f"Missing required argument: {field_name}"
            
        # 给了不需要的参数
        for field_name in arguments:
            if field_name not in properties:
                return f"Unexpected argument: {field_name}"
            
        # First version: only validate common primitive JSON schema types.
        for field_name, field_schema in properties.items():
            if field_name not in arguments:
                continue

            expected_type = field_schema.get("type")
            value = arguments[field_name]

            # 判断参数的类型是否符合预期
            if expected_type == "string" and not isinstance(value, str):
                return f"Argument {field_name!r} must be a string."
            if expected_type == "number" and not isinstance(value, (int, float)):
                return f"Argument {field_name!r} must be a number."
            if expected_type == "integer" and not isinstance(value, int):
                return f"Argument {field_name!r} must be an integer."
            if expected_type == "boolean" and not isinstance(value, bool):
                return f"Argument {field_name!r} must be a boolean."
            if expected_type == "object" and not isinstance(value, dict):
                return f"Argument {field_name!r} must be an object."
            if expected_type == "array" and not isinstance(value, list):
                return f"Argument {field_name!r} must be an array."

        return None
    
    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()

        input_error = self.validate_input(arguments=arguments)

        if input_error:
            return ToolResult.error(
                tool_name=self.name,
                error_type="invalid_input",
                message=input_error,
                latency_ms=self._elapsed_ms(start_time=start_time)
            )

        try:
            data = self.func(**arguments)

        except Exception as exc:
            return ToolResult.error(
                tool_name=self.name,
                error_type="runtime_error",
                message=str(exc),
                latency_ms=self._elapsed_ms(start_time=start_time),
                metadata={"exception_type": type(exc).__name__}
            )
        

        if data is None:
            return ToolResult.error(
                tool_name=self.name,
                error_type="empty_result",
                message="Tool returned no data",
                latency_ms=self._elapsed_ms(start_time=start_time)
            )

        return ToolResult.success(
            tool_name=self.name,
            data = data,
            latency_ms=self._elapsed_ms(start_time=start_time)
        )
    

class ToolRegistry:
    """
    工具注册类，其负责工具的注册，与执行工具的调用逻辑
    同时，需要处理unknown_tool与invalid_json两个边界问题
    其只负责注册工具、与执行工具调用
    """
    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}

        if tools:
            for tool in tools:
                self.register(tool)

    # 进行工具注册
    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
             raise ValueError(f"Tool {tool.name!r} is already registered.")

        self._tools[tool.name] = tool

    # 获取指定工具
    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)
    
    # 获取当前某个工具是否已经注册
    def has(self, name: str) -> bool:
        return name in self._tools
    
    # 获取当前已注册的工具的名字
    def names(self) -> list[str]:
        return sorted([name for name in self._tools])
    
    # 获取当前已注册的工具
    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())
    
    # 将工具转化为Openai的接口格式
    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    # 执行解析好的工具调用
    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self.get(name)

        if tool is None:
            return ToolResult.error(
                tool_name=name,
                error_type=ERROR_UNKNOWN_TOOL,
                message=f"Tool {name!r} is not registered."
            )
        
        return tool.execute(arguments=arguments)
    
    # 根据原始tool_call执行工具调用
    def execute_tool_call(self, tool_call: Any) -> ToolResult:
        name = tool_call.function.name
        raw_arguments = tool_call.function.arguments

        if not self.has(name):
            return ToolResult.error(
                tool_name=name,
                error_type=ERROR_UNKNOWN_TOOL,
                message=f"Tool {name!r} is not registered.",
            )
        
        try:
            arguments = json.loads(raw_arguments or "{}")

        except json.JSONDecodeError as exc:
            return ToolResult.error(
                tool_name=name,
                error_type=ERROR_INVALID_JSON,
                message=str(exc),
            )
        
        if not isinstance(arguments, dict):
            return ToolResult.error(
                tool_name=name,
                error_type=ERROR_INVALID_JSON,
                message="Tool call arguments must be a JSON object.",
            )

        return self.execute(name, arguments)