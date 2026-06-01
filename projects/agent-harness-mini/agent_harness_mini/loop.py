from openai import OpenAI

import json
import time

def call_model(client, model_id, messages, tools):
    """Call the chat completion API and return assistant message."""
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        tools=tools
    )
    return response.choices[0].message

def parse_tool_arguments(raw_arguments: str)->dict:
    """Parse tool call arguments from JSON string."""
    return json.loads(raw_arguments)

def execute_tool_call(tool_call, available_tools: dict):
    """
    Execute one tool call.

    Should handle:
    - unknown tool
    - invalid JSON arguments
    - tool runtime exception
    """
    tool_call_id = tool_call.id
    function_name = tool_call.function.name

    # 构建需要返回的信息的格式
    tool_response_message = {}

    # 检查工具是否可用
    if function_name not in available_tools:
        print(f"Error! {function_name} is not defined or unavailable!")

        tool_response_message = {
            "tool_call_id": tool_call_id,
            "tool_name": function_name,
            "ok": False,
            "data": None,
            "error_type": "unknown_tool",
            "message": "Tool is not defined or unavailable or tool arguments are not valid JSON.",
            "latency_ms": 1,
        }

        return tool_response_message
    
    # 动态调用工具
    function_to_call = available_tools[function_name]

    # 工具调用开始时间
    start_time = time.perf_counter()

    try:
        # 解析参数
        function_args = parse_tool_arguments(tool_call.function.arguments)

        # 调用工具
        tool_output = function_to_call(**function_args)
        ok = True
        error_type = None
        message = None
    except Exception as exc:
        tool_output = None
        ok = False
        error_type = "runtime_error"
        message = str(exc)

    # 计算本次工具调用延时
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    tool_response_message = {
        "tool_call_id": tool_call_id,
        "tool_name": function_name,
        "ok": ok,
        "data": tool_output,
        "error_type": error_type,
        "message": message,
        "latency_ms": latency_ms,
    }

    return tool_response_message


def build_tool_message(result):
    """
    把内部执行结果转换成 role='tool' 的消息。
    """

    tool_message = {
        "role": "tool",
        "tool_call_id": result["tool_call_id"],
        "name": result["tool_name"],
        "content": json.dumps({
            "ok": result["ok"] or False,
            "data": result["data"] or None,
            "error_type": result["error_type"] or None,
            "message": result["message"] or None,
        })
    }

    return tool_message

def build_assistant_message(message):
    """Convert model assistant message object into message dict."""
    if message.tool_calls:
        return {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in message.tool_calls
                    ],
                }
    
    return {
                "role": "assistant",
                "content": message.content,
            }




def run_agent(client, 
              model_id: str,
              messages: list[dict], 
              tools: list[dict], 
              available_tools: dict, 
              max_steps = 3):
    """
    Run one agent loop.
    Responsibilities:
    1. Send messages to model.
    2. Detect whether model requested tool calls.
    3. Execute requested tools.
    4. Append tool results back into messages.
    5. Repeat until final answer or max_steps reached.
    """

    for step in range(max_steps):
        assistant_messages = call_model(client=client, model_id=model_id, messages=messages, tools=tools)

        print(f"\nAssistant_messages>\t {build_assistant_message(assistant_messages)}\n")

        messages.append(build_assistant_message(assistant_messages))

        if not assistant_messages.tool_calls:
            return assistant_messages.content
        
        for tool_call in assistant_messages.tool_calls:
            # 执行工具调用
            result = execute_tool_call(tool_call=tool_call, available_tools=available_tools)

            # 处理工具调用结果
            tool_message = build_tool_message(result=result)

            # 将工具调用结果加到消息队列中
            messages.append(tool_message)

    # 若没有提前返回结果则说明超过最大步数了
    return "max_steps_exceeded"
