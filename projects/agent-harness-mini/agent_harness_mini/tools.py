from __future__ import annotations

import json
import string
import time
import requests
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



# 根据传入地点返回模拟天气信息。
def get_weather(location: str, **kwargs)->str:
    """
    获取指定城市的当前天气情况。
    :param location: 城市名称 (例如: "Beijing", "Tokyo", "New York")
    :return: 包含天气描述的字符串
    """
    try:
        # 1. 坐标转换：将城市名转换为经纬度
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en"
        geo_res = requests.get(geo_url).json()
        
        if not geo_res.get("results"):
            raise f"Error: Cannot find location '{location}'."
        
        loc_data = geo_res["results"][0]
        lat = loc_data["latitude"]
        lon = loc_data["longitude"]
        city_name = loc_data["name"]
        
        # 2. 请求天气数据
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_res = requests.get(weather_url).json()
        
        current = weather_res.get("current_weather")
        if not current:
            raise "Error: Failed to retrieve weather data."
        
        # 3. 提取核心指标
        temp = current["temperature"]
        windspeed = current["windspeed"]
        # WMO Weather interpretation codes (简化处理)
        weather_code = current["weathercode"] 
        
        return f"The current weather in {city_name} is: Temperature {temp}°C, Wind Speed {windspeed} km/h. (Weather Code: {weather_code})"
        
    except Exception as e:
        raise f"An error occurred: {str(e)}"


# 返回当前用户的模拟画像信息。
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

# 计算a*b
def calculate(a: float, b: float) -> float:
    return a * b
    
    

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


    # 构造一个表示工具执行成功的结果对象。
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
    
    # 构造一个表示工具执行失败的结果对象。
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
    
    # 将工具结果转换为普通字典，便于 trace、测试和调试。
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

    # 将工具结果序列化为 role="tool" 消息所需的 content 字符串。
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
class ToolCallResult:
    """Result wrapper for one model tool_call.
        Function call的结果为ToolResult，但是并不包含call id, call id又不适合作为参数传给Tool，因此定义ToolCallResult类
        来为工具调用结果增加call id属性
    """

    tool_call_id: str
    result: ToolResult

    def to_tool_message(self) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "name": self.result.tool_name,
            "content": self.result.to_message_content(),
        }

@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 0
    delay_seconds: float = 0.0
    retry_on: tuple[str, ...] = ("runtime_error", "timeout")

@dataclass(frozen=True, slots=True)
class Tool:
    """
    工具类
    需要包含工具名、描述、input schema, output schema等等属性，同时需要提供execute行为
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


    # 生成 OpenAI function calling 所需的工具 schema。
    def to_openai_schema(self)->dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    # 根据开始时间计算当前操作耗时，单位为毫秒。
    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)
    
    # 校验模型传入的工具参数是否符合 input_schema。
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
    
    # 执行工具函数，并将成功、异常和空结果统一转换成 ToolResult。
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
        
        max_attempts = self.retry_policy.max_retries + 1
        attempt_records: list[dict[str, Any]] = []

        for attempt in range(1, max_attempts + 1):
            attempt_start_time = time.perf_counter()
            try:
                data = self.func(**arguments)
            except Exception as exc:
                attempt_records.append(
                    {
                        "attempt": attempt,
                        "ok": False,
                        "error_type": "runtime_error",
                        "message": str(exc),
                        "latency_ms": self._elapsed_ms(start_time=attempt_start_time),
                    }
                )
                result = ToolResult.error(
                    tool_name=self.name,
                    error_type="runtime_error",
                    message=str(exc),
                    latency_ms=self._elapsed_ms(start_time=start_time),
                    attempts=attempt,
                    metadata={
                        "exception_type": type(exc).__name__,
                        "attempts": attempt_records,
                    }
                )
            else:
                if data is None:
                    attempt_records.append(
                        {
                            "attempt": attempt,
                            "ok": False,
                            "error_type": "empty_result",
                            "message": "Tool returned no data",
                            "latency_ms": self._elapsed_ms(start_time=attempt_start_time),
                        }
                    )
                    result = ToolResult.error(
                        tool_name=self.name,
                        error_type="empty_result",
                        message="Tool returned no data",
                        latency_ms=self._elapsed_ms(start_time=start_time),
                        attempts=attempt,
                        metadata={"attempts": attempt_records},
                    )
                else:
                    attempt_records.append(
                        {
                            "attempt": attempt,
                            "ok": True,
                            "error_type": None,
                            "message": None,
                            "latency_ms": self._elapsed_ms(start_time=attempt_start_time),
                        }
                    )
                    return ToolResult.success(
                        tool_name=self.name,
                        data=data,
                        latency_ms=self._elapsed_ms(start_time=start_time),
                        attempts=attempt,
                        metadata={"attempts": attempt_records},
                )
            
            should_retry = (
                result.error_type in self.retry_policy.retry_on
                and attempt < max_attempts
            )

            if not should_retry:
                return result

            if self.retry_policy.delay_seconds > 0:
                time.sleep(self.retry_policy.delay_seconds)

        return result


class ToolRegistry:
    """
    工具注册类，其负责工具的注册，与执行工具的调用逻辑
    同时，需要处理unknown_tool与invalid_json两个边界问题
    其只负责注册工具、与执行工具调用
    """
    # 初始化工具注册表，并可选择批量注册初始工具。
    def __init__(self, tools: Iterable[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}

        if tools:
            for tool in tools:
                self.register(tool)

    # 注册一个工具，并拒绝重复名称。
    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
             raise ValueError(f"Tool {tool.name!r} is already registered.")

        self._tools[tool.name] = tool

    # 根据名称获取工具；不存在时返回 None。
    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)
    
    # 判断指定名称的工具是否已经注册。
    def has(self, name: str) -> bool:
        return name in self._tools
    
    # 返回所有已注册工具的名称列表。
    def names(self) -> list[str]:
        return sorted([name for name in self._tools])
    
    # 返回所有已注册的 Tool 对象。
    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())
    
    # 将注册表中的工具批量转换为 OpenAI tools 参数格式。
    def to_openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    # 执行一个已经解析为 name 和 arguments 的工具调用。
    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self.get(name)

        if tool is None:
            return ToolResult.error(
                tool_name=name,
                error_type=ERROR_UNKNOWN_TOOL,
                message=f"Tool {name!r} is not registered."
            )
        
        return tool.execute(arguments=arguments) 
    
    # 从模型返回的原始 tool_call 中解析名称和参数，并执行对应工具。
    def execute_tool_call(self, tool_call: Any) -> ToolCallResult:
        tool_call_id = tool_call.id
        name = tool_call.function.name
        raw_arguments = tool_call.function.arguments

        if not self.has(name):
            return ToolCallResult(
                tool_call_id=tool_call_id,
                result=ToolResult.error(
                    tool_name=name,
                    error_type=ERROR_UNKNOWN_TOOL,
                    message=f"Tool {name!r} is not registered.",
                ),
            )
        
        try:
            arguments = json.loads(raw_arguments or "{}")

        except json.JSONDecodeError as exc:
            return ToolCallResult(
                tool_call_id=tool_call_id,
                result=ToolResult.error(
                    tool_name=name,
                    error_type=ERROR_INVALID_JSON,
                    message=str(exc),
                ),
            )
        
        if not isinstance(arguments, dict):
            return ToolCallResult(
                tool_call_id=tool_call_id,
                result=ToolResult.error(
                    tool_name=name,
                    error_type=ERROR_INVALID_JSON,
                    message="Tool call arguments must be a JSON object.",
                ),
            )

        return ToolCallResult(
            tool_call_id=tool_call_id,
            result=self.execute(name, arguments),
        )
    
# 创建项目默认工具注册表，集中维护内置工具定义。
def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        Tool(
            name="get_weather",
            description="Get today's weather of a location.",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city name only (e.g., 'Beijing', 'Tokyo', 'New York'). Do NOT include province, state, or country.",
                    }
                },
                "required": ["location"],
            },
            func=get_weather,
            retry_policy=RetryPolicy(max_retries=3, delay_seconds=0.5, retry_on=("runtime_error",)),
        )
    )

    registry.register(
        Tool(
            name="get_user_profile",
            description="Retrieve the current user's profile information.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
            func=get_user_profile,
        )
    )

    registry.register(
        Tool(
            name="calculate",
            description="Calculate the product of two numbers.",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "The first number.",
                    },
                    "b": {
                        "type": "number",
                        "description": "The second number.",
                    },
                },
                "required": ["a", "b"],
            },
            func=calculate,
        )
    )

    return registry
