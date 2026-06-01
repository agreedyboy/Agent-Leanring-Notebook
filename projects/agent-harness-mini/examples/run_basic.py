from openai import OpenAI
from agent_harness_mini.config import load_model_config
from agent_harness_mini.tools import tools, available_tools
from agent_harness_mini.loop import run_agent

import json

config = load_model_config("DEEPSEEK")

client = OpenAI(api_key=config.api_key,
               base_url=config.base_url)

def send_messages(messages):
    response = client.chat.completions.create(
        model=config.model_id,
        messages=messages,
        tools=tools
    )
    return response.choices[0].message

messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello, how's the weather in Zhenjiang, Jiangsu and Hefei, Anhui?"},
        # {"role": "user", "content": "Hello, do you know who i am?"},
    ]

output = run_agent(client=client, 
                   model_id=config.model_id, 
                   messages=messages, 
                   tools=tools, 
                   available_tools=available_tools,
                   max_steps=3)

print(f"Messags>\t {messages}")

print(f"\nOutput>\t {output}")