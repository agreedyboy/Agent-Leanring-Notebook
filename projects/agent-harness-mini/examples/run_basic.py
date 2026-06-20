from openai import OpenAI
from agent_harness_mini.config import load_model_config
from agent_harness_mini.loop import run_agent
from agent_harness_mini.tracing import JsonlTracer
from agent_harness_mini.tools import build_default_registry
from agent_harness_mini.session import AgentSession, AgentRunResult


config = load_model_config("DEEPSEEK")

client = OpenAI(api_key=config.api_key,
               base_url=config.base_url)

# messages=[
#         {"role": "system", "content": "You are a helpful assistant"},
#         {"role": "user", "content": "Hello, how's the weather in Jiangsu and Hefei, Anhui?"},
#         # {"role": "user", "content": "Hello, do you know who i am?"},
#     ]

session = AgentSession.create({"role": "system", "content": "You are a helpful assistant"})
session.add_user_message("Hello, how's the weather in Nanjing and Hefei, Anhui?")

tracer = JsonlTracer(".traces/run_basic.jsonl")

tool_registry = build_default_registry()

output = run_agent(client=client, 
                   model_id=config.model_id, 
                   session=session,
                   tool_registry=tool_registry,
                   max_steps=3,
                   tracer=tracer)

print(f"Messags>\t {session.to_model_messages()}")

print(f"\nOutput>\t {output.output}")
